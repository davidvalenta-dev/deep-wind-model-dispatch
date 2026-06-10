"""Train COVE-DV: a forecast-window dispatch planner.

COVE-DV is different from the original COVE-NN:
- Original COVE-NN behaves more like a step-by-step policy.
- COVE-DV sees the full 168-hour window first.
- COVE-DV predicts a full 168-hour action plan.

Action meaning:
- -1 = charge/store as hard as possible
-  0 = hold / mostly sell direct generation
- +1 = discharge/release as hard as possible

The teacher is the 168-hour mixed-integer dispatch optimizer created by
milp_teacher_dispatch.py.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
if str(STRATEGY_SRC) not in sys.path:
    sys.path.insert(0, str(STRATEGY_SRC))

import util  # noqa: E402
from classical_strategies import baseload  # noqa: E402
from model import VFNN_2  # noqa: E402


class CoveDVPlanner(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float):
        super().__init__()
        self.encoder = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded, _ = self.encoder(x)
        return self.head(encoded).squeeze(-1)


def split_sequences(values: np.ndarray, seq_length: int) -> np.ndarray:
    split_idxs = np.arange(0, len(values), seq_length)
    return np.array(np.split(values, split_idxs)[1:-1])


def flatten(items: list[np.ndarray]) -> np.ndarray:
    if not items:
        return np.array([])
    return np.concatenate([x.reshape(-1) for x in items])


def cove_value(power: np.ndarray, price: np.ndarray, config: dict) -> float:
    return float(
        util.cove(
            power,
            price,
            config["storage_type"],
            config["storage_rating"],
            config["storage_duration"],
            config["rated_capacity"],
            config["num_modules"],
        )
    )


def make_features(data: pd.DataFrame, config: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    power = data["power_generated"].to_numpy(dtype=float)
    price = util.normalize_price(data["lmp"].copy(), config).to_numpy(dtype=float)
    load = data["user_load_zonal"].to_numpy(dtype=float)
    load = load / np.max(load)

    feature_cols = [
        power / config["rated_capacity"],
        price,
        load,
    ]
    if "datetime" in data.columns:
        dt = pd.to_datetime(data["datetime"])
        hour = dt.dt.hour.to_numpy(dtype=float)
        doy = dt.dt.dayofyear.to_numpy(dtype=float)
        feature_cols.extend(
            [
                np.sin(2 * np.pi * hour / 24),
                np.cos(2 * np.pi * hour / 24),
                np.sin(2 * np.pi * doy / 366),
                np.cos(2 * np.pi * doy / 366),
            ]
        )
    features = np.stack(feature_cols, axis=-1)
    return features, power, price


def make_dataset(data_path: Path, labels_path: Path, config: dict) -> TensorDataset:
    data = pd.read_csv(data_path)
    labels = pd.read_csv(labels_path)
    if len(data) != len(labels):
        raise ValueError(f"data rows ({len(data)}) and label rows ({len(labels)}) do not match")

    features, power, price = make_features(data, config)
    target_action = labels["milp_action"].to_numpy(dtype=float)
    target_release = labels["milp_release"].to_numpy(dtype=float)

    seq_length = config["seq_length"]
    feature_seq = split_sequences(features, seq_length)
    power_seq = split_sequences(power, seq_length)
    price_seq = split_sequences(price, seq_length)
    action_seq = split_sequences(target_action, seq_length)
    release_seq = split_sequences(target_release, seq_length)

    return TensorDataset(
        torch.tensor(feature_seq, dtype=torch.float32),
        torch.tensor(action_seq, dtype=torch.float32),
        torch.tensor(release_seq, dtype=torch.float32),
        torch.tensor(power_seq, dtype=torch.float32),
        torch.tensor(price_seq, dtype=torch.float32),
    )


def split_dataset(dataset: TensorDataset, config: dict):
    n = len(dataset)
    train_size = int(config["train_percent"] * n)
    val_size = int(config["val_percent"] * n)
    torch.manual_seed(0)
    indices = torch.randperm(n)
    tensors = dataset.tensors

    def subset(idx: torch.Tensor) -> TensorDataset:
        return TensorDataset(*(tensor[idx] for tensor in tensors))

    return (
        subset(indices[:train_size]),
        subset(indices[train_size : train_size + val_size]),
        subset(indices[train_size + val_size :]),
    )


def simulate_actions(actions: torch.Tensor, power: torch.Tensor, config: dict):
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])

    batch, timesteps = actions.shape
    storage = torch.zeros(batch, dtype=actions.dtype, device=actions.device)
    releases = []
    storages = []
    charges = []
    discharges = []

    for t in range(timesteps):
        action = actions[:, t]
        generation = power[:, t]
        desired_charge = torch.relu(-action) * rating
        desired_discharge = torch.relu(action) * rating

        available_capacity = torch.clamp(capacity - storage, min=0.0)
        charge = torch.minimum(torch.minimum(desired_charge, generation), available_capacity)
        direct = torch.clamp(generation - charge, min=0.0, max=grid_cap)
        grid_room = torch.clamp(grid_cap - direct, min=0.0)
        max_discharge_from_soc = torch.clamp(storage * rte, min=0.0)
        discharge = torch.minimum(torch.minimum(desired_discharge, max_discharge_from_soc), grid_room)
        release = direct + discharge
        storage = torch.clamp(storage + charge - (discharge / rte), min=0.0, max=capacity)

        releases.append(release)
        storages.append(storage)
        charges.append(charge)
        discharges.append(discharge)

    return (
        torch.stack(releases, dim=1),
        torch.stack(storages, dim=1),
        torch.stack(charges, dim=1),
        torch.stack(discharges, dim=1),
    )


def baseline_releases(power_batches: list[np.ndarray], config: dict) -> np.ndarray:
    rte = util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"])
    parts = []
    for batch in power_batches:
        for seq in batch:
            released, *_ = baseload(
                seq,
                config["storage_rating"] * config["num_modules"],
                config["storage_rating"] * config["storage_duration"] * config["num_modules"],
                rte,
            )
            parts.append(released)
    return np.concatenate(parts)


def make_original_model(config: dict) -> VFNN_2:
    return VFNN_2(
        config["hidden_size"],
        config["num_hidden"],
        config["fc_hidden_sizes"],
        config["rated_capacity"],
        config["storage_type"],
        config["storage_rating"],
        config["storage_duration"],
        config["num_modules"],
    )


def evaluate_cove_dv(model: CoveDVPlanner, loader: DataLoader, config: dict, device: torch.device) -> dict[str, float]:
    model.eval()
    action_losses = []
    release_losses = []
    pred_releases = []
    teacher_releases = []
    powers = []
    prices = []
    actions = []
    with torch.no_grad():
        for features, target_action, target_release, power, price in loader:
            features = features.to(device)
            target_action = target_action.to(device)
            target_release = target_release.to(device)
            power = power.to(device)
            action = model(features)
            release, _, _, _ = simulate_actions(action, power, config)
            action_losses.append(float(torch.mean((action - target_action) ** 2).cpu()))
            release_losses.append(float(torch.mean(((release - target_release) / config["rated_capacity"]) ** 2).cpu()))
            pred_releases.append(release.cpu().numpy())
            teacher_releases.append(target_release.cpu().numpy())
            powers.append(power.cpu().numpy())
            prices.append(price.numpy())
            actions.append(action.cpu().numpy())

    pred = flatten(pred_releases)
    teacher = flatten(teacher_releases)
    power_flat = flatten(powers)
    price_flat = flatten(prices)
    action_flat = flatten(actions)
    base = baseline_releases(powers, config)
    model_cove = cove_value(pred, price_flat, config)
    teacher_cove = cove_value(teacher, price_flat, config)
    baseload_cove = cove_value(base, price_flat, config)
    return {
        "action_mse": float(np.mean(action_losses)),
        "release_mse_scaled": float(np.mean(release_losses)),
        "model_cove": model_cove,
        "teacher_cove": teacher_cove,
        "baseload_cove": baseload_cove,
        "model_improvement_vs_baseload_pct": (baseload_cove - model_cove) / baseload_cove * 100,
        "teacher_improvement_vs_baseload_pct": (baseload_cove - teacher_cove) / baseload_cove * 100,
        "mean_abs_action": float(np.mean(np.abs(action_flat))),
    }


def evaluate_original(model_path: Path, loader: DataLoader, config: dict, device: torch.device) -> dict[str, float] | None:
    if not model_path.exists():
        return None
    model = make_original_model(config)
    model.load_state_dict(torch.load(model_path, weights_only=True, map_location=device))
    model.to(device)
    model.eval()
    releases = []
    teacher_releases = []
    powers = []
    prices = []
    with torch.no_grad():
        for features, _, target_release, power, price in loader:
            # Original COVE-NN expects raw power, normalized price, normalized load.
            original_input = torch.stack(
                [
                    power,
                    price,
                    features[:, :, 2],
                ],
                dim=-1,
            ).to(device)
            pred = model(original_input)[:, :, 0]
            releases.append(pred.cpu().numpy())
            teacher_releases.append(target_release.numpy())
            powers.append(power.numpy())
            prices.append(price.numpy())
    release_flat = flatten(releases)
    price_flat = flatten(prices)
    base = baseline_releases(powers, config)
    model_cove = cove_value(release_flat, price_flat, config)
    baseload_cove = cove_value(base, price_flat, config)
    return {
        "model_cove": model_cove,
        "baseload_cove": baseload_cove,
        "model_improvement_vs_baseload_pct": (baseload_cove - model_cove) / baseload_cove * 100,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train COVE-DV forecast-window planner.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--labels", default=str(REPO_ROOT / "strategy_model" / "optimization" / "milp_teacher_labels_seq168_run_016.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--baseline-model", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "model_run_016.pth"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "strategy_model" / "optimization" / "cove_dv_run_016"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--release-weight", type=float, default=5.0)
    parser.add_argument("--revenue-weight", type=float, default=0.02)
    parser.add_argument("--terminal-weight", type=float, default=0.2)
    args = parser.parse_args()

    np.random.seed(0)
    torch.manual_seed(0)
    config = util.load_config(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = make_dataset(Path(args.data), Path(args.labels), config)
    train_set, val_set, test_set = split_dataset(dataset, config)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_set, batch_size=args.batch_size, shuffle=False)

    input_size = dataset.tensors[0].shape[-1]
    model = CoveDVPlanner(input_size, args.hidden_size, args.num_layers, args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=4)

    rows = []
    best_val_cove = float("inf")
    best_path = out_dir / "cove_dv_model.pth"
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])

    print(f"COVE-DV input features: {input_size}")
    print(f"training sequences: {len(train_set)}")
    print(f"validation sequences: {len(val_set)}")
    print(f"test sequences: {len(test_set)}")

    for epoch in range(args.epochs):
        model.train()
        train_losses = []
        for features, target_action, target_release, power, price in train_loader:
            features = features.to(device)
            target_action = target_action.to(device)
            target_release = target_release.to(device)
            power = power.to(device)
            price = price.to(device)

            optimizer.zero_grad()
            action = model(features)
            release, storage, _, _ = simulate_actions(action, power, config)

            action_weight = 1.0 + 4.0 * (torch.abs(target_action) > 1e-4).float()
            action_loss = torch.mean(action_weight * (action - target_action) ** 2)
            release_loss = torch.mean(((release - target_release) / config["rated_capacity"]) ** 2)
            revenue = torch.mean(torch.sum(release * price, dim=1) / (torch.sum(power * price, dim=1) + 1e-6))
            terminal_loss = torch.mean((storage[:, -1] / capacity) ** 2)
            loss = action_loss + args.release_weight * release_loss - args.revenue_weight * revenue + args.terminal_weight * terminal_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))

        val = evaluate_cove_dv(model, val_loader, config, device)
        scheduler.step(val["model_cove"])
        row = {
            "epoch": epoch,
            "train_loss": float(np.mean(train_losses)),
            "val_action_mse": val["action_mse"],
            "val_release_mse_scaled": val["release_mse_scaled"],
            "val_model_cove": val["model_cove"],
            "val_teacher_cove": val["teacher_cove"],
            "val_baseload_cove": val["baseload_cove"],
            "val_model_improvement_vs_baseload_pct": val["model_improvement_vs_baseload_pct"],
            "lr": optimizer.param_groups[0]["lr"],
        }
        rows.append(row)
        print(
            f"epoch {epoch}: train={row['train_loss']:.4f}, "
            f"val COVE={row['val_model_cove']:.6f}, "
            f"teacher={row['val_teacher_cove']:.6f}, "
            f"improvement={row['val_model_improvement_vs_baseload_pct']:.2f}%"
        )
        if val["model_cove"] < best_val_cove:
            best_val_cove = val["model_cove"]
            torch.save(model.state_dict(), best_path)

    model.load_state_dict(torch.load(best_path, weights_only=True, map_location=device))
    test = evaluate_cove_dv(model, test_loader, config, device)
    original = evaluate_original(Path(args.baseline_model), test_loader, config, device)

    write_rows(out_dir / "cove_dv_metrics.csv", rows)
    summary = {
        "best_val_cove": best_val_cove,
        "test_cove_dv_cove": test["model_cove"],
        "test_teacher_cove": test["teacher_cove"],
        "test_baseload_cove": test["baseload_cove"],
        "test_cove_dv_improvement_vs_baseload_pct": test["model_improvement_vs_baseload_pct"],
        "test_teacher_improvement_vs_baseload_pct": test["teacher_improvement_vs_baseload_pct"],
    }
    if original is not None:
        summary["test_original_cove_nn_cove"] = original["model_cove"]
        summary["test_original_improvement_vs_baseload_pct"] = original["model_improvement_vs_baseload_pct"]
        summary["test_cove_dv_delta_vs_original_cove"] = original["model_cove"] - test["model_cove"]
    pd.DataFrame([summary]).to_csv(out_dir / "cove_dv_summary.csv", index=False)
    with (out_dir / "cove_dv_summary.txt").open("w") as f:
        f.write("COVE-DV forecast-window planner summary\n")
        for key, value in summary.items():
            f.write(f"{key}: {value:.6f}\n")

    print("COVE-DV test metrics:")
    for key, value in test.items():
        print(f"{key}: {value:.6f}")
    if original is not None:
        print("Original COVE-NN on same test split:")
        for key, value in original.items():
            print(f"{key}: {value:.6f}")
    print(f"saved model: {best_path}")
    print(f"saved summary: {out_dir / 'cove_dv_summary.csv'}")


if __name__ == "__main__":
    main()

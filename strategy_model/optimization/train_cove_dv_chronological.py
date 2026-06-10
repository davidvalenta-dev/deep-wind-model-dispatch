"""Train COVE-DV with chronological state-of-charge continuity.

This is the corrected COVE-DV experiment.

The first COVE-DV version treated every 168-hour week as independent. That made
the battery start at zero each week, which can create an unrealistic boundary.

This version fixes that by:
- using chronological train/validation/test splits,
- adding the initial state of charge as an input feature,
- starting each simulated week from that initial state,
- training the model to end each week at the next chronological state, and
- evaluating by carrying model-predicted storage forward week by week.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
OPT_SRC = REPO_ROOT / "strategy_model" / "optimization"
for path in (STRATEGY_SRC, OPT_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import util  # noqa: E402
from train_cove_dv import CoveDVPlanner, cove_value  # noqa: E402


def split_full_sequences(values: np.ndarray, seq_length: int) -> np.ndarray:
    n_seq = len(values) // seq_length
    trimmed = values[: n_seq * seq_length]
    return trimmed.reshape(n_seq, seq_length, *values.shape[1:])


def make_features(data: pd.DataFrame, labels: pd.DataFrame, config: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    power = data["power_generated"].to_numpy(dtype=float)
    price = util.normalize_price(data["lmp"].copy(), config).to_numpy(dtype=float)
    load = data["user_load_zonal"].to_numpy(dtype=float)
    load = load / np.max(load)

    capacity = config["storage_rating"] * config["storage_duration"] * config["num_modules"]
    initial_soc_by_hour = labels["milp_storage"].to_numpy(dtype=float) / capacity

    cols = [
        power / config["rated_capacity"],
        price,
        load,
    ]
    if "datetime" in data.columns:
        dt = pd.to_datetime(data["datetime"])
        hour = dt.dt.hour.to_numpy(dtype=float)
        doy = dt.dt.dayofyear.to_numpy(dtype=float)
        cols.extend(
            [
                np.sin(2 * np.pi * hour / 24),
                np.cos(2 * np.pi * hour / 24),
                np.sin(2 * np.pi * doy / 366),
                np.cos(2 * np.pi * doy / 366),
            ]
        )
    cols.append(initial_soc_by_hour)
    features = np.stack(cols, axis=-1)
    return features, power, price


def make_chronological_dataset(data_path: Path, labels_path: Path, config: dict) -> TensorDataset:
    data = pd.read_csv(data_path)
    labels = pd.read_csv(labels_path)
    if len(data) != len(labels):
        raise ValueError(f"data rows ({len(data)}) and label rows ({len(labels)}) do not match")

    seq_length = config["seq_length"]
    n_seq = len(data) // seq_length
    usable_hours = n_seq * seq_length
    data = data.iloc[:usable_hours].reset_index(drop=True)
    labels = labels.iloc[:usable_hours].reset_index(drop=True)

    features, power, price = make_features(data, labels, config)
    target_action = labels["milp_action"].to_numpy(dtype=float)
    target_release = labels["milp_release"].to_numpy(dtype=float)
    storage = labels["milp_storage"].to_numpy(dtype=float)

    # Start SOC for each week is the first hour's teacher SOC.
    initial_soc = storage[::seq_length][:n_seq]

    # Target final SOC is the next week's starting SOC. The last full week uses
    # the next available hour if present in the original label file.
    full_labels = pd.read_csv(labels_path, usecols=["milp_storage"])
    full_storage = full_labels["milp_storage"].to_numpy(dtype=float)
    final_indices = np.arange(seq_length, (n_seq + 1) * seq_length, seq_length)
    final_soc = np.zeros(n_seq, dtype=float)
    valid = final_indices < len(full_storage)
    final_soc[valid] = full_storage[final_indices[valid]]

    return TensorDataset(
        torch.tensor(split_full_sequences(features, seq_length), dtype=torch.float32),
        torch.tensor(split_full_sequences(target_action[:, None], seq_length).squeeze(-1), dtype=torch.float32),
        torch.tensor(split_full_sequences(target_release[:, None], seq_length).squeeze(-1), dtype=torch.float32),
        torch.tensor(split_full_sequences(power[:, None], seq_length).squeeze(-1), dtype=torch.float32),
        torch.tensor(split_full_sequences(price[:, None], seq_length).squeeze(-1), dtype=torch.float32),
        torch.tensor(initial_soc, dtype=torch.float32),
        torch.tensor(final_soc, dtype=torch.float32),
    )


def chronological_split(dataset: TensorDataset, config: dict) -> tuple[TensorDataset, TensorDataset, TensorDataset]:
    n = len(dataset)
    train_size = int(config["train_percent"] * n)
    val_size = int(config["val_percent"] * n)
    tensors = dataset.tensors

    def subset(start: int, end: int) -> TensorDataset:
        return TensorDataset(*(tensor[start:end] for tensor in tensors))

    return (
        subset(0, train_size),
        subset(train_size, train_size + val_size),
        subset(train_size + val_size, n),
    )


def set_initial_soc_feature(features: torch.Tensor, initial_soc: torch.Tensor, capacity: float) -> torch.Tensor:
    updated = features.clone()
    updated[:, :, -1] = (initial_soc / capacity).unsqueeze(1)
    return updated


def simulate_actions(
    actions: torch.Tensor,
    power: torch.Tensor,
    config: dict,
    initial_storage: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    grid_cap = float(config["rated_capacity"])

    storage = initial_storage.to(actions.device).to(actions.dtype)
    releases = []
    storages = []
    charges = []
    discharges = []

    for t in range(actions.shape[1]):
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


def continuous_baseload(power: np.ndarray, config: dict) -> np.ndarray:
    rating = float(config["storage_rating"] * config["num_modules"])
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    rte = float(util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"]))
    avg = float(np.mean(power))
    storage = 0.0
    released = np.zeros(len(power), dtype=float)

    for i, generation in enumerate(power):
        if generation >= avg:
            charge = min(generation - avg, rating, capacity - storage)
            released[i] = generation - charge
            storage += charge
        else:
            needed_before_rte = (avg - generation) / rte
            discharge = min(needed_before_rte, rating, storage)
            released[i] = generation + rte * discharge
            storage -= discharge
    return released


def flatten(items: list[np.ndarray]) -> np.ndarray:
    if not items:
        return np.array([])
    return np.concatenate([x.reshape(-1) for x in items])


def evaluate_continuous(model: CoveDVPlanner, dataset: TensorDataset, config: dict, device: torch.device) -> dict[str, float]:
    model.eval()
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])
    current_storage = dataset.tensors[5][0:1].clone()
    pred_releases = []
    teacher_releases = []
    powers = []
    prices = []
    final_soc = []

    with torch.no_grad():
        for i in range(len(dataset)):
            features, _, target_release, power, price, _, _ = [tensor[i : i + 1] for tensor in dataset.tensors]
            features = set_initial_soc_feature(features, current_storage, capacity).to(device)
            power = power.to(device)
            action = model(features)
            release, storage, _, _ = simulate_actions(action, power, config, current_storage.to(device))
            current_storage = storage[:, -1].detach().cpu()
            pred_releases.append(release.cpu().numpy())
            teacher_releases.append(target_release.numpy())
            powers.append(power.cpu().numpy())
            prices.append(price.numpy())
            final_soc.append(float(current_storage.item()))

    pred = flatten(pred_releases)
    teacher = flatten(teacher_releases)
    power_flat = flatten(powers)
    price_flat = flatten(prices)
    base = continuous_baseload(power_flat, config)
    model_cove = cove_value(pred, price_flat, config)
    teacher_cove = cove_value(teacher, price_flat, config)
    baseload_cove = cove_value(base, price_flat, config)
    return {
        "model_cove": model_cove,
        "teacher_cove": teacher_cove,
        "baseload_cove": baseload_cove,
        "model_improvement_vs_baseload_pct": (baseload_cove - model_cove) / baseload_cove * 100,
        "teacher_improvement_vs_baseload_pct": (baseload_cove - teacher_cove) / baseload_cove * 100,
        "final_soc_mean_pct": float(np.mean(final_soc) / capacity * 100),
        "final_soc_max_pct": float(np.max(final_soc) / capacity * 100),
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train chronological COVE-DV.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--labels", default=str(REPO_ROOT / "strategy_model" / "optimization" / "milp_teacher_labels_full_run_016.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "strategy_model" / "optimization" / "cove_dv_chronological_run_016"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-size", type=int, default=256)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--release-weight", type=float, default=5.0)
    parser.add_argument("--terminal-weight", type=float, default=2.0)
    parser.add_argument("--storage-type", default=None)
    parser.add_argument("--storage-rating", type=float, default=None)
    parser.add_argument("--storage-duration", type=float, default=None)
    args = parser.parse_args()

    np.random.seed(0)
    torch.manual_seed(0)
    config = util.load_config(args.config)
    if args.storage_type is not None:
        config["storage_type"] = args.storage_type
    if args.storage_rating is not None:
        config["storage_rating"] = int(args.storage_rating) if args.storage_rating.is_integer() else args.storage_rating
    if args.storage_duration is not None:
        config["storage_duration"] = int(args.storage_duration) if args.storage_duration.is_integer() else args.storage_duration
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = make_chronological_dataset(Path(args.data), Path(args.labels), config)
    train_set, val_set, test_set = chronological_split(dataset, config)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)

    input_size = dataset.tensors[0].shape[-1]
    model = CoveDVPlanner(input_size, args.hidden_size, args.num_layers, args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=4)
    capacity = float(config["storage_rating"] * config["storage_duration"] * config["num_modules"])

    rows = []
    best_val_cove = float("inf")
    best_path = out_dir / "cove_dv_chronological_model.pth"

    print(f"chronological sequences: train={len(train_set)}, val={len(val_set)}, test={len(test_set)}")
    print(f"COVE-DV chronological input features: {input_size}")

    for epoch in range(args.epochs):
        model.train()
        train_losses = []
        for features, target_action, target_release, power, price, initial_soc, final_soc in train_loader:
            features = features.to(device)
            target_action = target_action.to(device)
            target_release = target_release.to(device)
            power = power.to(device)
            initial_soc = initial_soc.to(device)
            final_soc = final_soc.to(device)

            optimizer.zero_grad()
            action = model(features)
            release, storage, _, _ = simulate_actions(action, power, config, initial_soc)

            action_weight = 1.0 + 4.0 * (torch.abs(target_action) > 1e-4).float()
            action_loss = torch.mean(action_weight * (action - target_action) ** 2)
            release_loss = torch.mean(((release - target_release) / config["rated_capacity"]) ** 2)
            terminal_loss = torch.mean(((storage[:, -1] - final_soc) / capacity) ** 2)
            loss = action_loss + args.release_weight * release_loss + args.terminal_weight * terminal_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))

        val = evaluate_continuous(model, val_set, config, device)
        scheduler.step(val["model_cove"])
        row = {
            "epoch": epoch,
            "train_loss": float(np.mean(train_losses)),
            "val_model_cove": val["model_cove"],
            "val_teacher_cove": val["teacher_cove"],
            "val_baseload_cove": val["baseload_cove"],
            "val_model_improvement_vs_baseload_pct": val["model_improvement_vs_baseload_pct"],
            "val_final_soc_mean_pct": val["final_soc_mean_pct"],
            "val_final_soc_max_pct": val["final_soc_max_pct"],
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
    test = evaluate_continuous(model, test_set, config, device)
    write_rows(out_dir / "cove_dv_chronological_metrics.csv", rows)
    summary = {
        "best_val_cove": best_val_cove,
        "test_cove_dv_chronological_cove": test["model_cove"],
        "test_teacher_cove": test["teacher_cove"],
        "test_baseload_cove": test["baseload_cove"],
        "test_cove_dv_chronological_improvement_vs_baseload_pct": test["model_improvement_vs_baseload_pct"],
        "test_teacher_improvement_vs_baseload_pct": test["teacher_improvement_vs_baseload_pct"],
        "test_final_soc_mean_pct": test["final_soc_mean_pct"],
        "test_final_soc_max_pct": test["final_soc_max_pct"],
    }
    pd.DataFrame([summary]).to_csv(out_dir / "cove_dv_chronological_summary.csv", index=False)
    with (out_dir / "cove_dv_chronological_summary.txt").open("w") as f:
        for key, value in summary.items():
            f.write(f"{key}: {value:.6f}\n")

    print("COVE-DV chronological test metrics:")
    for key, value in summary.items():
        print(f"{key}: {value:.6f}")
    print(f"saved model: {best_path}")


if __name__ == "__main__":
    main()

"""Train COVE-NN to imitate optimizer teacher labels.

This is an imitation-learning experiment:
- inputs: wind power, normalized price, normalized load
- teacher label: optimized release from dispatch_teacher_labels_full_run_016.csv
- model: the existing VFNN_2 COVE-NN architecture

It does not replace the original COVE-loss training. It tests whether optimizer
labels can teach the neural network a better dispatch policy.
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
if str(STRATEGY_SRC) not in sys.path:
    sys.path.insert(0, str(STRATEGY_SRC))

import util  # noqa: E402
from classical_strategies import baseload  # noqa: E402
from model import VFNN_2  # noqa: E402


def split_sequences(values: np.ndarray, seq_length: int) -> np.ndarray:
    split_idxs = np.arange(0, len(values), seq_length)
    return np.array(np.split(values, split_idxs)[1:-1])


def flatten_batches(items: list[np.ndarray]) -> np.ndarray:
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


def make_dataset(data_path: Path, labels_path: Path, config: dict) -> TensorDataset:
    data = pd.read_csv(data_path)
    labels = pd.read_csv(labels_path)
    if len(data) != len(labels):
        raise ValueError(f"data rows ({len(data)}) and label rows ({len(labels)}) do not match")

    price = util.normalize_price(data["lmp"].copy(), config).to_numpy(dtype=float)
    load = data["user_load_zonal"].to_numpy(dtype=float)
    load = load / np.max(load)
    power = data["power_generated"].to_numpy(dtype=float)
    target_release = labels["optimal_release"].to_numpy(dtype=float)

    seq_length = config["seq_length"]
    power_seq = split_sequences(power, seq_length)
    price_seq = split_sequences(price, seq_length)
    load_seq = split_sequences(load, seq_length)
    target_seq = split_sequences(target_release, seq_length)

    inputs = np.stack([power_seq, price_seq, load_seq], axis=-1)
    return TensorDataset(
        torch.tensor(inputs, dtype=torch.float32),
        torch.tensor(target_seq, dtype=torch.float32),
        torch.tensor(power_seq, dtype=torch.float32),
        torch.tensor(price_seq, dtype=torch.float32),
    )


def split_dataset(dataset: TensorDataset, config: dict) -> tuple[TensorDataset, TensorDataset, TensorDataset]:
    n = len(dataset)
    train_size = int(config["train_percent"] * n)
    val_size = int(config["val_percent"] * n)
    torch.manual_seed(0)
    indices = torch.randperm(n)
    tensors = dataset.tensors

    def subset(idx: torch.Tensor) -> TensorDataset:
        return TensorDataset(*(tensor[idx] for tensor in tensors))

    train = subset(indices[:train_size])
    val = subset(indices[train_size : train_size + val_size])
    test = subset(indices[train_size + val_size :])
    return train, val, test


def make_model(config: dict) -> VFNN_2:
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


def evaluate_model(model: torch.nn.Module, loader: DataLoader, config: dict) -> dict[str, float]:
    model.eval()
    criterion = torch.nn.MSELoss()
    losses: list[float] = []
    releases: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    powers: list[np.ndarray] = []
    prices: list[np.ndarray] = []

    with torch.no_grad():
        for inputs, target, power, price in loader:
            pred = model(inputs)
            released = pred[:, :, 0]
            loss = criterion(released, target)
            losses.append(float(loss.detach().cpu()))
            releases.append(released.detach().cpu().numpy())
            targets.append(target.detach().cpu().numpy())
            powers.append(power.detach().cpu().numpy())
            prices.append(price.detach().cpu().numpy())

    release_flat = flatten_batches(releases)
    target_flat = flatten_batches(targets)
    power_flat = flatten_batches(powers)
    price_flat = flatten_batches(prices)

    rte = util.get_rte(config["storage_type"], config["storage_rating"], config["storage_duration"])
    baseload_parts = []
    for power_batch in powers:
        for seq in power_batch:
            base_release, *_ = baseload(
                seq,
                config["storage_rating"] * config["num_modules"],
                config["storage_rating"] * config["storage_duration"] * config["num_modules"],
                rte,
            )
            baseload_parts.append(base_release)
    baseload_flat = np.concatenate(baseload_parts)

    model_cove = cove_value(release_flat, price_flat, config)
    teacher_cove = cove_value(target_flat, price_flat, config)
    baseload_cove = cove_value(baseload_flat, price_flat, config)
    return {
        "mse": float(np.mean(losses)),
        "model_cove": model_cove,
        "teacher_cove": teacher_cove,
        "baseload_cove": baseload_cove,
        "model_improvement_vs_baseload_pct": (baseload_cove - model_cove) / baseload_cove * 100,
        "teacher_improvement_vs_baseload_pct": (baseload_cove - teacher_cove) / baseload_cove * 100,
    }


def save_metrics(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train COVE-NN on optimizer teacher labels.")
    parser.add_argument("--data", default=str(REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"))
    parser.add_argument("--labels", default=str(REPO_ROOT / "strategy_model" / "optimization" / "dispatch_teacher_labels_full_run_016.csv"))
    parser.add_argument("--config", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "config_run_016.yaml"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "strategy_model" / "optimization" / "teacher_policy_run_016"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--baseline-model", default=str(REPO_ROOT / "strategy_model" / "test" / "run_016" / "model_run_016.pth"))
    parser.add_argument("--init-model", default=None, help="Optional model checkpoint to fine-tune from.")
    args = parser.parse_args()

    np.random.seed(0)
    torch.manual_seed(0)
    config = util.load_config(args.config)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = make_dataset(Path(args.data), Path(args.labels), config)
    train_set, val_set, test_set = split_dataset(dataset, config)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_set, batch_size=args.batch_size, shuffle=False)

    model = make_model(config)
    if args.init_model:
        model.load_state_dict(torch.load(args.init_model, weights_only=True))
        print(f"initialized from: {args.init_model}")
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    criterion = torch.nn.MSELoss()

    rows: list[dict[str, float | int | str]] = []
    best_val = float("inf")
    best_path = out_dir / "teacher_policy_model.pth"

    print(f"training sequences: {len(train_set)}")
    print(f"validation sequences: {len(val_set)}")
    print(f"test sequences: {len(test_set)}")

    for epoch in range(args.epochs):
        model.train()
        train_losses: list[float] = []
        for inputs, target, _, _ in train_loader:
            optimizer.zero_grad()
            pred = model(inputs)
            released = pred[:, :, 0]
            loss = criterion(released, target)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach().cpu()))

        val_metrics = evaluate_model(model, val_loader, config)
        row = {
            "epoch": epoch,
            "train_mse": float(np.mean(train_losses)),
            "val_mse": val_metrics["mse"],
            "val_model_cove": val_metrics["model_cove"],
            "val_teacher_cove": val_metrics["teacher_cove"],
            "val_baseload_cove": val_metrics["baseload_cove"],
            "val_model_improvement_vs_baseload_pct": val_metrics["model_improvement_vs_baseload_pct"],
        }
        rows.append(row)
        print(
            f"epoch {epoch}: train MSE={row['train_mse']:.3f}, "
            f"val MSE={row['val_mse']:.3f}, "
            f"val COVE={row['val_model_cove']:.6f}, "
            f"improvement={row['val_model_improvement_vs_baseload_pct']:.2f}%"
        )
        if val_metrics["mse"] < best_val:
            best_val = val_metrics["mse"]
            torch.save(model.state_dict(), best_path)

    model.load_state_dict(torch.load(best_path, weights_only=True))
    test_metrics = evaluate_model(model, test_loader, config)
    print("teacher-trained test metrics:")
    for key, value in test_metrics.items():
        print(f"{key}: {value:.6f}")

    if args.baseline_model and Path(args.baseline_model).exists():
        baseline = make_model(config)
        baseline.load_state_dict(torch.load(args.baseline_model, weights_only=True))
        baseline_metrics = evaluate_model(baseline, test_loader, config)
        print("original run_016 test metrics on same teacher split:")
        for key, value in baseline_metrics.items():
            print(f"{key}: {value:.6f}")
    else:
        baseline_metrics = None

    metrics_path = out_dir / "teacher_policy_metrics.csv"
    save_metrics(metrics_path, rows)
    summary_path = out_dir / "teacher_policy_summary.txt"
    with summary_path.open("w") as f:
        f.write("Teacher-trained COVE-NN summary\n")
        f.write(f"epochs: {args.epochs}\n")
        f.write(f"train sequences: {len(train_set)}\n")
        f.write(f"validation sequences: {len(val_set)}\n")
        f.write(f"test sequences: {len(test_set)}\n")
        f.write("\nTeacher-trained test metrics:\n")
        for key, value in test_metrics.items():
            f.write(f"{key}: {value:.6f}\n")
        if baseline_metrics is not None:
            f.write("\nOriginal run_016 test metrics on same split:\n")
            for key, value in baseline_metrics.items():
                f.write(f"{key}: {value:.6f}\n")

    print(f"saved model: {best_path}")
    print(f"saved metrics: {metrics_path}")
    print(f"saved summary: {summary_path}")


if __name__ == "__main__":
    main()

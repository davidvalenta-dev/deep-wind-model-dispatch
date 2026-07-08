import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURE_NAMES = [
    "bias",
    "speed",
    "speed_sq",
    "speed_cu",
    "lag_power_1h",
    "lag_power_2h",
    "lag_power_3h",
    "lag_power_24h",
    "hour_sin",
    "hour_cos",
    "day_sin",
    "day_cos",
]


def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mae(y_true, y_pred):
    return float(np.mean(np.abs(y_true - y_pred)))


def chronological_slices(n, train_frac=0.7, val_frac=0.2):
    train_end = int(train_frac * n)
    val_end = train_end + int(val_frac * n)
    return {
        "train": slice(0, train_end),
        "validation": slice(train_end, val_end),
        "test": slice(val_end, n),
    }


def build_causal_features(df, max_lag=24):
    if not {"datetime", "speed", "power"}.issubset(df.columns):
        raise ValueError("Expected columns: datetime, speed, power")

    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.dropna(subset=["datetime", "speed", "power"]).reset_index(drop=True)

    power_mw = df["power"].to_numpy(dtype=float)
    power_scale = float(np.max(power_mw))
    power = power_mw / power_scale
    speed = df["speed"].to_numpy(dtype=float)

    rows = []
    targets = []
    timestamps = []
    raw_power = []

    for i in range(max_lag, len(df)):
        dt = df.loc[i, "datetime"]
        rows.append(
            [
                1.0,
                speed[i],
                speed[i] ** 2,
                speed[i] ** 3,
                power[i - 1],
                power[i - 2],
                power[i - 3],
                power[i - 24],
                np.sin(2 * np.pi * dt.hour / 24),
                np.cos(2 * np.pi * dt.hour / 24),
                np.sin(2 * np.pi * dt.dayofyear / 365.25),
                np.cos(2 * np.pi * dt.dayofyear / 365.25),
            ]
        )
        targets.append(power[i])
        timestamps.append(dt)
        raw_power.append(power_mw[i])

    return (
        np.asarray(rows, dtype=float),
        np.asarray(targets, dtype=float),
        pd.Series(timestamps, name="datetime"),
        np.asarray(raw_power, dtype=float),
        power_scale,
    )


def fit_ridge(X, y, alpha):
    regularizer = alpha * np.eye(X.shape[1])
    regularizer[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + regularizer, X.T @ y)


def fit_speed_power_curve(X, y):
    speed = X[:, FEATURE_NAMES.index("speed")]
    return np.polyfit(speed, y, deg=5)


def predict_speed_power_curve(coef, X):
    speed = X[:, FEATURE_NAMES.index("speed")]
    return np.clip(np.polyval(coef, speed), 0, 1)


def evaluate_predictions(name, y, pred, slices, power_scale):
    rows = []
    for split, split_slice in slices.items():
        y_split = y[split_slice]
        pred_split = pred[split_slice]
        rows.append(
            {
                "model": name,
                "split": split,
                "normalized_rmse": rmse(y_split, pred_split),
                "normalized_mae": mae(y_split, pred_split),
                "rmse_mw": rmse(y_split * power_scale, pred_split * power_scale),
                "mae_mw": mae(y_split * power_scale, pred_split * power_scale),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Train a causal short-term wind-power forecast using speed, time, and previous measured power."
    )
    parser.add_argument(
        "--dataset",
        default="../../data/processed/dataset_14-23.csv",
        help="CSV with datetime, speed, and power columns.",
    )
    parser.add_argument("--alpha", type=float, default=1e-6, help="Ridge regularization strength.")
    parser.add_argument("--output-dir", default="../evaluation", help="Directory for metrics and prediction CSVs.")
    args = parser.parse_args()

    df = pd.read_csv(args.dataset)
    X, y, timestamps, power_mw, power_scale = build_causal_features(df)
    slices = chronological_slices(len(y))

    train_slice = slices["train"]
    weights = fit_ridge(X[train_slice], y[train_slice], alpha=args.alpha)
    causal_pred = np.clip(X @ weights, 0, 1)

    speed_curve = fit_speed_power_curve(X[train_slice], y[train_slice])
    speed_curve_pred = predict_speed_power_curve(speed_curve, X)

    persistence_pred = X[:, FEATURE_NAMES.index("lag_power_1h")]
    train_mean_pred = np.full_like(y, np.mean(y[train_slice]))

    metrics = []
    metrics.extend(evaluate_predictions("causal_lag_ridge", y, causal_pred, slices, power_scale))
    metrics.extend(evaluate_predictions("speed_power_curve", y, speed_curve_pred, slices, power_scale))
    metrics.extend(evaluate_predictions("lag1_persistence", y, persistence_pred, slices, power_scale))
    metrics.extend(evaluate_predictions("train_mean", y, train_mean_pred, slices, power_scale))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "causal_lag_forecast_metrics.csv"
    predictions_path = output_dir / "causal_lag_forecast_predictions.csv"

    pd.DataFrame(metrics).to_csv(metrics_path, index=False)
    pd.DataFrame(
        {
            "datetime": timestamps,
            "actual_power_mw": power_mw,
            "causal_lag_prediction_mw": causal_pred * power_scale,
            "speed_power_curve_prediction_mw": speed_curve_pred * power_scale,
            "lag1_persistence_prediction_mw": persistence_pred * power_scale,
        }
    ).to_csv(predictions_path, index=False)

    print(f"Features: {', '.join(FEATURE_NAMES)}")
    print(pd.DataFrame(metrics).to_string(index=False))
    print(f"Saved metrics to {metrics_path}")
    print(f"Saved predictions to {predictions_path}")


if __name__ == "__main__":
    main()

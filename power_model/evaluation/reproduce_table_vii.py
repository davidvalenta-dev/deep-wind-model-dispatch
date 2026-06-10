import numpy as np
import pandas as pd
from pathlib import Path


def jensen_shannon_distance(p, q):
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    p = p / p.sum()
    q = q / q.sum()
    midpoint = 0.5 * (p + q)

    def kl_divergence(a, b):
        mask = a > 0
        return np.sum(a[mask] * np.log(a[mask] / b[mask]))

    return np.sqrt(
        0.5 * kl_divergence(p, midpoint) + 0.5 * kl_divergence(q, midpoint)
    )


def metrics(speed, true_power, predicted_power):
    normalized_true = true_power / np.max(true_power)
    normalized_predicted = predicted_power / np.max(predicted_power)

    rmse = np.sqrt(np.mean((normalized_true - normalized_predicted) ** 2))
    cross_correlation = np.corrcoef(normalized_true, normalized_predicted)[0, 1]

    true_hist, _, _ = np.histogram2d(speed, true_power, bins=50)
    predicted_hist, _, _ = np.histogram2d(speed, predicted_power, bins=50)
    similarity = 1 - jensen_shannon_distance(
        true_hist.flatten(), predicted_hist.flatten()
    )

    return rmse, cross_correlation, similarity


def main():
    csv_path = Path(__file__).resolve().parent / "palouse_results.csv"
    df = pd.read_csv(csv_path)
    models = {
        "NWPDB": "nwpdb",
        "PLUSWIND": "pluswind",
        "NQF-RNN": "rnn_preds",
    }

    print("Model,RMSE,Cross Correlation,Similarity")
    for model_name, column in models.items():
        rmse, cross_correlation, similarity = metrics(
            df["speed"].to_numpy(),
            df["power"].to_numpy(),
            df[column].to_numpy(),
        )
        print(f"{model_name},{rmse:.3f},{cross_correlation:.3f},{similarity:.3f}")


if __name__ == "__main__":
    main()

"""Statistical and sensitivity analysis for the forecast dispatch backtest."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY_SRC = REPO_ROOT / "strategy_model" / "src"
OPTIMIZATION_DIR = REPO_ROOT / "strategy_model" / "optimization"
for module_path in (STRATEGY_SRC, OPTIMIZATION_DIR):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

import util  # noqa: E402
import forecast_backtest_rolling_horizons as forecast  # noqa: E402
from rolling_horizon_gurobi_dispatch import continuous_baseload, fixed_costs  # noqa: E402


HORIZONS = (24, 48, 72, 168)
COLORS = {24: "#2563EB", 48: "#0F766E", 72: "#B45309", 168: "#7C3AED"}


def load_base_config(config_path: Path) -> dict:
    config = util.load_config(config_path)
    config.update(
        {
            "storage_type": "caes",
            "storage_rating": 100,
            "storage_duration": 24,
            "num_modules": 1,
            "rated_capacity": 249,
        }
    )
    return config


def load_backtest_labels(result_dir: Path) -> dict[int, pd.DataFrame]:
    labels = {}
    for horizon in HORIZONS:
        frame = pd.read_csv(
            result_dir / f"forecast_dispatch_{horizon}h.csv",
            parse_dates=["datetime"],
        )
        labels[horizon] = frame
    return labels


def yearly_results(
    labels: dict[int, pd.DataFrame], config: dict, initial_soc: float
) -> pd.DataFrame:
    reference = labels[24]
    power = reference["actual_generation"].to_numpy(dtype=float)
    price = reference["actual_price"].to_numpy(dtype=float)
    baseload_release = continuous_baseload(power, config, initial_soc=initial_soc)
    baseload = pd.DataFrame(
        {
            "datetime": reference["datetime"],
            "actual_price": price,
            "baseload_delivered": baseload_release,
        }
    )
    _, dispatch_cost = fixed_costs(config)
    rows = []
    complete_years = list(range(2014, 2023))

    for year in complete_years:
        base_year = baseload[baseload["datetime"].dt.year == year]
        base_revenue = float(
            np.sum(
                base_year["baseload_delivered"].to_numpy()
                * base_year["actual_price"].to_numpy()
            )
        )
        base_cove = dispatch_cost / base_revenue
        for horizon, frame in labels.items():
            selected = frame[frame["datetime"].dt.year == year]
            revenue = float(
                np.sum(
                    selected["realized_delivered"].to_numpy()
                    * selected["actual_price"].to_numpy()
                )
            )
            cove = dispatch_cost / revenue
            rows.append(
                {
                    "year": year,
                    "horizon_hours": horizon,
                    "hours": len(selected),
                    "revenue_metric": revenue,
                    "baseload_revenue_metric": base_revenue,
                    "cove": cove,
                    "baseload_cove": base_cove,
                    "improvement_vs_baseload_pct": (
                        (base_cove - cove) / base_cove * 100
                    ),
                }
            )
    return pd.DataFrame(rows)


def bootstrap_ci(values: np.ndarray, seed: int = 2026, draws: int = 20000):
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return (
        float(values.mean()),
        float(np.quantile(samples, 0.025)),
        float(np.quantile(samples, 0.975)),
    )


def exact_sign_flip_pvalue(values: np.ndarray) -> float:
    observed = abs(float(values.mean()))
    means = []
    for signs in itertools.product((-1.0, 1.0), repeat=len(values)):
        means.append(abs(float(np.mean(values * np.asarray(signs)))))
    means = np.asarray(means)
    return float(np.mean(means >= observed - 1e-12))


def statistical_tests(yearly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pivot_value = yearly.pivot(
        index="year", columns="horizon_hours", values="revenue_metric"
    )
    pivot_improvement = yearly.pivot(
        index="year",
        columns="horizon_hours",
        values="improvement_vs_baseload_pct",
    )

    for comparison in (24, 72, 168):
        value_difference = (
            pivot_value[48].to_numpy() - pivot_value[comparison].to_numpy()
        )
        improvement_difference = (
            pivot_improvement[48].to_numpy()
            - pivot_improvement[comparison].to_numpy()
        )
        value_mean, value_low, value_high = bootstrap_ci(value_difference)
        imp_mean, imp_low, imp_high = bootstrap_ci(improvement_difference)
        rows.append(
            {
                "comparison": f"48h minus {comparison}h",
                "years": len(value_difference),
                "48h_wins": int(np.sum(value_difference > 0)),
                "ties": int(np.sum(np.isclose(value_difference, 0))),
                "mean_value_difference": value_mean,
                "value_difference_ci95_low": value_low,
                "value_difference_ci95_high": value_high,
                "mean_improvement_difference_pct_points": imp_mean,
                "improvement_difference_ci95_low": imp_low,
                "improvement_difference_ci95_high": imp_high,
                "exact_paired_sign_flip_pvalue": exact_sign_flip_pvalue(
                    value_difference
                ),
            }
        )
    return pd.DataFrame(rows)


def horizon_win_counts(yearly: pd.DataFrame) -> pd.DataFrame:
    winners = (
        yearly.sort_values(["year", "cove"])
        .groupby("year", as_index=False)
        .first()[["year", "horizon_hours", "cove"]]
    )
    counts = (
        winners["horizon_hours"]
        .value_counts()
        .reindex(HORIZONS, fill_value=0)
        .rename_axis("horizon_hours")
        .reset_index(name="years_won")
    )
    winning_years = (
        winners.groupby("horizon_hours")["year"]
        .apply(lambda values: ",".join(str(int(value)) for value in values))
        .rename("winning_years")
        .reset_index()
    )
    return counts.merge(winning_years, on="horizon_hours", how="left").fillna(
        {"winning_years": ""}
    )


def persistence_forecast_matrix(
    values: np.ndarray, origins: np.ndarray, max_horizon: int
) -> np.ndarray:
    result = np.empty((len(origins), max_horizon), dtype=float)
    for row, origin in enumerate(origins):
        for lead in range(max_horizon):
            hour_in_day = lead % 24
            result[row, lead] = np.mean(
                [
                    values[origin - 24 * day + hour_in_day]
                    for day in range(1, 8)
                ]
            )
    return result


def nqf_diagnostic_matrix(
    df: pd.DataFrame,
    origins: np.ndarray,
    max_horizon: int,
    nqf_path: Path,
) -> tuple[np.ndarray, np.ndarray]:
    nqf = pd.read_csv(nqf_path, parse_dates=["datetime"])
    prediction_by_time = pd.Series(
        nqf["preds"].to_numpy(dtype=float), index=nqf["datetime"]
    )
    valid_rows = []
    matrices = []
    for row_index, origin in enumerate(origins):
        target_times = df["datetime"].iloc[origin : origin + max_horizon]
        predictions = prediction_by_time.reindex(target_times).to_numpy()
        if len(predictions) == max_horizon and np.isfinite(predictions).all():
            valid_rows.append(row_index)
            matrices.append(predictions)
    return np.asarray(matrices, dtype=float), np.asarray(valid_rows, dtype=int)


def run_model_comparison(
    df: pd.DataFrame,
    origins: np.ndarray,
    generation_forecasts: np.ndarray,
    price_forecasts: np.ndarray,
    config: dict,
    initial_soc: float,
    min_soc_frac: float,
    max_soc_frac: float,
    nqf_path: Path,
) -> pd.DataFrame:
    nqf_matrix, valid_rows = nqf_diagnostic_matrix(df, origins, 48, nqf_path)
    common_origins = origins[valid_rows]
    ridge_matrix = generation_forecasts[valid_rows]
    common_price = price_forecasts[valid_rows]
    persistence_matrix = persistence_forecast_matrix(
        df["power_generated"].to_numpy(dtype=float), common_origins, 168
    )
    candidates = {
        "causal_ridge": ridge_matrix,
        "causal_7day_profile": persistence_matrix,
        "NQF_RNN_target_speed_diagnostic": np.pad(
            nqf_matrix, ((0, 0), (0, 120)), mode="edge"
        ),
    }
    rows = []
    for name, matrix in candidates.items():
        _, summary = forecast.run_horizon(
            df,
            int(common_origins[0]),
            common_origins,
            matrix,
            common_price,
            48,
            config,
            initial_soc,
            min_soc_frac,
            max_soc_frac,
            0.0,
            perfect_information=False,
        )
        summary["wind_forecast_model"] = name
        summary["causal_operational_forecast"] = name != "NQF_RNN_target_speed_diagnostic"
        rows.append(summary)
    return pd.DataFrame(rows)


def run_sensitivities(
    df: pd.DataFrame,
    origins: np.ndarray,
    generation_forecasts: np.ndarray,
    price_forecasts: np.ndarray,
    base_config: dict,
    min_soc_frac: float,
    max_soc_frac: float,
) -> pd.DataFrame:
    rows = []

    for duration in (10, 24, 100):
        config = dict(base_config)
        config["storage_duration"] = duration
        initial_soc = config["storage_rating"] * duration * 0.6
        _, summary = forecast.run_horizon(
            df,
            int(origins[0]),
            origins,
            generation_forecasts,
            price_forecasts,
            48,
            config,
            initial_soc,
            min_soc_frac,
            max_soc_frac,
            0.0,
            perfect_information=False,
        )
        rows.append(
            {
                "sensitivity": "storage_duration_hours",
                "value": duration,
                **summary,
            }
        )

    original_get_rte = util.get_rte
    for rte in (0.45, 0.55, 0.65):
        util.get_rte = lambda storage_type, rating, duration, rte=rte: rte
        try:
            _, summary = forecast.run_horizon(
                df,
                int(origins[0]),
                origins,
                generation_forecasts,
                price_forecasts,
                48,
                dict(base_config),
                1440.0,
                min_soc_frac,
                max_soc_frac,
                0.0,
                perfect_information=False,
            )
        finally:
            util.get_rte = original_get_rte
        rows.append(
            {
                "sensitivity": "round_trip_efficiency",
                "value": rte,
                **summary,
            }
        )

    base_training_mean = float(
        np.minimum(
            df.loc[df["datetime"] < pd.Timestamp("2014-01-01"), "lmp"].to_numpy(),
            1000,
        ).mean()
    )
    original_price = df["price_normalized"].copy()
    for price_cap in (100, 500, 1000):
        config = dict(base_config)
        normalized_cap = price_cap / base_training_mean
        clipped_forecast = np.clip(
            price_forecasts, -2.0, normalized_cap
        )
        clipped_df = df.copy()
        clipped_df["price_normalized"] = np.minimum(
            clipped_df["lmp"].to_numpy(dtype=float), price_cap
        ) / base_training_mean
        _, summary = forecast.run_horizon(
            clipped_df,
            int(origins[0]),
            origins,
            generation_forecasts,
            clipped_forecast,
            48,
            config,
            1440.0,
            min_soc_frac,
            max_soc_frac,
            0.0,
            perfect_information=False,
        )
        rows.append(
            {
                "sensitivity": "price_cap_dollars_per_mwh",
                "value": price_cap,
                **summary,
            }
        )
    df["price_normalized"] = original_price
    return pd.DataFrame(rows)


def style_axis(axis):
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    axis.set_axisbelow(True)


def save_figures(
    yearly: pd.DataFrame,
    tests: pd.DataFrame,
    model_comparison: pd.DataFrame,
    sensitivity: pd.DataFrame,
    output_dir: Path,
):
    fig, axis = plt.subplots(figsize=(10, 5.5), dpi=220)
    for horizon in HORIZONS:
        selected = yearly[yearly["horizon_hours"] == horizon]
        axis.plot(
            selected["year"],
            selected["improvement_vs_baseload_pct"],
            marker="o",
            linewidth=2,
            label=f"{horizon} h",
            color=COLORS[horizon],
        )
    axis.set_ylabel("COVE improvement vs baseload (%)")
    axis.set_title("Year-by-year out-of-sample dispatch performance", fontweight="bold")
    axis.legend(frameon=False, ncol=4)
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_01_yearly_horizon_results.png", bbox_inches="tight")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 5), dpi=220)
    y = np.arange(len(tests))
    means = tests["mean_improvement_difference_pct_points"].to_numpy()
    low = means - tests["improvement_difference_ci95_low"].to_numpy()
    high = tests["improvement_difference_ci95_high"].to_numpy() - means
    axis.errorbar(
        means,
        y,
        xerr=np.vstack([low, high]),
        fmt="o",
        color="#0F766E",
        ecolor="#64748B",
        capsize=5,
        linewidth=2,
    )
    axis.axvline(0, color="#111827", linestyle="--", linewidth=1)
    axis.set_yticks(y, tests["comparison"])
    axis.set_xlabel("48 h improvement advantage (percentage points)")
    axis.set_title("Paired yearly bootstrap confidence intervals", fontweight="bold")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_02_48h_confidence_intervals.png", bbox_inches="tight")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(9, 5), dpi=220)
    models = model_comparison["wind_forecast_model"].replace(
        {
            "causal_ridge": "Causal ridge",
            "causal_7day_profile": "7-day profile",
            "NQF_RNN_target_speed_diagnostic": "NQF-RNN diagnostic",
        }
    )
    bars = axis.bar(models, model_comparison["improvement_vs_baseload_pct"], color=["#2563EB", "#0F766E", "#B45309"])
    for bar, value in zip(bars, model_comparison["improvement_vs_baseload_pct"]):
        axis.text(bar.get_x() + bar.get_width() / 2, value + 0.15, f"{value:.2f}%", ha="center", fontweight="bold")
    axis.set_ylabel("COVE improvement vs baseload (%)")
    axis.set_title("Wind-forecast model comparison at a 48-hour horizon", fontweight="bold")
    style_axis(axis)
    fig.tight_layout()
    fig.savefig(output_dir / "figure_03_forecast_model_comparison.png", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), dpi=220)
    panels = [
        ("storage_duration_hours", "Storage duration (h)", axes[0]),
        ("round_trip_efficiency", "Round-trip efficiency", axes[1]),
        ("price_cap_dollars_per_mwh", "Price cap ($/MWh)", axes[2]),
    ]
    for sensitivity_name, xlabel, axis in panels:
        selected = sensitivity[sensitivity["sensitivity"] == sensitivity_name]
        axis.plot(
            selected["value"],
            selected["cove"],
            marker="o",
            linewidth=2.5,
            color="#2563EB",
        )
        axis.set_xlabel(xlabel)
        axis.set_ylabel("COVE (lower is better)")
        style_axis(axis)
    fig.suptitle("48-hour COVE sensitivity (lower is better)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_dir / "figure_04_sensitivity_analysis.png", bbox_inches="tight")
    plt.close(fig)


def write_summary(
    yearly: pd.DataFrame,
    tests: pd.DataFrame,
    win_counts: pd.DataFrame,
    model_comparison: pd.DataFrame,
    sensitivity: pd.DataFrame,
    output_dir: Path,
):
    complete_year_wins = (
        yearly.sort_values(["year", "cove"]).groupby("year").first()["horizon_hours"]
    )
    best_model = model_comparison.sort_values("cove").iloc[0]
    lines = [
        "# Statistical Robustness and Sensitivity Results",
        "",
        "## Year-by-year result",
        "",
        f"The 48-hour horizon won {int((complete_year_wins == 48).sum())} of {len(complete_year_wins)} complete test years (2014-2022).",
        "",
        "## Paired statistical tests",
        "",
    ]
    for _, row in tests.iterrows():
        lines.append(
            f"- {row['comparison']}: 48 h won {int(row['48h_wins'])}/{int(row['years'])} years; "
            f"mean advantage {row['mean_improvement_difference_pct_points']:.3f} percentage points; "
            f"95% bootstrap CI [{row['improvement_difference_ci95_low']:.3f}, {row['improvement_difference_ci95_high']:.3f}]; "
            f"exact paired sign-flip p={row['exact_paired_sign_flip_pvalue']:.4f}."
        )
    lines.extend(
        [
            "",
            "A confidence interval crossing zero means the present nine-year sample does not establish statistical significance at the 5% level, even when the aggregate result favors 48 hours.",
            "",
            "Because the 48-hour horizon was selected after inspecting this same backtest, these intervals and p-values are exploratory evidence rather than an independent confirmatory test.",
            "",
            "## Forecast-model comparison",
            "",
        ]
    )
    for _, row in model_comparison.iterrows():
        caveat = (
            " (diagnostic only: uses target-hour wind speed and is not a deployable causal forecast)"
            if not row["causal_operational_forecast"]
            else ""
        )
        lines.append(
            f"- {row['wind_forecast_model']}: COVE {row['cove']:.4f}, "
            f"improvement {row['improvement_vs_baseload_pct']:.2f}%{caveat}."
        )
    lines.extend(
        [
            "",
            f"Best diagnostic model in the common-period comparison: {best_model['wind_forecast_model']}.",
            "",
            "## Sensitivity analysis",
            "",
        ]
    )
    for sensitivity_name, selected in sensitivity.groupby("sensitivity"):
        lines.append(f"### {sensitivity_name}")
        lines.append("")
        for _, row in selected.iterrows():
            lines.append(
                f"- {row['value']}: COVE {row['cove']:.4f}; "
                f"improvement {row['improvement_vs_baseload_pct']:.2f}%."
            )
        lines.append("")
    lines.extend(
        [
            "Sensitivity interpretation:",
            "",
            "- Storage duration: 10 hours has the lowest absolute COVE by a very small margin. The 100-hour system gains more relative to its own baseload, but its much larger storage cost produces the worst absolute COVE.",
            "- Efficiency: 55% has the lowest absolute COVE of the three tested values. The relative improvement percentage is not evidence that an inefficient device is physically better because both the optimized and baseload denominators change.",
            "- Price spikes: allowing prices up to $1,000/MWh produces the lowest COVE, showing that high-price events contribute materially to storage value.",
            "",
            "## Interpretation",
            "",
            "The aggregate 2014-2023 experiment supports an intermediate planning region of roughly 48-72 hours. The observed winner is 48 hours, with clear evidence over 24 and 168 hours, but the present data do not establish that 48 is better than 72 hours. The NQF-RNN comparison must be described as diagnostic because the saved predictions are conditioned on wind speed at the target hour rather than archived forecast vintages.",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result-dir",
        default=str(
            REPO_ROOT
            / "strategy_model"
            / "optimization"
            / "rolling_horizon_gurobi_results"
            / "forecast_backtest_2014_2023"
        ),
    )
    parser.add_argument(
        "--data",
        default=str(
            REPO_ROOT
            / "data"
            / "processed"
            / "dataset_1980-2023_withloads_fix.csv"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(
            REPO_ROOT
            / "strategy_model"
            / "test"
            / "run_016"
            / "config_run_016.yaml"
        ),
    )
    parser.add_argument(
        "--nqf",
        default=str(
            REPO_ROOT
            / "power_model"
            / "probabilistic"
            / "new_trained_results"
            / "rnn24_1423.csv"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=str(
            REPO_ROOT
            / "strategy_model"
            / "optimization"
            / "rolling_horizon_gurobi_results"
            / "forecast_backtest_robustness"
        ),
    )
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_base_config(Path(args.config))
    labels = load_backtest_labels(result_dir)
    yearly = yearly_results(labels, config, initial_soc=1440.0)
    tests = statistical_tests(yearly)
    wins = horizon_win_counts(yearly)
    yearly.to_csv(output_dir / "yearly_horizon_results.csv", index=False)
    tests.to_csv(output_dir / "paired_statistical_tests.csv", index=False)
    wins.to_csv(output_dir / "yearly_win_counts.csv", index=False)

    df = pd.read_csv(args.data, parse_dates=["datetime"]).sort_values("datetime").reset_index(drop=True)
    train_end = int(np.searchsorted(df["datetime"].to_numpy(), np.datetime64("2014-01-01")))
    capped_price = np.minimum(df["lmp"].to_numpy(dtype=float), 1000)
    training_price_mean = float(capped_price[:train_end].mean())
    df["price_normalized"] = capped_price / training_price_mean
    matrices = np.load(result_dir / "forecast_matrices.npz")
    origins = matrices["origins"]
    generation_forecasts = matrices["generation_forecast"]
    price_forecasts = matrices["price_forecast"]

    model_comparison = run_model_comparison(
        df,
        origins,
        generation_forecasts,
        price_forecasts,
        config,
        1440.0,
        0.2,
        1.0,
        Path(args.nqf),
    )
    model_comparison.to_csv(output_dir / "forecast_model_comparison.csv", index=False)

    sensitivity = run_sensitivities(
        df,
        origins,
        generation_forecasts,
        price_forecasts,
        config,
        0.2,
        1.0,
    )
    sensitivity.to_csv(output_dir / "sensitivity_results.csv", index=False)
    save_figures(yearly, tests, model_comparison, sensitivity, output_dir)
    write_summary(yearly, tests, wins, model_comparison, sensitivity, output_dir)

    maximum_violation = max(
        float(
            pd.concat([model_comparison, sensitivity])[column].max()
        )
        for column in pd.concat([model_comparison, sensitivity]).columns
        if column.startswith("max_") and column.endswith("_violation")
    )
    metadata = {
        "complete_test_years": list(range(2014, 2023)),
        "bootstrap_draws": 20000,
        "statistical_test": "exact paired sign-flip permutation test",
        "maximum_constraint_violation_new_runs": maximum_violation,
        "nqf_caveat": "Saved NQF-RNN predictions use target-hour wind speed and are diagnostic, not causal archived forecasts.",
    }
    (output_dir / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2))

    print("\nYearly winners")
    print(
        yearly.sort_values(["year", "cove"])
        .groupby("year")
        .first()[["horizon_hours", "cove", "improvement_vs_baseload_pct"]]
        .to_string()
    )
    print("\nPaired tests")
    print(tests.to_string(index=False))
    print("\nForecast model comparison")
    print(
        model_comparison[
            [
                "wind_forecast_model",
                "causal_operational_forecast",
                "cove",
                "improvement_vs_baseload_pct",
                "revenue_metric",
            ]
        ].to_string(index=False)
    )
    print("\nSensitivity")
    print(
        sensitivity[
            ["sensitivity", "value", "cove", "improvement_vs_baseload_pct"]
        ].to_string(index=False)
    )
    print(f"\nMaximum new-run constraint violation: {maximum_violation:.3e}")
    print(f"Saved to {output_dir}")


if __name__ == "__main__":
    main()

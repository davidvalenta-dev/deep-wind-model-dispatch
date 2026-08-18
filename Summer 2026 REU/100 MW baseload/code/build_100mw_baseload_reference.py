#!/usr/bin/env python3
"""Build the 100 MW baseload reference for the full paper period.

This script is intentionally not a Gurobi optimizer. It applies one fixed,
chronological rule:

1. Try to deliver 100 MW every hour.
2. If wind is above 100 MW, deliver 100 MW and charge storage with extra wind.
3. If wind is below 100 MW, deliver wind and discharge storage toward 100 MW.
4. Keep SoC between the configured minimum and maximum.

It writes the hourly 100 MW baseload output and comparison tables against the
existing rolling-horizon, scenario, and oracle result summaries.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
import sys

sys.path.insert(0, str(REPO_ROOT / "Summer 2026 REU" / "common"))
from annual_soc import next_target_corridor  # noqa: E402
from metrics import annualized_dispatch_cost, cove  # noqa: E402


@dataclass(frozen=True)
class StorageConfig:
    storage_power_mw: float
    storage_duration_h: float
    rte: float
    grid_cap_mw: float
    target_output_mw: float
    min_soc_mwh: float | None
    max_soc_mwh: float | None
    initial_soc_mwh: float | None
    price_threshold: float
    normalized_price_train_end: str
    annual_target_soc_mwh: float | None
    final_target_soc_mwh: float | None
    annual_soc_settlement_hours: int

    @property
    def capacity_mwh(self) -> float:
        return self.storage_power_mw * self.storage_duration_h

    @property
    def min_soc(self) -> float:
        return 0.2 * self.capacity_mwh if self.min_soc_mwh is None else self.min_soc_mwh

    @property
    def max_soc(self) -> float:
        return self.capacity_mwh if self.max_soc_mwh is None else self.max_soc_mwh

    @property
    def initial_soc(self) -> float:
        if self.initial_soc_mwh is not None:
            return self.initial_soc_mwh
        return (self.min_soc + self.max_soc) / 2.0


def load_data(path: Path, start: str, end: str | None, config: StorageConfig) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    start_ts = pd.Timestamp(start)
    df = df[df["datetime"] >= start_ts].copy()
    if end:
        df = df[df["datetime"] <= pd.Timestamp(end)].copy()
    df = df.reset_index(drop=True)

    train_cutoff = np.searchsorted(
        df["datetime"].to_numpy(),
        np.datetime64(pd.Timestamp(config.normalized_price_train_end)),
    )
    if train_cutoff <= 0:
        # The paper-period file starts at the test boundary, so compute the
        # normalization mean from the full source file before filtering.
        full = pd.read_csv(path, parse_dates=["datetime"]).sort_values("datetime")
        full_train = full[full["datetime"] < pd.Timestamp(config.normalized_price_train_end)]
        if full_train.empty:
            raise ValueError("Cannot compute normalized price mean; no training-price rows found.")
        training_price_mean = float(np.minimum(full_train["lmp"].to_numpy(float), config.price_threshold).mean())
    else:
        training_price_mean = float(
            np.minimum(df["lmp"].iloc[:train_cutoff].to_numpy(float), config.price_threshold).mean()
        )
    if not math.isfinite(training_price_mean) or training_price_mean == 0:
        raise ValueError("Invalid price normalization mean.")

    df["raw_price_usd_per_mwh"] = df["lmp"].astype(float)
    df["normalized_price"] = np.minimum(df["raw_price_usd_per_mwh"], config.price_threshold) / training_price_mean
    df["actual_wind_mw"] = df["power_generated"].astype(float)
    return df


def run_100mw_baseload(df: pd.DataFrame, config: StorageConfig) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    soc = float(np.clip(config.initial_soc, config.min_soc, config.max_soc))
    final_timestamp = pd.Timestamp(df["datetime"].iloc[-1])
    for _, row in df.iterrows():
        wind = max(0.0, float(row["actual_wind_mw"]))
        soc_start = soc
        direct = charge = discharge = 0.0

        if wind >= config.target_output_mw:
            direct = min(config.target_output_mw, config.grid_cap_mw)
            room = max(0.0, config.max_soc - soc_start)
            charge = min(wind - direct, config.storage_power_mw, room)
            delivered = direct
        else:
            direct = min(wind, config.grid_cap_mw)
            needed = max(0.0, config.target_output_mw - direct)
            available_discharge = max(0.0, (soc_start - config.min_soc) * config.rte)
            discharge = min(needed, config.storage_power_mw, available_discharge, config.grid_cap_mw - direct)
            delivered = direct + discharge

        corridor = next_target_corridor(
            pd.Timestamp(row["datetime"]),
            final_timestamp,
            config.annual_target_soc_mwh,
            config.final_target_soc_mwh,
            config.min_soc,
            config.max_soc,
            config.storage_power_mw,
            config.rte,
            config.annual_soc_settlement_hours,
        )
        if corridor.active and corridor.target_mwh is not None:
            if soc_start < corridor.target_mwh - 1e-7:
                discharge = 0.0
                charge = min(
                    config.storage_power_mw,
                    wind,
                    config.max_soc - soc_start,
                    corridor.target_mwh - soc_start,
                )
                direct = min(config.target_output_mw, max(0.0, wind - charge), config.grid_cap_mw)
                delivered = direct
            else:
                discharge = min(discharge, max(0.0, (soc_start - corridor.target_mwh) * config.rte))
                direct = min(direct, wind, max(0.0, config.grid_cap_mw - discharge))
                delivered = direct + discharge
        projected_soc = soc_start + charge - discharge / config.rte
        if projected_soc < corridor.lower_mwh - 1e-7:
            discharge = 0.0
            required_charge = max(0.0, corridor.lower_mwh - soc_start)
            feasible_charge = min(config.storage_power_mw, wind, config.max_soc - soc_start)
            if required_charge > feasible_charge + 1e-6:
                raise RuntimeError(
                    f"100 MW benchmark cannot physically reach annual SoC floor at {row['datetime']}"
                )
            charge = max(charge, required_charge)
            direct = min(config.target_output_mw, max(0.0, wind - charge), config.grid_cap_mw)
            delivered = direct
        projected_soc = soc_start + charge - discharge / config.rte
        if projected_soc > corridor.upper_mwh + 1e-7:
            charge = 0.0
            required_discharge = max(0.0, (soc_start - corridor.upper_mwh) * config.rte)
            feasible_discharge = min(
                config.storage_power_mw,
                max(0.0, (soc_start - config.min_soc) * config.rte),
                config.grid_cap_mw,
            )
            if required_discharge > feasible_discharge + 1e-6:
                raise RuntimeError(
                    f"100 MW benchmark cannot physically reach annual SoC ceiling at {row['datetime']}"
                )
            discharge = max(discharge, required_discharge)
            direct = min(direct, wind, max(0.0, config.grid_cap_mw - discharge))
            delivered = direct + discharge

        soc = soc_start + charge - discharge / config.rte
        curtailment = max(0.0, wind - direct - charge)
        shortfall = max(0.0, config.target_output_mw - delivered)
        raw_revenue = delivered * float(row["raw_price_usd_per_mwh"])
        normalized_revenue = delivered * float(row["normalized_price"])

        rows.append(
            {
                "datetime": row["datetime"],
                "actual_wind_mw": wind,
                "target_output_mw": config.target_output_mw,
                "direct_wind_mw": direct,
                "charge_mw": charge,
                "discharge_mw": discharge,
                "delivered_power_mw": delivered,
                "curtailment_mw": curtailment,
                "output_shortfall_mw": shortfall,
                "soc_start_mwh": soc_start,
                "soc_end_mwh": soc,
                "raw_price_usd_per_mwh": float(row["raw_price_usd_per_mwh"]),
                "normalized_price": float(row["normalized_price"]),
                "raw_hourly_revenue_usd": raw_revenue,
                "normalized_hourly_revenue_metric": normalized_revenue,
                "annual_soc_control_active": float(corridor.active),
                "annual_soc_lower_bound_mwh": corridor.lower_mwh,
                "annual_soc_upper_bound_mwh": corridor.upper_mwh,
                "annual_soc_target_mwh": corridor.target_mwh,
            }
        )
    return pd.DataFrame(rows)


def summarize_period(labels: pd.DataFrame, start: str | None = None, end: str | None = None) -> dict[str, float | str | int]:
    subset = labels.copy()
    if start is not None:
        subset = subset[subset["datetime"] >= pd.Timestamp(start)]
    if end is not None:
        subset = subset[subset["datetime"] <= pd.Timestamp(end)]
    if subset.empty:
        raise ValueError(f"No 100 MW baseload rows for requested period start={start} end={end}")
    return {
        "period_start": str(pd.to_datetime(subset["datetime"].iloc[0])),
        "period_end": str(pd.to_datetime(subset["datetime"].iloc[-1])),
        "hours": int(len(subset)),
        "raw_revenue_usd": float(subset["raw_hourly_revenue_usd"].sum()),
        "normalized_revenue_metric": float(subset["normalized_hourly_revenue_metric"].sum()),
        "delivered_energy_mwh": float(subset["delivered_power_mw"].sum()),
        "curtailment_mwh": float(subset["curtailment_mw"].sum()),
        "output_shortfall_mwh": float(subset["output_shortfall_mw"].sum()),
        "total_charge_mwh": float(subset["charge_mw"].sum()),
        "total_discharge_mwh": float(subset["discharge_mw"].sum()),
        "initial_soc_mwh": float(subset["soc_start_mwh"].iloc[0]),
        "final_soc_mwh": float(subset["soc_end_mwh"].iloc[-1]),
        "min_soc_mwh": float(min(subset["soc_start_mwh"].min(), subset["soc_end_mwh"].min())),
        "max_soc_mwh": float(max(subset["soc_start_mwh"].max(), subset["soc_end_mwh"].max())),
    }


def add_period_100mw_comparison(
    result_rows: pd.DataFrame,
    labels: pd.DataFrame,
    result_revenue_col: str,
    result_cove_col: str,
    result_cost_col: str | None,
    result_baseload_revenue_col: str | None,
    result_baseload_cove_col: str | None,
    price_mode: str,
) -> pd.DataFrame:
    rows = []
    for _, row in result_rows.iterrows():
        start = row.get("test_start")
        end = row.get("test_end")
        period = summarize_period(labels, start, end)
        reference_revenue = (
            period["raw_revenue_usd"]
            if price_mode == "raw"
            else period["normalized_revenue_metric"]
        )
        if result_cost_col and result_cost_col in row.index and pd.notna(row[result_cost_col]):
            cost = float(row[result_cost_col])
        elif result_baseload_revenue_col and result_baseload_cove_col:
            cost = float(row[result_baseload_revenue_col]) * float(row[result_baseload_cove_col])
        else:
            cost = math.nan
        reference_cove = cost / float(reference_revenue) if cost and math.isfinite(cost) else math.nan
        result_revenue = float(row[result_revenue_col])
        result_cove = float(row[result_cove_col])
        out = row.to_dict()
        out.update(
            {
                "comparison_reference": "100mw_constant_output_baseload",
                "comparison_price_mode": price_mode,
                "reference_period_start": period["period_start"],
                "reference_period_end": period["period_end"],
                "reference_hours": period["hours"],
                "100mw_baseload_revenue": reference_revenue,
                "100mw_baseload_cove": reference_cove,
                "revenue_gain_vs_100mw_baseload_pct": (result_revenue / float(reference_revenue) - 1.0) * 100.0,
                "cove_reduction_vs_100mw_baseload_pct": (reference_cove - result_cove) / reference_cove * 100.0
                if math.isfinite(reference_cove) and reference_cove != 0
                else math.nan,
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def make_figures(labels: pd.DataFrame, summary: pd.DataFrame, comparison_frames: list[pd.DataFrame], figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    week = labels.iloc[:168].copy()
    fig, axes = plt.subplots(3, 1, figsize=(10.8, 7.8), dpi=180, sharex=True)
    axes[0].plot(week["datetime"], week["actual_wind_mw"], color="#111827", label="actual wind", linewidth=1.5)
    axes[0].plot(week["datetime"], week["delivered_power_mw"], color="#2563EB", label="100 MW baseload delivery", linewidth=1.8)
    axes[0].axhline(100.0, color="#DC2626", linestyle="--", linewidth=1.1, label="100 MW target")
    axes[0].set_ylabel("MW")
    axes[0].set_title("2014-2023 100 MW Baseload Reference: Example Week", fontweight="bold")
    axes[0].legend(frameon=False, ncol=3, loc="upper right")

    axes[1].bar(week["datetime"], week["charge_mw"], color="#22C55E", width=0.035, label="charge")
    axes[1].bar(week["datetime"], -week["discharge_mw"], color="#F97316", width=0.035, label="discharge")
    axes[1].set_ylabel("MW")
    axes[1].legend(frameon=False, ncol=2, loc="upper right")

    axes[2].plot(week["datetime"], week["soc_end_mwh"], color="#7C3AED", linewidth=1.8)
    axes[2].axhline(200, color="#6B7280", linestyle="--", linewidth=1.0)
    axes[2].axhline(1000, color="#6B7280", linestyle="--", linewidth=1.0)
    axes[2].set_ylabel("SoC (MWh)")
    axes[2].set_xlabel("Date")

    for axis in axes:
        axis.grid(color="#E5E7EB")
        axis.set_axisbelow(True)
    fig.autofmt_xdate(rotation=16)
    fig.tight_layout()
    fig.savefig(figure_dir / "step0_100mw_baseload_2014_2023_example_week.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)

    if comparison_frames:
        combined = pd.concat(comparison_frames, ignore_index=True, sort=False)
        keep = combined.dropna(subset=["cove_reduction_vs_100mw_baseload_pct"]).copy()
        if not keep.empty:
            keep["label"] = keep.apply(
                lambda row: f"{row.get('method', row.get('candidate', 'case'))}\n{int(float(row.get('horizon_hours', 0)))} h"
                if "horizon_hours" in row.index and pd.notna(row.get("horizon_hours"))
                else str(row.get("candidate", "case")),
                axis=1,
            )
            keep = keep.sort_values("cove_reduction_vs_100mw_baseload_pct")
            fig, ax = plt.subplots(figsize=(11.2, max(5.5, 0.45 * len(keep))), dpi=180)
            bars = ax.barh(keep["label"], keep["cove_reduction_vs_100mw_baseload_pct"], color="#0F766E")
            ax.axvline(0, color="#111827", linewidth=1.0)
            ax.set_xlabel("COVE reduction vs 100 MW baseload (%)")
            ax.set_title("All Methods Compared Against the Same 100 MW Baseload Rule", fontweight="bold")
            ax.grid(axis="x", color="#E5E7EB")
            for bar, value in zip(bars, keep["cove_reduction_vs_100mw_baseload_pct"]):
                ax.text(value + (0.4 if value >= 0 else -0.4), bar.get_y() + bar.get_height() / 2, f"{value:.2f}%", va="center", ha="left" if value >= 0 else "right", fontsize=8)
            fig.tight_layout()
            fig.savefig(figure_dir / "step0_methods_vs_100mw_baseload.png", facecolor="white", bbox_inches="tight")
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 2014-2023 100 MW baseload reference and comparisons.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", default=None)
    parser.add_argument("--storage-power-mw", type=float, default=100.0)
    parser.add_argument("--storage-duration-h", type=float, default=10.0)
    parser.add_argument("--rte", type=float, default=0.55)
    parser.add_argument("--grid-cap-mw", type=float, default=249.0)
    parser.add_argument("--target-output-mw", type=float, default=100.0)
    parser.add_argument("--min-soc-mwh", type=float, default=None)
    parser.add_argument("--max-soc-mwh", type=float, default=None)
    parser.add_argument("--initial-soc-mwh", type=float, default=None)
    parser.add_argument("--price-threshold", type=float, default=1000.0)
    parser.add_argument("--normalized-price-train-end", default="2014-01-01")
    parser.add_argument("--annual-target-soc-mwh", type=float, default=600.0)
    parser.add_argument("--final-target-soc-mwh", type=float, default=600.0)
    parser.add_argument("--annual-soc-settlement-hours", type=int, default=720)
    parser.add_argument("--rolling-summary", type=Path, default=None)
    parser.add_argument("--scenario-summary", type=Path, default=None)
    parser.add_argument("--oracle-summary", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    config = StorageConfig(
        storage_power_mw=args.storage_power_mw,
        storage_duration_h=args.storage_duration_h,
        rte=args.rte,
        grid_cap_mw=args.grid_cap_mw,
        target_output_mw=args.target_output_mw,
        min_soc_mwh=args.min_soc_mwh,
        max_soc_mwh=args.max_soc_mwh,
        initial_soc_mwh=args.initial_soc_mwh,
        price_threshold=args.price_threshold,
        normalized_price_train_end=args.normalized_price_train_end,
        annual_target_soc_mwh=args.annual_target_soc_mwh,
        final_target_soc_mwh=args.final_target_soc_mwh,
        annual_soc_settlement_hours=args.annual_soc_settlement_hours,
    )
    df = load_data(args.data, args.start, args.end, config)
    labels = run_100mw_baseload(df, config)
    hourly_path = out_dir / "constant_output_baseload_100mw_2014_2023_hourly.csv"
    labels.to_csv(hourly_path, index=False)

    summary = summarize_period(labels)
    timestamps = pd.to_datetime(labels["datetime"])
    annual_mask = (
        (timestamps.dt.month == 12)
        & (timestamps.dt.day == 31)
        & (timestamps.dt.hour == 23)
    )
    annual_errors = np.abs(
        labels.loc[annual_mask, "soc_end_mwh"].to_numpy(float)
        - float(config.annual_target_soc_mwh)
    ) if config.annual_target_soc_mwh is not None else np.array([], dtype=float)
    final_target_error = (
        abs(float(labels["soc_end_mwh"].iloc[-1]) - float(config.final_target_soc_mwh))
        if config.final_target_soc_mwh is not None
        else 0.0
    )
    wind_violation = float(
        np.maximum(labels["direct_wind_mw"] + labels["charge_mw"] - labels["actual_wind_mw"], 0.0).max()
    )
    grid_violation = float(np.maximum(labels["delivered_power_mw"] - config.grid_cap_mw, 0.0).max())
    soc_update_violation = float(
        np.abs(
            labels["soc_end_mwh"]
            - (labels["soc_start_mwh"] + labels["charge_mw"] - labels["discharge_mw"] / config.rte)
        ).max()
    )
    simultaneous = float(np.minimum(labels["charge_mw"], labels["discharge_mw"]).max())
    summary.update(
        {
            "case_id": "constant_output_baseload_100mw_2014_2023",
            "storage_power_mw": config.storage_power_mw,
            "storage_duration_h": config.storage_duration_h,
            "capacity_mwh": config.capacity_mwh,
            "rte": config.rte,
            "grid_cap_mw": config.grid_cap_mw,
            "target_output_mw": config.target_output_mw,
            "min_soc_mwh_configured": config.min_soc,
            "max_soc_mwh_configured": config.max_soc,
            "initial_soc_mwh_configured": config.initial_soc,
            "annual_target_soc_mwh": config.annual_target_soc_mwh,
            "final_target_soc_mwh": config.final_target_soc_mwh,
            "annual_soc_settlement_hours": config.annual_soc_settlement_hours,
            "annual_soc_target_count": int(annual_mask.sum()),
            "annual_soc_target_violation_count": int(np.sum(annual_errors > 1e-5)),
            "annual_soc_target_max_abs_error": float(annual_errors.max()) if annual_errors.size else 0.0,
            "final_soc_target_abs_error": float(final_target_error),
            "final_soc_target_violation_count": int(final_target_error > 1e-5),
            "qa_max_wind_balance_violation": wind_violation,
            "qa_max_grid_violation": grid_violation,
            "qa_max_soc_update_violation": soc_update_violation,
            "qa_max_simultaneous_charge_discharge": simultaneous,
            "qa_total_violation_count": int(
                sum(value > 1e-5 for value in [wind_violation, grid_violation, soc_update_violation, simultaneous])
            ),
            "annualized_dispatch_cost_usd": annualized_dispatch_cost(
                wind_rating_mw=config.grid_cap_mw,
                storage_power_mw=config.storage_power_mw,
            ),
            "normalized_cove_index": cove(
                annualized_dispatch_cost(
                    wind_rating_mw=config.grid_cap_mw,
                    storage_power_mw=config.storage_power_mw,
                ),
                float(summary["normalized_revenue_metric"]),
            ),
            "raw_cove_usd_basis": cove(
                annualized_dispatch_cost(
                    wind_rating_mw=config.grid_cap_mw,
                    storage_power_mw=config.storage_power_mw,
                ),
                float(summary["raw_revenue_usd"]),
            ),
            "price_note": "raw revenue uses raw LMP; normalized revenue uses the rolling-horizon normalized/capped price metric",
            "hourly_output_file": str(hourly_path),
        }
    )
    if (
        summary["annual_soc_target_violation_count"]
        or summary["final_soc_target_violation_count"]
        or summary["qa_total_violation_count"]
    ):
        raise RuntimeError(f"100 MW benchmark failed annual/final SoC QA: {summary}")
    pd.DataFrame([summary]).to_csv(out_dir / "constant_output_baseload_100mw_2014_2023_summary.csv", index=False)

    metadata = {
        "data": str(args.data),
        "start": args.start,
        "end": args.end,
        "storage_config": config.__dict__,
        "outputs": {
            "hourly": str(hourly_path),
            "summary": str(out_dir / "constant_output_baseload_100mw_2014_2023_summary.csv"),
        },
    }
    (out_dir / "constant_output_baseload_100mw_2014_2023_metadata.json").write_text(json.dumps(metadata, indent=2))

    comparison_frames: list[pd.DataFrame] = []
    if args.rolling_summary and args.rolling_summary.exists():
        rolling = pd.read_csv(args.rolling_summary)
        rolling_cmp = add_period_100mw_comparison(
            rolling,
            labels,
            result_revenue_col="revenue_metric",
            result_cove_col="cove",
            result_cost_col="dispatch_cost",
            result_baseload_revenue_col="baseload_revenue_metric",
            result_baseload_cove_col="baseload_cove",
            price_mode="normalized",
        )
        rolling_cmp.to_csv(out_dir / "comparison_rolling_horizon_vs_100mw_baseload.csv", index=False)
        comparison_frames.append(rolling_cmp)

    if args.oracle_summary and args.oracle_summary.exists():
        oracle = pd.read_csv(args.oracle_summary)
        oracle_cmp = add_period_100mw_comparison(
            oracle,
            labels,
            result_revenue_col="revenue_metric",
            result_cove_col="cove",
            result_cost_col="dispatch_cost",
            result_baseload_revenue_col="baseload_revenue_metric",
            result_baseload_cove_col="baseload_cove",
            price_mode="normalized",
        )
        oracle_cmp.to_csv(out_dir / "comparison_oracle_vs_100mw_baseload.csv", index=False)
        comparison_frames.append(oracle_cmp)

    if args.scenario_summary and args.scenario_summary.exists():
        scenarios = pd.read_csv(args.scenario_summary)
        scenario_cmp = add_period_100mw_comparison(
            scenarios,
            labels,
            result_revenue_col="dispatch_revenue",
            result_cove_col="dispatch_cove_index",
            result_cost_col=None,
            result_baseload_revenue_col="baseload_revenue",
            result_baseload_cove_col="baseload_cove_index",
            price_mode="raw",
        )
        scenario_cmp.to_csv(out_dir / "comparison_scenarios_vs_100mw_baseload.csv", index=False)
        comparison_frames.append(scenario_cmp)

    make_figures(labels, pd.DataFrame([summary]), comparison_frames, args.figures_dir)

    print("\n100 MW baseload reference built")
    print(f"Period: {summary['period_start']} to {summary['period_end']} ({summary['hours']:,} hours)")
    print(f"Raw revenue: ${summary['raw_revenue_usd']:,.2f}")
    print(f"Normalized revenue metric: {summary['normalized_revenue_metric']:,.2f}")
    print(f"Final SoC: {summary['final_soc_mwh']:.2f} MWh")
    print(f"Hourly CSV: {hourly_path}")
    print(f"Summary CSV: {out_dir / 'constant_output_baseload_100mw_2014_2023_summary.csv'}")


if __name__ == "__main__":
    main()

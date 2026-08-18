#!/usr/bin/env python3
"""Audit the active Summer 2026 REU hourly CSVs against the common CAES setup.

Run from this folder:
    ../venv/bin/python AUDIT_DATA_CONFIG.py

This does not optimize anything. It checks the already generated hourly CSVs.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
OUT = HERE / "audit"
OUT.mkdir(exist_ok=True)

SOC_MIN = 200.0
SOC_MAX = 1000.0
POWER_LIMIT = 100.0
GRID_CAP = 249.0
TOL = 1e-6


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def max_over(value: float, limit: float) -> float:
    return max(0.0, value - limit)


def max_under(value: float, limit: float) -> float:
    return max(0.0, limit - value)


def audit_hourly(path: Path, case_group: str, case_name: str) -> dict[str, object]:
    df = pd.read_csv(path)
    soc_start_col = first_existing(df, ["SOC_start_MWh", "soc_start_mwh", "soc_start"])
    soc_end_col = first_existing(df, ["SOC_end_MWh", "soc_end_mwh", "soc_end"])
    charge_col = first_existing(df, ["charge_MW", "charge_mw", "realized_charge_mw", "realized_charge"])
    discharge_col = first_existing(df, ["discharge_MW", "discharge_mw", "realized_discharge_mw", "realized_discharge"])
    delivered_col = first_existing(df, ["delivered_power_MW", "delivered_power_mw", "realized_delivered_mw", "realized_delivered"])
    wind_col = first_existing(df, ["actual_wind_MW", "actual_wind_mw", "actual_generation_mw", "actual_generation"])
    direct_col = first_existing(df, ["direct_wind_MW", "direct_wind_mw", "realized_direct_mw", "realized_direct"])
    curtail_col = first_existing(df, ["curtailment_MW", "curtailment_mw", "realized_curtailment_mw", "realized_curtailment"])

    report: dict[str, object] = {
        "case_group": case_group,
        "case_name": case_name,
        "file": str(path.relative_to(HERE)),
        "rows": len(df),
    }
    for col_name, label in [(soc_start_col, "soc_start"), (soc_end_col, "soc_end")]:
        if col_name is None:
            report[f"{label}_min_mwh"] = math.nan
            report[f"{label}_max_mwh"] = math.nan
            report[f"{label}_max_violation_mwh"] = math.nan
        else:
            values = pd.to_numeric(df[col_name], errors="coerce")
            low = float(values.min())
            high = float(values.max())
            report[f"{label}_min_mwh"] = low
            report[f"{label}_max_mwh"] = high
            report[f"{label}_max_violation_mwh"] = max(max_under(low, SOC_MIN), max_over(high, SOC_MAX))
    if soc_end_col is not None and len(df):
        report["final_soc_mwh"] = float(pd.to_numeric(df[soc_end_col], errors="coerce").iloc[-1])
        report["final_soc_target_violation_mwh"] = abs(report["final_soc_mwh"] - 600.0)

    for col_name, label, limit in [
        (charge_col, "charge", POWER_LIMIT),
        (discharge_col, "discharge", POWER_LIMIT),
        (delivered_col, "delivered", GRID_CAP),
    ]:
        if col_name is None:
            report[f"{label}_max_mw"] = math.nan
            report[f"{label}_max_violation_mw"] = math.nan
            report[f"{label}_negative_violation_mw"] = math.nan
        else:
            values = pd.to_numeric(df[col_name], errors="coerce")
            report[f"{label}_max_mw"] = float(values.max())
            report[f"{label}_max_violation_mw"] = max_over(float(values.max()), limit)
            report[f"{label}_negative_violation_mw"] = max_under(float(values.min()), 0.0)

    if wind_col and direct_col and charge_col and discharge_col and delivered_col:
        wind = pd.to_numeric(df[wind_col], errors="coerce")
        direct = pd.to_numeric(df[direct_col], errors="coerce")
        charge = pd.to_numeric(df[charge_col], errors="coerce")
        discharge = pd.to_numeric(df[discharge_col], errors="coerce")
        delivered = pd.to_numeric(df[delivered_col], errors="coerce")
        report["wind_balance_max_abs_mw"] = float((wind - direct - charge - df.get(curtail_col, 0)).abs().max()) if curtail_col else math.nan
        report["delivered_definition_max_abs_mw"] = float((delivered - direct - discharge).abs().max())

    numeric_violations = [
        value
        for key, value in report.items()
        if "violation" in key and isinstance(value, (int, float)) and not math.isnan(value)
    ]
    report["passes_common_100mw_10h_checks"] = all(value <= TOL for value in numeric_violations)
    return report


def collect_files() -> list[tuple[Path, str, str]]:
    files: list[tuple[Path, str, str]] = []
    files.append((
        HERE / "100 MW baseload" / "results" / "frozen_controlled" / "constant_output_baseload_100mw_2014_2023_hourly.csv",
        "Step 0",
        "100 MW benchmark 2014-2023",
    ))
    for horizon in [24, 48, 72, 168]:
        files.append((
            HERE
            / "rolling horizon"
            / "results"
            / "controlled_hourly_nowcast_from_knobs"
            / f"horizon_{horizon}h"
            / "single_forecast_recourse_nowcast_gated_labels.csv",
            "Step 2",
            f"deterministic forecast-driven RH MILP {horizon} h",
        ))
        files.append((
            HERE / "oracle upper bound" / "results" / "frozen_controlled" / f"oracle_dispatch_{horizon}h.csv",
            "Step 4 hourly",
            f"hourly-replan oracle {horizon} h",
        ))
    for name in [
        "single_forecast_recourse_nowcast_gated",
        "three_scenario_expected_nowcast_gated",
        "five_scenario_expected_nowcast_gated",
        "seven_scenario_expected_nowcast_gated",
        "ten_scenario_expected_nowcast_gated",
    ]:
        files.append((
            HERE / "different scenarios" / "results" / "frozen_controlled" / f"{name}_labels.csv",
            "Step 3",
            name,
        ))
    return files


def main() -> None:
    rows = []
    missing = []
    for path, case_group, case_name in collect_files():
        if not path.exists():
            missing.append({"case_group": case_group, "case_name": case_name, "file": str(path.relative_to(HERE))})
            continue
        rows.append(audit_hourly(path, case_group, case_name))

    report = pd.DataFrame(rows)
    report_path = OUT / "summer_2026_reu_data_config_audit.csv"
    report.to_csv(report_path, index=False)
    if missing:
        pd.DataFrame(missing).to_csv(OUT / "summer_2026_reu_missing_hourly_files.csv", index=False)

    passed = int(report["passes_common_100mw_10h_checks"].sum()) if not report.empty else 0
    total = len(report)
    print("SUMMER 2026 REU DATA / CONFIG AUDIT")
    print(f"Audited hourly files: {total}")
    print(f"Passed common 100 MW / 10 h checks: {passed}/{total}")
    if missing:
        print(f"Missing expected files: {len(missing)}")
    print(f"Audit CSV: {report_path}")
    if total and passed != total:
        print("\nFiles needing attention:")
        bad = report[~report["passes_common_100mw_10h_checks"]]
        print(bad[["case_group", "case_name", "file", "soc_end_min_mwh", "soc_end_max_mwh", "delivered_max_mw"]].to_string(index=False))


if __name__ == "__main__":
    main()

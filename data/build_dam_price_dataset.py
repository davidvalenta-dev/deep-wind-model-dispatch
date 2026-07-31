"""Build a 2014-2023 Pyron-style dataset with ERCOT DAM price columns.

This is a future-experiment data builder. It does not replace the frozen
RTM-based benchmark data. It pulls ERCOT Day-Ahead Market Settlement Point
Prices through gridstatus, keeps the West hub/load-zone locations available in
the annual DAM SPP archive, and merges them onto the existing project dispatch
dataset.

Run from the repository root:

    ./venv/bin/python data/build_dam_price_dataset.py

Outputs:
- data/raw/dam_spp/ercot_dam_spp_west_2014_2023.csv
- data/processed/dataset_2014_2023_with_dam_prices.csv
- data/processed/dataset_2014_2023_with_dam_prices_QA.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from gridstatus import Ercot


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT_DATA = REPO_ROOT / "data" / "processed" / "dataset_1980-2023_withloads_fix.csv"
DEFAULT_RAW_DAM_OUT = REPO_ROOT / "data" / "raw" / "dam_spp" / "ercot_dam_spp_west_2011_2023.csv"
DEFAULT_MERGED_OUT = REPO_ROOT / "data" / "processed" / "dataset_2014_2023_with_dam_prices.csv"
DEFAULT_FULL_MERGED_OUT = REPO_ROOT / "data" / "processed" / "dataset_1980_2023_with_dam_prices_for_forecast.csv"
DEFAULT_QA_OUT = REPO_ROOT / "data" / "processed" / "dataset_2014_2023_with_dam_prices_QA.csv"
DEFAULT_METADATA_OUT = REPO_ROOT / "data" / "processed" / "dataset_2014_2023_with_dam_prices_metadata.json"

YEARS = range(2011, 2024)
LOCATIONS = ("LZ_WEST", "HB_WEST")


def timestamp_without_timezone(series: pd.Series) -> pd.Series:
    timestamps = pd.to_datetime(series, errors="raise", utc=True)
    return timestamps.dt.tz_convert("America/Chicago").dt.tz_localize(None)


def fetch_west_dam_spp(years: range, force: bool, raw_out: Path) -> pd.DataFrame:
    if raw_out.exists() and not force:
        return pd.read_csv(raw_out, parse_dates=["datetime"])

    iso = Ercot()
    frames = []
    for year in years:
        dam = iso.get_dam_spp(year, verbose=True)
        dam = dam[dam["Location"].isin(LOCATIONS)].copy()
        dam["datetime"] = timestamp_without_timezone(dam["Time"])
        dam["year"] = year
        frames.append(
            dam[
                [
                    "datetime",
                    "year",
                    "Location",
                    "Location Type",
                    "Market",
                    "SPP",
                ]
            ]
        )

    west = pd.concat(frames, ignore_index=True)
    west = west.sort_values(["datetime", "Location"]).reset_index(drop=True)
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    west.to_csv(raw_out, index=False)
    return west


def pivot_west_dam(west: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        west.pivot_table(
            index="datetime",
            columns="Location",
            values="SPP",
            aggfunc="mean",
        )
        .reset_index()
        .rename(
            columns={
                "LZ_WEST": "dam_lz_west_spp_usd_per_mwh",
                "HB_WEST": "dam_hb_west_spp_usd_per_mwh",
            }
        )
    )
    return pivot


def merge_project_with_dam(project_data: Path, dam_prices: pd.DataFrame) -> pd.DataFrame:
    project = pd.read_csv(project_data, parse_dates=["datetime"])
    project = project.sort_values("datetime").reset_index(drop=True)
    project = project.rename(columns={"lmp": "rtm_lmp_pyron_usd_per_mwh"})

    merged = project.merge(dam_prices, on="datetime", how="left", validate="one_to_one")
    dam_columns = [
        "dam_lz_west_spp_usd_per_mwh",
        "dam_hb_west_spp_usd_per_mwh",
    ]
    dam_period = merged["datetime"] >= pd.Timestamp("2011-01-01")
    for column in dam_columns:
        flag_column = f"{column}_was_interpolated"
        merged[flag_column] = dam_period & merged[column].isna()
        merged.loc[dam_period, column] = (
            merged.loc[dam_period, column]
            .interpolate(method="linear", limit_direction="both")
        )

    merged["dam_source_note"] = (
        "ERCOT DAM SPP annual archive via gridstatus. Public annual archive contains "
        "West hub/load-zone prices; PYR_PYRON1 node was not present in the annual DAM SPP file. "
        "Spring daylight-saving 02:00 gaps are linearly interpolated and flagged."
    )
    return merged


def build_dataset(project_data: Path, dam_prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    full_merged = merge_project_with_dam(project_data, dam_prices)
    merged = full_merged[
        (full_merged["datetime"] >= "2014-01-01")
        & (full_merged["datetime"] <= "2023-12-31 23:00:00")
    ].copy()

    by_year = []
    for year, group in merged.groupby(merged["datetime"].dt.year):
        by_year.append(
            {
                "year": int(year),
                "project_rows": int(len(group)),
                "raw_missing_dam_lz_west_rows_interpolated": int(group["dam_lz_west_spp_usd_per_mwh_was_interpolated"].sum()),
                "raw_missing_dam_hb_west_rows_interpolated": int(group["dam_hb_west_spp_usd_per_mwh_was_interpolated"].sum()),
                "remaining_missing_dam_lz_west_rows": int(group["dam_lz_west_spp_usd_per_mwh"].isna().sum()),
                "remaining_missing_dam_hb_west_rows": int(group["dam_hb_west_spp_usd_per_mwh"].isna().sum()),
                "rtm_lmp_min": float(group["rtm_lmp_pyron_usd_per_mwh"].min()),
                "rtm_lmp_max": float(group["rtm_lmp_pyron_usd_per_mwh"].max()),
                "dam_lz_west_min": float(group["dam_lz_west_spp_usd_per_mwh"].min()),
                "dam_lz_west_max": float(group["dam_lz_west_spp_usd_per_mwh"].max()),
                "dam_hb_west_min": float(group["dam_hb_west_spp_usd_per_mwh"].min()),
                "dam_hb_west_max": float(group["dam_hb_west_spp_usd_per_mwh"].max()),
            }
        )

    qa = pd.DataFrame(by_year)
    metadata = {
        "purpose": "Future DAM-informed dispatch experiment dataset.",
        "project_input": str(project_data),
        "project_input_columns_used": [
            "datetime",
            "power_generated",
            "lmp",
            "user_load_zonal",
        ],
        "dam_source": "ERCOT DAM Settlement Point Prices, accessed with gridstatus.Ercot.get_dam_spp(year)",
        "dam_locations_available_and_used": list(LOCATIONS),
        "dam_pyron_node_status": "PYR_PYRON1 was checked and was not present in the annual public DAM SPP files pulled by gridstatus.",
        "dam_gap_handling": "The existing project dataset has continuous local timestamps. ERCOT DAM local timestamps skip the spring daylight-saving 02:00 hour. Those 10 hourly DAM gaps were linearly interpolated and flagged in *_was_interpolated columns.",
        "merged_output_definition": "Existing Pyron-style project rows with RTM PYR_PYRON1 LMP plus DAM West hub/load-zone SPP columns.",
        "intended_experiment": "Plan dispatch with forecast wind and DAM price columns, then score realized revenue with RTM PYR_PYRON1 LMP.",
        "years": [min(YEARS), max(YEARS)],
        "rows": int(len(merged)),
        "first_datetime": str(merged["datetime"].min()),
        "last_datetime": str(merged["datetime"].max()),
    }
    return merged, qa, metadata, full_merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 2014-2023 ERCOT DAM price dataset.")
    parser.add_argument("--project-data", default=str(DEFAULT_PROJECT_DATA))
    parser.add_argument("--raw-dam-out", default=str(DEFAULT_RAW_DAM_OUT))
    parser.add_argument("--merged-out", default=str(DEFAULT_MERGED_OUT))
    parser.add_argument("--full-merged-out", default=str(DEFAULT_FULL_MERGED_OUT))
    parser.add_argument("--qa-out", default=str(DEFAULT_QA_OUT))
    parser.add_argument("--metadata-out", default=str(DEFAULT_METADATA_OUT))
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    raw_out = Path(args.raw_dam_out)
    west = fetch_west_dam_spp(YEARS, args.force_download, raw_out)
    dam_prices = pivot_west_dam(west)
    merged, qa, metadata, full_merged = build_dataset(Path(args.project_data), dam_prices)

    merged_out = Path(args.merged_out)
    full_merged_out = Path(args.full_merged_out)
    qa_out = Path(args.qa_out)
    metadata_out = Path(args.metadata_out)
    merged_out.parent.mkdir(parents=True, exist_ok=True)
    full_merged_out.parent.mkdir(parents=True, exist_ok=True)
    qa_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)

    merged.to_csv(merged_out, index=False)
    full_merged.to_csv(full_merged_out, index=False)
    qa.to_csv(qa_out, index=False)
    metadata_out.write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"Raw filtered DAM prices saved to {raw_out}")
    print(f"Merged DAM/RTM project dataset saved to {merged_out}")
    print(f"Full training/backtest DAM/RTM dataset saved to {full_merged_out}")
    print(f"QA saved to {qa_out}")
    print()
    print(qa.to_string(index=False))


if __name__ == "__main__":
    main()

from __future__ import annotations

import io
import math
import re
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from herbie import Herbie


OUT_DIR = Path("outputs/new-data")
TMP_DIR = Path("/tmp/deep_wind_newest_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

ERCOT_BASE = "https://www.ercot.com"
WIND_REPORT_URL = f"{ERCOT_BASE}/misapp/GetReports.do?reportTypeId=13028"
LMP_REPORT_URL = f"{ERCOT_BASE}/misapp/GetReports.do?reportTypeId=12300"
LOAD_FORECAST_URL = f"{ERCOT_BASE}/misapp/GetReports.do?reportTypeId=12312"
LOAD_ARCHIVE_URL = "https://www.ercot.com/gridinfo/load/load_hist"

PYRON_LAT = 32.580306
PYRON_LON_360 = 259.340082
CENTRAL = ZoneInfo("America/Chicago")


def download_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def save_download(url: str, path: Path) -> Path:
    if not path.exists():
        path.write_bytes(download_bytes(url))
    return path


def parse_report_zip_links(html: str, must_contain: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        rf"([^<>]*{re.escape(must_contain)}[^<>]*_csv\.zip).*?doclookupId=(\d+)",
        re.IGNORECASE | re.DOTALL,
    )
    out = []
    seen = set()
    for filename, doc_id in pattern.findall(html):
        filename = filename.strip()
        if (filename, doc_id) not in seen:
            seen.add((filename, doc_id))
            out.append((filename, f"{ERCOT_BASE}/misdownload/servlets/mirDownload?mimic_duns=000000000&doclookupId={doc_id}"))
    return out


def hour_ending_datetime(date_text: str, hour: int) -> pd.Timestamp:
    date = datetime.strptime(str(date_text), "%m/%d/%Y")
    if hour == 24:
        dt = date + timedelta(days=1)
    else:
        dt = date.replace(hour=hour)
    return pd.Timestamp(dt)


def read_first_csv_from_zip(zip_bytes: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError("ZIP did not contain a CSV file")
        with z.open(csv_names[0]) as f:
            return pd.read_csv(f)


def build_wind_generation() -> pd.DataFrame:
    html = download_bytes(WIND_REPORT_URL).decode(errors="ignore")
    links = parse_report_zip_links(html, "WPPHRLYAVGACTNP")
    if not links:
        raise RuntimeError("Could not find ERCOT wind-generation CSV ZIP links")

    latest_name, latest_url = links[0]
    raw = read_first_csv_from_zip(download_bytes(latest_url))
    actual = raw[raw["GEN_LZ_WEST"].notna()].copy()
    actual["datetime"] = [
        hour_ending_datetime(d, int(h))
        for d, h in zip(actual["DELIVERY_DATE"], actual["HOUR_ENDING"])
    ]
    actual = actual.sort_values("datetime").drop_duplicates("datetime")
    actual["power"] = actual["GEN_LZ_WEST"].astype(float)
    actual["power_source_file"] = latest_name
    return actual[["datetime", "power", "GEN_LZ_WEST", "SYSTEM_WIDE_GEN", "power_source_file"]]


def build_load(year: int) -> pd.DataFrame:
    html = download_bytes(LOAD_ARCHIVE_URL).decode(errors="ignore")
    match = re.search(rf'href="([^"]*Native_Load_{year}\.zip)"', html)
    if not match:
        match = re.search(rf"(https://www\.ercot\.com/files/docs/[^\s\"']*Native_Load_{year}\.zip)", html)
    if not match:
        raise RuntimeError(f"Could not find Native_Load_{year}.zip")

    load_url = match.group(1)
    if load_url.startswith("/"):
        load_url = ERCOT_BASE + load_url
    zip_path = save_download(load_url, TMP_DIR / f"Native_Load_{year}.zip")

    with zipfile.ZipFile(zip_path) as z:
        xlsx_name = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))][0]
        with z.open(xlsx_name) as f:
            load = pd.read_excel(f)

    load["datetime"] = pd.to_datetime(load["Hour Ending"].astype(str), format="%m/%d/%Y %H:%M", errors="coerce")
    # Pandas cannot parse 24:00 directly; fix those rows.
    bad = load["datetime"].isna()
    if bad.any():
        fixed = []
        for value in load.loc[bad, "Hour Ending"].astype(str):
            date_part, hour_part = value.split()
            hour = int(hour_part.split(":")[0])
            fixed.append(hour_ending_datetime(date_part, hour))
        load.loc[bad, "datetime"] = fixed
    load["load"] = load["WEST"].astype(float)
    load["load_source"] = f"Native_Load_{year}.zip WEST actual"
    return load[["datetime", "load", "WEST", "load_source"]]


def parse_hour_ending_text(date_text: str, hour_text: str) -> pd.Timestamp:
    hour = int(str(hour_text).split(":")[0])
    return hour_ending_datetime(date_text, hour)


def build_load_forecast() -> pd.DataFrame:
    html = download_bytes(LOAD_FORECAST_URL).decode(errors="ignore")
    links = parse_report_zip_links(html, "LFCWEATHERNP")
    if not links:
        raise RuntimeError("Could not find ERCOT weather-zone load forecast CSV ZIP links")

    latest_name, latest_url = links[0]
    forecast = read_first_csv_from_zip(download_bytes(latest_url))
    forecast["datetime"] = [
        parse_hour_ending_text(d, h)
        for d, h in zip(forecast["DeliveryDate"], forecast["HourEnding"])
    ]
    forecast["load_forecast"] = forecast["West"].astype(float)
    forecast["load_forecast_source"] = f"{latest_name} West forecast"
    return forecast[["datetime", "load_forecast", "load_forecast_source"]]


def parse_lmp_datetime_from_filename(filename: str) -> datetime | None:
    match = re.search(r"LMPSROSNODENP\d+_(\d{8})_(\d{6})_csv\.zip", filename)
    if not match:
        return None
    return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")


def build_pyron_hourly_lmp(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    html = download_bytes(LMP_REPORT_URL).decode(errors="ignore")
    links = parse_report_zip_links(html, "LMPSROSNODENP")
    if not links:
        raise RuntimeError("Could not find ERCOT resource-node LMP CSV ZIP links")

    start_pad = start.to_pydatetime() - timedelta(hours=1)
    end_pad = end.to_pydatetime() + timedelta(hours=1)
    selected = []
    for filename, url in links:
        dt = parse_lmp_datetime_from_filename(filename)
        if dt and start_pad <= dt <= end_pad:
            selected.append((filename, url))

    rows = []
    for i, (filename, url) in enumerate(selected, start=1):
        try:
            df = read_first_csv_from_zip(download_bytes(url))
            sub = df[df["SettlementPoint"].astype(str).eq("PYR_PYRON1")]
            if sub.empty:
                continue
            row = sub.iloc[0]
            ts = pd.to_datetime(row["SCEDTimestamp"])
            rows.append(
                {
                    "sced_timestamp": ts,
                    "datetime": ts.floor("h"),
                    "price_sample": float(row["LMP"]),
                    "price_source_file": filename,
                }
            )
        except Exception as exc:
            print(f"Skipping LMP file {filename}: {exc}")

    if not rows:
        raise RuntimeError("No PYR_PYRON1 rows found in selected LMP files")

    samples = pd.DataFrame(rows)
    hourly = (
        samples.groupby("datetime", as_index=False)
        .agg(price=("price_sample", "mean"), price_sample_count=("price_sample", "size"))
    )
    return hourly


def hrrr_speed_for_local_hour(local_hour: pd.Timestamp) -> dict[str, float | str]:
    # ERCOT hour-ending timestamps are in Central market time. In July that is CDT (UTC-5).
    local_dt = local_hour.to_pydatetime().replace(tzinfo=CENTRAL)
    utc_dt = local_dt.astimezone(timezone.utc).replace(tzinfo=None)
    h = Herbie(utc_dt, model="hrrr", product="nat", fxx=0, save_dir=str(TMP_DIR / "hrrr"))
    ds = h.xarray(search="(?:UGRD|VGRD):80 m above ground")
    lat = ds.latitude.values
    lon = ds.longitude.values
    dist = (lat - PYRON_LAT) ** 2 + (lon - PYRON_LON_360) ** 2
    idx = np.unravel_index(np.nanargmin(dist), dist.shape)
    u = float(ds["u"].values[idx])
    v = float(ds["v"].values[idx])
    speed = math.sqrt(u * u + v * v)
    return {
        "datetime": local_hour,
        "speed": speed,
        "hrrr_u80": u,
        "hrrr_v80": v,
        "hrrr_lat": float(lat[idx]),
        "hrrr_lon": float(lon[idx]),
        "hrrr_valid_utc": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_hrrr_speeds(hours: list[pd.Timestamp]) -> pd.DataFrame:
    rows = []
    for i, hour in enumerate(hours, start=1):
        print(f"HRRR {i}/{len(hours)} {hour}")
        try:
            rows.append(hrrr_speed_for_local_hour(hour))
        except Exception as exc:
            print(f"HRRR failed for {hour}: {exc}")
            rows.append({"datetime": hour, "speed": np.nan})
    return pd.DataFrame(rows)


def main() -> None:
    generation = build_wind_generation()
    start = generation["datetime"].min()
    end = generation["datetime"].max()
    year = int(start.year)

    print(f"Actual generation window: {start} to {end} ({len(generation)} hours)")
    load = build_load(year)
    load_forecast = build_load_forecast()
    price = build_pyron_hourly_lmp(start, end)
    speed = build_hrrr_speeds(generation["datetime"].tolist())

    merged = generation.merge(speed, on="datetime", how="left")
    merged = merged.merge(price, on="datetime", how="left")
    merged = merged.merge(load, on="datetime", how="left")
    merged = merged.merge(load_forecast, on="datetime", how="left")
    merged["load"] = merged["load"].fillna(merged["load_forecast"])
    merged["load_source"] = merged["load_source"].fillna(merged["load_forecast_source"])
    merged = merged.sort_values("datetime")

    exact = merged[["datetime", "speed", "power", "price", "load"]].dropna().copy()
    exact["datetime"] = exact["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    exact_start = pd.to_datetime(exact["datetime"]).min()
    exact_end = pd.to_datetime(exact["datetime"]).max()
    start_label = exact_start.strftime("%Y%m%d%H")
    end_label = exact_end.strftime("%Y%m%d%H")
    exact_path = OUT_DIR / f"newest_pyron_shaped_dataset_{start_label}_{end_label}.csv"
    expanded_path = OUT_DIR / f"newest_pyron_shaped_dataset_{start_label}_{end_label}_with_sources.csv"
    notes_path = OUT_DIR / f"newest_pyron_shaped_dataset_{start_label}_{end_label}_README.md"

    exact.to_csv(exact_path, index=False)
    merged.to_csv(expanded_path, index=False)

    with notes_path.open("w") as f:
        f.write("# Newest Pyron-Shaped Dataset\n\n")
        f.write(f"Rows: {len(exact)}\n\n")
        f.write(f"Complete-row time window: {exact_start} to {exact_end}\n\n")
        f.write(f"Raw generation window checked: {start} to {end}\n\n")
        f.write("## Columns in exact CSV\n\n")
        f.write("- `datetime`: ERCOT hour-ending timestamp in Central market time.\n")
        f.write("- `speed`: HRRR 80 m wind speed near the Pyron coordinate.\n")
        f.write("- `power`: ERCOT `GEN_LZ_WEST` actual wind generation, used as the current public generation proxy.\n")
        f.write("- `price`: ERCOT report 12300 `PYR_PYRON1` LMP averaged to hourly.\n")
        f.write("- `load`: ERCOT native load archive `WEST` actual when available; otherwise ERCOT report 12312 `West` load forecast.\n\n")
        f.write("## Important caveat\n\n")
        f.write(
            "This matches the old Pyron dataset shape, but `power` is not confirmed Pyron-specific generation. "
            "It is ERCOT West-zone wind generation from report 13028. If we obtain updated `PYR_PYRON1&2` "
            "hourly generation, that column should replace `GEN_LZ_WEST`.\n"
        )

    print(f"Wrote {exact_path}")
    print(f"Wrote {expanded_path}")
    print(f"Wrote {notes_path}")
    print(exact.tail().to_string(index=False))


if __name__ == "__main__":
    main()

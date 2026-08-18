"""Shared physical annual state-of-charge settlement rules.

The dispatch experiments are chronological and may charge storage only from
wind.  An annual target therefore cannot be implemented by resetting SoC at a
year boundary.  This module supplies a causal corridor that gradually reserves
enough energy before each boundary and lands exactly on the requested target.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SocCorridor:
    lower_mwh: float
    upper_mwh: float
    target_mwh: float | None
    active: bool
    boundary: pd.Timestamp | None
    hours_to_boundary: int | None


def next_target_corridor(
    timestamp: pd.Timestamp,
    final_timestamp: pd.Timestamp,
    annual_target_mwh: float | None,
    final_target_mwh: float | None,
    min_soc_mwh: float,
    max_soc_mwh: float,
    storage_power_mw: float,
    rte: float,
    settlement_hours: int,
) -> SocCorridor:
    """Return causal end-of-hour SoC bounds for the next required boundary."""
    stamp = pd.Timestamp(timestamp)
    final_stamp = pd.Timestamp(final_timestamp)
    candidates: list[tuple[pd.Timestamp, float]] = []

    calendar_end = pd.Timestamp(year=stamp.year, month=12, day=31, hour=23)
    if annual_target_mwh is not None and stamp <= calendar_end <= final_stamp:
        candidates.append((calendar_end, float(annual_target_mwh)))
    if final_target_mwh is not None and stamp <= final_stamp:
        candidates.append((final_stamp, float(final_target_mwh)))

    if not candidates:
        return SocCorridor(min_soc_mwh, max_soc_mwh, None, False, None, None)

    boundary, target = min(candidates, key=lambda item: item[0])
    target = min(max(target, min_soc_mwh), max_soc_mwh)
    hours_to_boundary = int(round((boundary - stamp) / pd.Timedelta(hours=1)))
    settlement_hours = max(1, int(settlement_hours))
    if hours_to_boundary >= settlement_hours:
        return SocCorridor(
            min_soc_mwh,
            max_soc_mwh,
            target,
            False,
            boundary,
            hours_to_boundary,
        )

    # Charging availability is uncertain, so the lower bound cannot rise by a
    # fixed amount every hour. The executor instead greedily charges from
    # available wind until the target is reached, then protects that reserve.
    lower = min_soc_mwh
    max_soc_reduction_remaining = hours_to_boundary * storage_power_mw / rte
    upper = min(max_soc_mwh, target + max_soc_reduction_remaining)
    if hours_to_boundary == 0:
        lower = target
        upper = target
    return SocCorridor(lower, upper, target, True, boundary, hours_to_boundary)

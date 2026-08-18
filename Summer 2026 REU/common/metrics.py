"""Frozen economic constants shared by the Summer 2026 controlled experiment."""

from __future__ import annotations


FCR = 0.065
WIND_CAPEX_USD_PER_KW = 1968.0
WIND_OPEX_USD_PER_KW_YEAR = 43.0
CAES_CAPEX_USD_PER_KW = 1125.33
CAES_OPEX_USD_PER_KW_YEAR = 15.43


def annualized_wind_cost(wind_rating_mw: float = 249.0) -> float:
    wind_kw = float(wind_rating_mw) * 1000.0
    return float(
        WIND_CAPEX_USD_PER_KW * wind_kw * FCR
        + WIND_OPEX_USD_PER_KW_YEAR * wind_kw
    )


def annualized_dispatch_cost(
    wind_rating_mw: float = 249.0,
    storage_power_mw: float = 100.0,
) -> float:
    storage_kw = float(storage_power_mw) * 1000.0
    storage_cost = (
        CAES_CAPEX_USD_PER_KW * storage_kw * FCR
        + CAES_OPEX_USD_PER_KW_YEAR * storage_kw
    )
    return float(annualized_wind_cost(wind_rating_mw) + storage_cost)


def cove(cost: float, price_weighted_revenue: float) -> float:
    if price_weighted_revenue <= 0:
        raise ValueError("COVE denominator must be positive.")
    return float(cost / price_weighted_revenue)

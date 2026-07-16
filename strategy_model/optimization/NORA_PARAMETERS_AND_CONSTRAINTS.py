"""Reviewer-facing summary of the storage parameters and MILP constraints.

This file does not replace the optimizer.  The active Gurobi implementation is
`rolling_horizon_gurobi_dispatch.py`.  This file is the quick place to show
Chris/reviewers exactly what physical rules the dispatch model is supposed to
follow.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageCase:
    name: str
    storage_power_mw: float
    duration_hours: float
    round_trip_efficiency: float
    depth_of_discharge: float
    grid_export_cap_mw: float

    @property
    def energy_capacity_mwh(self) -> float:
        return self.storage_power_mw * self.duration_hours

    @property
    def min_soc_mwh(self) -> float:
        return self.energy_capacity_mwh * (1.0 - self.depth_of_discharge)

    @property
    def mid_soc_mwh(self) -> float:
        return 0.5 * (self.min_soc_mwh + self.energy_capacity_mwh)


NORA_CAES_100MW_10H = StorageCase(
    name="Nora matching CAES case",
    storage_power_mw=100.0,
    duration_hours=10.0,
    round_trip_efficiency=0.55,
    depth_of_discharge=0.80,
    grid_export_cap_mw=249.0,
)

B6_ARCHITECTURES = {
    "A": {"energy_capacity_mwh": 600.0, "soc_20pct_mwh": 120.0},
    "B": {"energy_capacity_mwh": 600.0, "soc_20pct_mwh": 120.0},
    "C": {"energy_capacity_mwh": 1000.0, "soc_20pct_mwh": 200.0},
}

CONSTRAINTS = [
    "State of charge is bounded: Cmin <= SoC(t) <= Cmax.",
    "Charging power is bounded by the storage power rating.",
    "Discharging power is bounded by the storage power rating.",
    "A binary mode prevents simultaneous charging and discharging.",
    "Discharge cannot use more energy than is available above minimum SoC.",
    "Storage can charge only from wind; there is no grid charging.",
    "Direct wind plus charging cannot exceed wind generation.",
    "Delivered power equals direct wind plus storage discharge.",
    "Delivered power cannot exceed the 249 MW grid export cap.",
    "SoC is chronological: SoC(t+1) = SoC(t) + charge - discharge / RTE.",
    "N+1 SoC indexing is used when a final state is required.",
    "Terminal SoC rules are explicit: equal-initial, no-empty, none, or the B6 annual terminal rule.",
    "Revenue is price times realized delivered power.",
    "COVE is annualized cost divided by price-weighted delivered energy.",
]


def print_summary() -> None:
    case = NORA_CAES_100MW_10H
    print("NORA / CAES REFERENCE CASE")
    print(f"storage power:       {case.storage_power_mw:.0f} MW")
    print(f"duration:            {case.duration_hours:.0f} h")
    print(f"energy capacity:     {case.energy_capacity_mwh:.0f} MWh")
    print(f"RTE:                 {case.round_trip_efficiency:.2f}")
    print(f"DoD:                 {case.depth_of_discharge:.2f}")
    print(f"Cmin:                {case.min_soc_mwh:.0f} MWh")
    print(f"middle SoC:          {case.mid_soc_mwh:.0f} MWh")
    print(f"grid export cap:     {case.grid_export_cap_mw:.0f} MW")
    print()
    print("B6 ANNUAL 20% SOC CASES")
    for name, values in B6_ARCHITECTURES.items():
        print(
            f"architecture {name}: capacity={values['energy_capacity_mwh']:.0f} MWh, "
            f"min/initial/final SoC={values['soc_20pct_mwh']:.0f} MWh"
        )
    print()
    print("CONSTRAINT CHECKLIST")
    for number, constraint in enumerate(CONSTRAINTS, start=1):
        print(f"{number:02d}. {constraint}")
    print()
    print("Main implementation: strategy_model/optimization/rolling_horizon_gurobi_dispatch.py")
    print("Scenario implementation: strategy_model/optimization/run_uncertainty_aware_dispatch.py")
    print("B6 canonical runner: strategy_model/optimization/B6_CANONICAL_RUNNER.py")
    print("B6 canonical outputs: strategy_model/optimization/b6_final_results/")


if __name__ == "__main__":
    print_summary()

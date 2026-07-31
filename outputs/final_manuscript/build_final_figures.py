from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path("/Users/davidvalenta/deep-wind-model-dispatch")
SUMMER = ROOT / "Summer 2026 REU"
OUT = ROOT / "outputs" / "final_manuscript" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 13,
    "axes.titlesize": 18,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 11,
    "figure.dpi": 180,
    "savefig.dpi": 300,
})


def savefig(path: Path):
    plt.tight_layout(pad=1.35)
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


def add_value_labels(ax, bars, fmt="{:.2f}", dx=0.0):
    for bar in bars:
        width = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        ax.text(width + dx, y, fmt.format(width), va="center", ha="left", fontsize=11)


def draw_ladder():
    steps = [
        ("0", "Baseload", "Wind sold as it comes", "#E5E7EB"),
        ("1", "Causal ridge forecast", "Predict wind and price from past data", "#DBEAFE"),
        ("2", "Rolling-horizon Gurobi", "Plan ahead, execute, replan", "#DCFCE7"),
        ("3", "Scenario dispatch", "Plan across several possible futures", "#FEF3C7"),
        ("4", "Oracle upper bound", "Perfect future information, not deployable", "#FCE7F3"),
    ]
    fig, ax = plt.subplots(figsize=(13.5, 5.2))
    ax.axis("off")
    x_positions = np.linspace(0.04, 0.83, len(steps))
    y = 0.42
    for i, (num, title, desc, color) in enumerate(steps):
        x = x_positions[i]
        box = FancyBboxPatch(
            (x, y), 0.15, 0.32,
            boxstyle="round,pad=0.014,rounding_size=0.025",
            transform=ax.transAxes,
            fc=color,
            ec="#334155",
            lw=1.3,
        )
        ax.add_patch(box)
        ax.text(x + 0.075, y + 0.235, f"Step {num}", ha="center", va="center",
                fontsize=12, weight="bold", transform=ax.transAxes, color="#0F172A")
        ax.text(x + 0.075, y + 0.16, title, ha="center", va="center",
                fontsize=12.5, weight="bold", transform=ax.transAxes, color="#111827")
        ax.text(x + 0.075, y + 0.075, desc, ha="center", va="center",
                fontsize=10.5, transform=ax.transAxes, color="#334155", wrap=True)
        if i < len(steps) - 1:
            arrow = FancyArrowPatch(
                (x + 0.153, y + 0.16), (x_positions[i + 1] - 0.006, y + 0.16),
                arrowstyle="-|>", mutation_scale=16, lw=1.6, color="#0F766E",
                transform=ax.transAxes,
            )
            ax.add_patch(arrow)
    ax.text(0.5, 0.92, "The final paper is built as a ladder of evidence",
            ha="center", va="center", fontsize=20, weight="bold", color="#0F172A",
            transform=ax.transAxes)
    ax.text(0.5, 0.13,
            "Each step adds one idea while keeping the comparison tied to baseload and explicit storage constraints.",
            ha="center", va="center", fontsize=13, color="#475569", transform=ax.transAxes)
    plt.savefig(OUT / "fig01_research_ladder.png", bbox_inches="tight", facecolor="white")
    plt.close()


def draw_forecast_rmse():
    df = pd.read_csv(SUMMER / "causal ridge regression" / "results" / "forecast_model_rmse_comparison.csv")
    labels = {
        "causal_lag_prediction_mw": "Causal ridge\n(this project)",
        "lag1_persistence_prediction_mw": "Last-hour\npersistence",
        "speed_power_curve_prediction_mw": "Speed/power\ncurve",
        "rnn_preds": "Prior RNN\nbenchmark",
        "physics_preds": "Physics\nbaseline",
        "prob_preds": "Probabilistic\nbaseline",
    }
    df["label"] = df["model"].map(labels).fillna(df["model"])
    df = df.sort_values("rmse_mw", ascending=True)
    colors = ["#0F766E" if "Causal ridge" in x else "#94A3B8" for x in df["label"]]

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    bars = ax.barh(df["label"], df["rmse_mw"], color=colors, edgecolor="#334155", linewidth=0.8)
    ax.invert_yaxis()
    ax.set_xlabel("Power forecast RMSE (MW). Lower is better.")
    ax.set_title("Causal ridge produced the lowest power forecast error")
    ax.grid(axis="x", alpha=0.23)
    ax.set_xlim(0, max(df["rmse_mw"]) * 1.23)
    add_value_labels(ax, bars, "{:.2f} MW", dx=1.0)
    ax.text(
        0.985, 0.08,
        "Why it matters: the optimizer can only dispatch well if the forecast it sees is useful.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11.5,
        color="#334155",
        bbox=dict(boxstyle="round,pad=0.45", fc="#F8FAFC", ec="#CBD5E1"),
    )
    savefig(OUT / "fig02_forecast_rmse.png")


def draw_milp_flow():
    fig, ax = plt.subplots(figsize=(12.8, 5.3))
    ax.axis("off")
    boxes = [
        (0.04, 0.55, 0.19, 0.25, "Forecast inputs", "wind power + price"),
        (0.30, 0.55, 0.20, 0.25, "MILP/Gurobi", "charge, discharge,\ndirect wind, SoC"),
        (0.58, 0.55, 0.18, 0.25, "Realized operation", "execute first action\nwith actual wind"),
        (0.82, 0.55, 0.14, 0.25, "Score", "revenue + COVE"),
        (0.30, 0.14, 0.50, 0.22, "Physical constraints", "SoC limits, no grid charging, wind-only charging, power rating, 249 MW grid cap, terminal SoC"),
    ]
    for i, (x, y, w, h, title, desc) in enumerate(boxes):
        fc = ["#DBEAFE", "#DCFCE7", "#FEF3C7", "#FCE7F3", "#F1F5F9"][i]
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.018,rounding_size=0.018",
                             transform=ax.transAxes, fc=fc, ec="#334155", lw=1.2)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center", fontsize=14,
                weight="bold", transform=ax.transAxes, color="#0F172A")
        ax.text(x + w / 2, y + h * 0.34, desc, ha="center", va="center", fontsize=11.5,
                transform=ax.transAxes, color="#334155")
    for start, end in [((0.23, 0.675), (0.30, 0.675)), ((0.50, 0.675), (0.58, 0.675)),
                       ((0.76, 0.675), (0.82, 0.675)), ((0.55, 0.36), (0.55, 0.55))]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, lw=1.7,
                                     color="#0F766E", transform=ax.transAxes))
    ax.text(0.5, 0.93, "How revenue and COVE are produced in code", ha="center",
            fontsize=20, weight="bold", color="#0F172A", transform=ax.transAxes)
    ax.text(0.5, 0.045,
            "The optimizer plans with forecasts. The final score is calculated with what actually happened.",
            ha="center", fontsize=12.5, color="#475569", transform=ax.transAxes)
    plt.savefig(OUT / "fig03_dispatch_code_flow.png", bbox_inches="tight", facecolor="white")
    plt.close()


def draw_horizon_results():
    df = pd.read_csv(SUMMER / "rolling horizon" / "results" / "causal_ridge_rolling_horizon_summary.csv")
    causal = df[df["method"].str.contains("causal")].copy()
    horizons = causal["horizon_hours"].astype(int).to_list()
    gains = causal["improvement_vs_baseload_pct"].to_numpy()
    cove = causal["cove"].to_numpy()
    colors = ["#0F766E" if h == 48 else "#60A5FA" for h in horizons]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    bars = ax.bar([str(h) + " h" for h in horizons], gains, color=colors, edgecolor="#334155", linewidth=0.8)
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_xlabel("Gurobi planning horizon")
    ax.set_title("48 hours was the best realistic deterministic horizon")
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(gains) * 1.28)
    for bar, val, cv in zip(bars, gains, cove):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.15, f"{val:.2f}%\nCOVE {cv:.3f}",
                ha="center", va="bottom", fontsize=10.5)
    ax.text(0.02, 0.93, "Baseload COVE = 7.274", transform=ax.transAxes,
            ha="left", va="top", fontsize=11.5, color="#475569")
    savefig(OUT / "fig04_rolling_horizon_gain.png")

    fig, ax = plt.subplots(figsize=(11.2, 5.4))
    ax.plot(horizons, cove, marker="o", linewidth=3.0, color="#2563EB")
    ax.scatter([48], [cove[horizons.index(48)]], s=160, color="#0F766E", zorder=4,
               edgecolor="white", linewidth=1.5)
    ax.axhline(float(causal["baseload_cove"].iloc[0]), ls="--", lw=1.8, color="#64748B", label="Baseload COVE")
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_ylabel("COVE (lower is better)")
    ax.set_xlabel("Gurobi planning horizon")
    ax.set_title("Longer is not always better under forecast error")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    for h, cv in zip(horizons, cove):
        ax.text(h, cv + 0.022, f"{cv:.3f}", ha="center", va="bottom", fontsize=10.5,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))
    savefig(OUT / "fig05_rolling_horizon_cove.png")


def draw_scenario_results():
    df = pd.read_csv(SUMMER / "different scenarios" / "results" / "scenario_48h_full_ladder" / "uncertainty_aware_summary.csv")
    rows = df[df["candidate"].str.contains("scenario|single", regex=True)].copy()
    order = [
        "single_forecast_recourse_nowcast_gated",
        "three_scenario_expected_nowcast_gated",
        "five_scenario_expected_nowcast_gated",
        "seven_scenario_expected_nowcast_gated",
        "ten_scenario_expected_nowcast_gated",
    ]
    rows["candidate"] = pd.Categorical(rows["candidate"], order, ordered=True)
    rows = rows.sort_values("candidate")
    labels = ["1 forecast", "3 scenarios", "5 scenarios", "7 scenarios", "10 scenarios"]
    cove_red = rows["cove_reduction_vs_baseload_pct"].to_numpy()
    rev_gain = rows["revenue_gain_vs_baseload_pct"].to_numpy()
    colors = ["#93C5FD", "#0F766E", "#A7F3D0", "#FCD34D", "#FDA4AF"]

    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    x = np.arange(len(labels))
    bars = ax.bar(x, cove_red, color=colors, edgecolor="#334155", linewidth=0.8)
    ax.set_xticks(x, labels)
    ax.set_ylabel("COVE reduction vs baseload (%)")
    ax.set_title("Three scenarios gave the strongest uncertainty-aware result")
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(cove_red) * 1.28)
    for i, (bar, val, rev) in enumerate(zip(bars, cove_red, rev_gain)):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.55,
                f"{val:.2f}%\nrev +{rev:.2f}%", ha="center", va="bottom", fontsize=10.5)
    ax.text(0.02, 0.92, "All scenario cases use the selected 48 h planning setup.",
            transform=ax.transAxes, ha="left", va="top", fontsize=11.5, color="#475569")
    savefig(OUT / "fig06_scenario_cove_reduction.png")

    fig, ax1 = plt.subplots(figsize=(11.5, 5.8))
    ax2 = ax1.twinx()
    line1 = ax1.plot(labels, rev_gain, marker="o", color="#0F766E", linewidth=3.0, label="Revenue gain")
    line2 = ax2.plot(labels, cove_red, marker="s", color="#EA580C", linewidth=3.0, label="COVE reduction")
    ax1.set_ylabel("Revenue gain vs baseload (%)", color="#0F766E")
    ax2.set_ylabel("COVE reduction vs baseload (%)", color="#EA580C")
    ax1.set_title("Scenario count: value vs caution", pad=14)
    ax1.grid(axis="y", alpha=0.25)
    lines = line1 + line2
    ax1.legend(lines, [l.get_label() for l in lines], loc="lower center", ncol=2, frameon=True)
    for i, val in enumerate(rev_gain):
        ax1.text(i, val + 0.45, f"{val:.1f}%", ha="center", fontsize=10)
    for i, val in enumerate(cove_red):
        ax2.text(i, val - 0.7, f"{val:.1f}%", ha="center", fontsize=10, color="#9A3412")
    savefig(OUT / "fig07_scenario_tradeoff.png")


def draw_oracle_results():
    df = pd.read_csv(SUMMER / "oracle upper bound" / "results" / "oracle_upper_bound_summary.csv")
    oracle = df[df["method"] == "oracle"].copy()
    horizons = oracle["horizon_hours"].astype(int).to_list()
    gains = oracle["improvement_vs_baseload_pct"].to_numpy()
    cove = oracle["cove"].to_numpy()

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.plot(horizons, gains, marker="o", linewidth=3.0, color="#9333EA")
    ax.fill_between(horizons, gains, color="#E9D5FF", alpha=0.65)
    ax.set_xticks(horizons, [f"{h} h" for h in horizons])
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_xlabel("Oracle look-ahead horizon")
    ax.set_title("Oracle result is the upper bound, not a real controller")
    ax.grid(alpha=0.25)
    for h, g, cv in zip(horizons, gains, cove):
        ax.text(h, g + 0.45, f"{g:.2f}%\nCOVE {cv:.3f}", ha="center", va="bottom", fontsize=10.3)
    ax.set_ylim(min(gains) - 2, max(gains) + 4.2)
    savefig(OUT / "fig08_oracle_upper_bound.png")


def draw_information_surface():
    horizon_df = pd.read_csv(SUMMER / "rolling horizon" / "results" / "causal_ridge_rolling_horizon_summary.csv")
    causal = horizon_df[horizon_df["method"].str.contains("causal")].copy()
    oracle = horizon_df[horizon_df["method"] == "oracle"].copy()
    scenario_df = pd.read_csv(SUMMER / "different scenarios" / "results" / "scenario_48h_full_ladder" / "uncertainty_aware_summary.csv")
    scen_best = scenario_df[scenario_df["candidate"] == "three_scenario_expected_nowcast_gated"].iloc[0]

    horizons = np.array([24, 48, 72, 168], dtype=float)
    y_labels = ["causal\nforecast", "scenario\n48 h", "oracle\nupper bound"]
    y = np.arange(len(y_labels), dtype=float)
    Z = np.zeros((len(y), len(horizons)))
    Z[0, :] = causal.set_index("horizon_hours").loc[[24, 48, 72, 168], "improvement_vs_baseload_pct"].to_numpy()
    Z[1, :] = scen_best["cove_reduction_vs_baseload_pct"]
    Z[2, :] = oracle.set_index("horizon_hours").loc[[24, 48, 72, 168], "improvement_vs_baseload_pct"].to_numpy()
    X, Y = np.meshgrid(horizons, y)

    fig = plt.figure(figsize=(10.2, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="#334155", linewidth=0.45, antialiased=True, alpha=0.96)
    ax.set_title("Information quality raises the dispatch ceiling", pad=18, fontsize=17, weight="bold")
    ax.set_xlabel("Planning horizon (hours)", labelpad=10)
    ax.set_ylabel("Information case", labelpad=12)
    ax.set_zlabel("COVE gain (%)", labelpad=12)
    ax.set_xticks(horizons)
    ax.set_yticks(y)
    ax.set_yticklabels(y_labels)
    ax.view_init(elev=24, azim=-132)
    cbar = fig.colorbar(surf, ax=ax, shrink=0.68, pad=0.12)
    cbar.set_label("COVE improvement (%)")
    ax.text(48, 1, float(scen_best["cove_reduction_vs_baseload_pct"]) + 1.3, "Best scenario\n23.19%",
            color="#111827", fontsize=11, ha="center",
            path_effects=[patheffects.withStroke(linewidth=3, foreground="white")])
    plt.subplots_adjust(left=0.03, right=0.86, bottom=0.05, top=0.92)
    plt.savefig(OUT / "fig09_information_surface_3d.png", bbox_inches="tight", facecolor="white")
    plt.close()


def draw_final_ladder_numbers():
    labels = ["Baseload\nreference", "Single forecast\n48 h controller", "Best scenario\n48 h controller", "Oracle\nupper bound"]
    values = [0.0, 19.403382, 23.189458, 32.833140]
    colors = ["#CBD5E1", "#60A5FA", "#0F766E", "#9333EA"]
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    bars = ax.bar(labels, values, color=colors, edgecolor="#334155", linewidth=0.8)
    ax.set_ylabel("COVE improvement vs baseload (%)")
    ax.set_title("Final result ladder: from reference case to upper bound")
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, 38)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.8, f"{val:.2f}%",
                ha="center", va="bottom", fontsize=12, weight="bold")
    savefig(OUT / "fig10_final_ladder_numbers.png")


def main():
    draw_ladder()
    draw_forecast_rmse()
    draw_milp_flow()
    draw_horizon_results()
    draw_scenario_results()
    draw_oracle_results()
    draw_information_surface()
    draw_final_ladder_numbers()
    print(f"Figures written to {OUT}")


if __name__ == "__main__":
    main()

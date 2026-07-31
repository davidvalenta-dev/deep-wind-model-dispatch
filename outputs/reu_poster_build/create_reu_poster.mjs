import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT_DIR = "/Users/davidvalenta/deep-wind-model-dispatch/outputs/reu_poster_build";
const FINAL_PPTX = "/Users/davidvalenta/deep-wind-model-dispatch/outputs/Deep_Wind_REU_Research_Poster_2026.pptx";
const REPO = "/Users/davidvalenta/deep-wind-model-dispatch";

const figures = {
  pipeline: `${REPO}/Summer 2026 REU/paper overview figures/figures/paper_fig01_pipeline.png`,
  ladder: `${REPO}/Summer 2026 REU/paper overview figures/figures/paper_fig10_ladder.png`,
  constraints: `${REPO}/Summer 2026 REU/paper overview figures/figures/paper_fig11_constraints.png`,
  forecastRmse: `${REPO}/Summer 2026 REU/causal ridge regression/figures/step1_forecast_rmse_comparison.png`,
  forecastWeek: `${REPO}/Summer 2026 REU/causal ridge regression/figures/step1_example_forecast_week.png`,
  rollingCove: `${REPO}/Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_improvement.png`,
  rollingRevenue: `${REPO}/Summer 2026 REU/rolling horizon/figures/step2_revenue_by_horizon.png`,
  scenarioGain: `${REPO}/Summer 2026 REU/different scenarios/figures/step3_scenario_cove_improvement.png`,
  scenarioTradeoff: `${REPO}/Summer 2026 REU/different scenarios/figures/step3_revenue_cove_tradeoff.png`,
  oracle: `${REPO}/Summer 2026 REU/oracle upper bound/figures/step4_oracle_improvement_by_horizon.png`,
  baseWeek: `${REPO}/Summer 2026 REU/100 MW baseload/figures/step0_100mw_baseload_2014_2023_example_week.png`,
};

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function imgBlob(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function addText(slide, text, x, y, w, h, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: opts.size ?? 24,
    bold: opts.bold ?? false,
    color: opts.color ?? "#111827",
    alignment: opts.align ?? "left",
    fontFace: opts.font ?? "Aptos",
  };
  return shape;
}

function addBox(slide, x, y, w, h, fill = "#ffffff", line = "#cbd5e1") {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: 2 },
    borderRadius: 16,
  });
}

function addSectionTitle(slide, title, x, y, w, color = "#0f766e") {
  addText(slide, title, x, y, w, 38, { size: 30, bold: true, color });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y + 42, width: w, height: 4 },
    fill: color,
    line: { style: "solid", fill: color, width: 0 },
  });
}

function addBullets(slide, items, x, y, w, h, size = 20) {
  const text = items.map((item) => `• ${item}`).join("\n");
  addText(slide, text, x, y, w, h, { size, color: "#1f2937" });
}

function addColoredBullets(slide, items, x, y, w, h, size = 20, color = "#1f2937") {
  const text = items.map((item) => `• ${item}`).join("\n");
  addText(slide, text, x, y, w, h, { size, color });
}

async function addImage(slide, filePath, x, y, w, h, alt) {
  addBox(slide, x - 6, y - 6, w + 12, h + 12, "#ffffff", "#d1d5db");
  slide.images.add({
    blob: await imgBlob(filePath),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
  });
}

function addMetric(slide, label, value, sub, x, y, w, color) {
  addBox(slide, x, y, w, 156, "#f8fafc", color);
  addText(slide, value, x + 18, y + 16, w - 36, 42, { size: 32, bold: true, color });
  addText(slide, label, x + 18, y + 64, w - 36, 42, { size: 17, bold: true, color: "#111827" });
  addText(slide, sub, x + 18, y + 112, w - 36, 30, { size: 14, color: "#475569" });
}

function addTable(slide, x, y, w, h) {
  const rows = [
    ["Stage", "Main idea", "Best result vs 100 MW"],
    ["Benchmark", "100 MW rule-based CAES", "reference"],
    ["Forecast", "Causal lag/ridge predicts wind power before dispatch", "RMSE 21.24 MW"],
    ["Rolling horizon", "Gurobi uses one predicted future and replans", "48 h: 20.63% COVE gain"],
    ["Scenarios", "Several futures are optimized together", "3 scenarios: 40.18% COVE gain"],
    ["Oracle", "Perfect future wind and price; not deployable", "168 h: 40.87% COVE gain"],
  ];
  const colW = [0.23, 0.45, 0.32].map((f) => w * f);
  const rowH = h / rows.length;
  for (let r = 0; r < rows.length; r++) {
    let xx = x;
    for (let c = 0; c < 3; c++) {
      const fill = r === 0 ? "#0f766e" : r % 2 ? "#ecfdf5" : "#ffffff";
      slide.shapes.add({
        geometry: "rect",
        position: { left: xx, top: y + r * rowH, width: colW[c], height: rowH },
        fill,
        line: { style: "solid", fill: "#94a3b8", width: 1 },
      });
      addText(slide, rows[r][c], xx + 10, y + r * rowH + 8, colW[c] - 20, rowH - 14, {
        size: r === 0 ? 18 : 16,
        bold: r === 0 || c === 0,
        color: r === 0 ? "#ffffff" : "#111827",
      });
      xx += colW[c];
    }
  }
}

async function main() {
  await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
  await fs.mkdir(OUT_DIR, { recursive: true });

  const deck = Presentation.create({ slideSize: { width: 1920, height: 2880 } });
  const slide = deck.slides.add();
  slide.background.fill = "#f6f7f4";

  // Header
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1920, height: 240 },
    fill: "#315f5b",
    line: { style: "solid", fill: "#315f5b", width: 0 },
  });
  addText(slide, "Forecast-Aware Rolling-Horizon Optimization for Hybrid Wind-Storage Dispatch", 70, 24, 1420, 94, {
    size: 39,
    bold: true,
    color: "#ffffff",
  });
  addText(slide, "David Valenta, North Carolina State University  |  Dr. Chris Qin, Washington State University", 72, 128, 1320, 34, {
    size: 24,
    color: "#d1fae5",
  });
  addText(slide, "Summer 2026 REU  |  Pyron wind farm case study  |  ERCOT price data  |  PNNL CAES assumptions", 72, 170, 1420, 34, {
    size: 20,
    color: "#ecfdf5",
  });
  addBox(slide, 1510, 42, 330, 142, "#eef5ef", "#d6e7df");
  addText(slide, "Main takeaway", 1534, 58, 280, 28, { size: 20, bold: true, color: "#315f5b" });
  addText(slide, "Hourly uncertainty-aware dispatch gave the strongest COVE reduction while respecting storage limits.", 1534, 90, 282, 76, {
    size: 18,
    color: "#244743",
  });

  // Column coordinates
  const margin = 70;
  const gutter = 38;
  const colW = (1920 - 2 * margin - 2 * gutter) / 3;
  const x1 = margin;
  const x2 = margin + colW + gutter;
  const x3 = margin + 2 * (colW + gutter);
  let y = 280;

  // Left column: problem, data, constraints, forecast
  addBox(slide, x1, y, colW, 350, "#ffffff", "#b8d7d2");
  addSectionTitle(slide, "1. Problem and Goal", x1 + 24, y + 20, colW - 48, "#315f5b");
  addBullets(
    slide,
    [
      "Wind farms do not control when wind arrives.",
      "Electricity prices change hour by hour.",
      "Storage can hold wind energy and release it later.",
      "The goal is to choose direct delivery, charging, discharging, and curtailment to increase value.",
      "The hard part is making decisions before the future is known.",
    ],
    x1 + 30,
    y + 86,
    colW - 60,
    230,
    19,
  );
  addText(slide, "Main comparison: a 100 MW constant-output CAES benchmark. It is a realistic storage rule, while wind-only is secondary context.", x1 + 30, y + 294, colW - 60, 54, {
    size: 16,
    bold: true,
    color: "#315f5b",
  });

  await addImage(slide, figures.pipeline, x1 + 8, y + 380, colW - 16, 255, "Project pipeline from forecast to dispatch");
  addText(slide, "Figure 1. End-to-end pipeline: forecast wind/price, optimize dispatch with Gurobi, then score realized revenue and COVE.", x1 + 18, y + 642, colW - 36, 52, {
    size: 16,
    color: "#334155",
  });

  addBox(slide, x1, y + 720, colW, 360, "#ffffff", "#cbd5d8");
  addSectionTitle(slide, "2. Data and Storage Setup", x1 + 24, y + 742, colW - 48, "#486a86");
  addBullets(
    slide,
    [
      "Dataset: Pyron wind farm, 1980-2023 hourly records.",
      "Forecast training: historical data before 2014.",
      "Testing period: 2014-2023 unseen years.",
      "Price: ERCOT locational marginal price.",
      "Storage: CAES, 100 MW, 10 h, 1000 MWh capacity.",
      "SoC bounds: 200-1000 MWh; initial SoC: 600 MWh; RTE: 55%.",
      "All dispatch results carry SoC forward chronologically.",
    ],
    x1 + 30,
    y + 808,
    colW - 60,
    250,
    17,
  );

  await addImage(slide, figures.constraints, x1 + 8, y + 1110, colW - 16, 286, "MILP storage constraints");
  addText(slide, "Figure 2. Dispatch is constrained by wind-only charging, grid export, charge/discharge limits, and chronological SoC.", x1 + 18, y + 1402, colW - 36, 52, {
    size: 16,
    color: "#334155",
  });

  addBox(slide, x1, y + 1475, colW, 270, "#ffffff", "#bed4df");
  addSectionTitle(slide, "3. Forecasting", x1 + 24, y + 1497, colW - 48, "#3f6575");
  addBullets(
    slide,
    [
      "Causal lag/ridge uses only past information.",
      "It predicts generated power directly, not wind speed.",
      "Best forecast RMSE: 21.24 MW.",
      "This forecast feeds the realistic dispatch experiments.",
      "Other tested methods included persistence, speed-power curve, RNN, physics, and probabilistic outputs.",
    ],
    x1 + 30,
    y + 1565,
    colW - 60,
    170,
    16,
  );
  await addImage(slide, figures.forecastRmse, x1 + 8, y + 1778, colW - 16, 260, "Forecast RMSE comparison");
  addText(slide, "Figure 3. Causal lag/ridge had the lowest power-prediction RMSE among tested forecast outputs.", x1 + 18, y + 2044, colW - 36, 48, {
    size: 16,
    color: "#334155",
  });

  // Middle column
  await addImage(slide, figures.ladder, x2 + 8, y, colW - 16, 305, "Method ladder");
  addText(slide, "Figure 4. Research ladder: start from 100 MW benchmark, add forecasting, add rolling-horizon dispatch, add scenarios, then compare to oracle.", x2 + 18, y + 312, colW - 36, 60, {
    size: 16,
    color: "#334155",
  });

  addBox(slide, x2, y + 390, colW, 565, "#ffffff", "#cfc7dc");
  addSectionTitle(slide, "4. How the Optimizer Decides", x2 + 24, y + 412, colW - 48, "#5f5472");
  addText(slide, "Gurobi solves a mixed-integer linear program. It is the mathematical planner that chooses a feasible storage schedule under the rules below.", x2 + 30, y + 480, colW - 60, 58, {
    size: 18,
    color: "#1f2937",
  });
  addBullets(
    slide,
    [
      "P_direct: wind sent straight to the grid.",
      "P_charge: wind stored in CAES.",
      "P_discharge: stored energy released to the grid.",
      "SoC: storage energy carried forward through time.",
      "Curtailment: wind not used because of physical limits.",
    ],
    x2 + 30,
    y + 548,
    colW - 60,
    142,
    17,
  );
  addText(slide, "Rolling horizon means: plan ahead, execute the near-term action, update the battery, then solve again. Revenue uses realized delivered power times realized price. COVE is lower when delivered energy is more valuable.", x2 + 30, y + 710, colW - 60, 92, {
    size: 17,
    bold: true,
    color: "#4c405f",
  });
  await addImage(slide, figures.baseWeek, x2 + 18, y + 800, colW - 36, 140, "100 MW baseload example week");

  addTable(slide, x2, y + 990, colW, 410);

  await addImage(slide, figures.rollingCove, x2 + 8, y + 1415, colW - 16, 260, "Rolling horizon COVE gains");
  addText(slide, "Figure 5. Deterministic dispatch found that 48 h lookahead gave the best COVE gain under the 100 MW benchmark.", x2 + 18, y + 1682, colW - 36, 52, {
    size: 16,
    color: "#334155",
  });
  await addImage(slide, figures.rollingRevenue, x2 + 8, y + 1760, colW - 16, 220, "Rolling horizon revenue by horizon");
  addText(slide, "Figure 6. Longer horizons do not automatically win when forecasts are imperfect; 48 h balanced planning value and forecast error.", x2 + 18, y + 1988, colW - 36, 72, {
    size: 16,
    color: "#334155",
  });

  // Right column: results
  addBox(slide, x3, y, colW, 176, "#ffffff", "#e5c7aa");
  addSectionTitle(slide, "5. Key Results", x3 + 24, y + 20, colW - 48, "#8a5134");
  addText(slide, "Primary comparison: 100 MW constant-output CAES benchmark. Wind-only is side context. Higher COVE gain means the storage policy makes energy more valuable per cost.", x3 + 30, y + 86, colW - 60, 76, {
    size: 16,
    color: "#1f2937",
  });

  addMetric(slide, "Best forecast model", "21.24 MW", "causal lag/ridge RMSE", x3, y + 205, (colW - 18) / 2, "#3f6575");
  addMetric(slide, "Best deterministic dispatch", "20.63%", "48 h COVE gain vs 100 MW", x3 + (colW + 18) / 2, y + 205, (colW - 18) / 2, "#5f5472");
  addMetric(slide, "Best scenario controller", "40.18%", "3 scenarios, hourly replan", x3, y + 382, (colW - 18) / 2, "#557a5a");
  addMetric(slide, "Oracle upper bound", "40.87%", "168 h perfect future", x3 + (colW + 18) / 2, y + 382, (colW - 18) / 2, "#8a5134");

  await addImage(slide, figures.scenarioGain, x3 + 8, y + 580, colW - 16, 305, "Scenario COVE gain");
  addText(slide, "Figure 7. The hourly uncertainty-aware controller worked best with 3 scenarios; too many scenarios became conservative.", x3 + 18, y + 893, colW - 36, 52, {
    size: 16,
    color: "#334155",
  });

  await addImage(slide, figures.scenarioTradeoff, x3 + 8, y + 970, colW - 16, 285, "Scenario revenue-COVE tradeoff");
  addText(slide, "Figure 8. The best scenario case had the highest revenue and lowest COVE among scenario counts.", x3 + 18, y + 1261, colW - 36, 48, {
    size: 16,
    color: "#334155",
  });

  await addImage(slide, figures.oracle, x3 + 8, y + 1330, colW - 16, 285, "Oracle upper bound");
  addText(slide, "Figure 9. Oracle dispatch is not realistic because it knows the future, but it shows the ceiling for the controller.", x3 + 18, y + 1621, colW - 36, 48, {
    size: 16,
    color: "#334155",
  });

  addBox(slide, x3, y + 1710, colW, 340, "#ffffff", "#bdd8c1");
  addSectionTitle(slide, "6. Main Conclusion", x3 + 24, y + 1732, colW - 48, "#557a5a");
  addBullets(
    slide,
    [
      "Forecast quality matters, but dispatch logic matters too.",
      "A 48-hour deterministic lookahead was best when one forecast was used.",
      "Hourly uncertainty-aware replanning improved the best result because it corrected mistakes quickly.",
      "Three scenarios were enough to capture useful uncertainty without making the optimizer overly cautious.",
      "The project shows forecasting and optimization must be designed as one connected control system.",
    ],
    x3 + 30,
    y + 1800,
    colW - 60,
    190,
    16,
  );
  addText(slide, "Practical message: hybrid wind-storage control should tune the forecast horizon, replanning frequency, storage assumptions, and scenario count together, not separately.", x3 + 30, y + 1982, colW - 60, 58, {
    size: 17,
    bold: true,
    color: "#335a39",
  });

  // Bottom strip
  const bottomY = 2385;
  addBox(slide, margin, bottomY, 1780, 330, "#1f2933", "#1f2933");
  addText(slide, "Definitions for the reader", margin + 28, bottomY + 22, 420, 34, { size: 26, bold: true, color: "#ffffff" });
  addColoredBullets(
    slide,
    [
      "100 MW benchmark: rule-based storage case that tries to deliver 100 MW every hour.",
      "Wind-only: no storage; actual wind goes to the grid up to the 249 MW cap.",
      "Rolling horizon: solve the future, execute the near-term action, then solve again.",
      "Scenario dispatch: solve against several possible futures instead of one forecast.",
      "Oracle: perfect-future case used only as an upper bound.",
      "COVE: cost divided by valued delivered energy; lower is better.",
      "Constraint violation check: confirms storage and grid rules were not broken.",
    ],
    margin + 28,
    bottomY + 70,
    1060,
    220,
    16,
    "#e2e8f0",
  );
  addText(slide, "Acknowledgements", margin + 1140, bottomY + 22, 320, 34, { size: 26, bold: true, color: "#ffffff" });
  addText(
    slide,
    "Thank you to Dr. Chris Qin, Nora Hosseiniimeni, Zach Lawrence, Jessica Yao, and the WSU Summer Research Program. Data and assumptions draw from the Pyron wind-storage dataset, ERCOT LMP records, and PNNL CAES storage references.",
    margin + 1140,
    bottomY + 70,
    590,
    145,
    { size: 18, color: "#e2e8f0" },
  );
  addText(slide, "Contact: dvalent2@ncsu.edu", margin + 1140, bottomY + 230, 500, 32, { size: 20, bold: true, color: "#a7f3d0" });
  addText(slide, "Poster size: 20 in x 30 in", margin + 1140, bottomY + 264, 500, 26, { size: 15, color: "#cbd5e1" });

  // Footer rule
  slide.shapes.add({
    geometry: "rect",
    position: { left: 70, top: 2750, width: 1780, height: 4 },
    fill: "#7aa7a0",
    line: { style: "solid", fill: "#7aa7a0", width: 0 },
  });
  addText(slide, "All reported comparative metrics use the 100 MW constant-output benchmark as the primary reference; wind-only is secondary context.", 72, 2765, 1780, 34, {
    size: 17,
    color: "#475569",
    align: "center",
  });

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(FINAL_PPTX);
  await writeBlob(`${OUT_DIR}/poster_preview.png`, await deck.export({ slide, format: "png", scale: 1 }));
  await writeBlob(`${OUT_DIR}/poster_preview_2x.png`, await deck.export({ slide, format: "png", scale: 2 }));
  await fs.writeFile(`${OUT_DIR}/source-notes.txt`, [
    "Poster created from local repo figures and result CSVs.",
    "Poster instruction PDF required 20 x 30 inch PowerPoint page with 0.75 to 1 inch margins.",
    "Key results: Step 1 RMSE 21.24 MW; Step 2 48h deterministic COVE gain 20.63%; Step 3 hourly 3-scenario COVE gain 40.18%; Step 4 oracle 168h COVE gain 40.87%.",
  ].join("\n"));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT_DIR = "/Users/davidvalenta/deep-wind-model-dispatch/outputs/reu_poster_build";
const FINAL_PPTX = "/Users/davidvalenta/deep-wind-model-dispatch/outputs/Deep_Wind_REU_Research_Poster_2026_Landscape.pptx";
const REPO = "/Users/davidvalenta/deep-wind-model-dispatch";

const figures = {
  pipeline: `${OUT_DIR}/poster_fixed_pipeline.png`,
  constraints: `${REPO}/Summer 2026 REU/paper overview figures/figures/paper_fig11_constraints.png`,
  forecastRmse: `${REPO}/Summer 2026 REU/causal ridge regression/figures/paper_fig02_forecast_rmse.png`,
  rollingCove: `${REPO}/Summer 2026 REU/rolling horizon/figures/step2_causal_horizon_improvement.png`,
  rollingRevenue: `${REPO}/Summer 2026 REU/rolling horizon/figures/step2_revenue_by_horizon.png`,
  scenarioGain: `${REPO}/Summer 2026 REU/different scenarios/figures/step3_scenario_cove_improvement.png`,
  scenarioTradeoff: `${OUT_DIR}/poster_fixed_scenario_tradeoff.png`,
  oracle: `${REPO}/Summer 2026 REU/oracle upper bound/figures/step4_oracle_improvement_by_horizon.png`,
  oracleDailyHourly: `${REPO}/Summer 2026 REU/oracle upper bound/figures/step4_daily_vs_hourly_oracle_gain.png`,
  ladder: `${REPO}/Summer 2026 REU/paper overview figures/figures/paper_fig10_ladder.png`,
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

function addBox(slide, x, y, w, h, fill = "#ffffff", line = "#cbd5e1", radius = 12) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: 2 },
    borderRadius: radius,
  });
}

function addSectionTitle(slide, title, x, y, w, color = "#315f5b") {
  addText(slide, title, x, y, w, 34, { size: 27, bold: true, color });
  slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y + 39, width: w, height: 4 },
    fill: color,
    line: { style: "solid", fill: color, width: 0 },
  });
}

function addBullets(slide, items, x, y, w, h, size = 16, color = "#1f2937") {
  addText(slide, items.map((item) => `• ${item}`).join("\n"), x, y, w, h, { size, color });
}

async function addImage(slide, filePath, x, y, w, h, alt) {
  addBox(slide, x - 6, y - 6, w + 12, h + 12, "#ffffff", "#d1d5db", 10);
  slide.images.add({
    blob: await imgBlob(filePath),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left: x, top: y, width: w, height: h },
  });
}

function addMetric(slide, label, value, sub, x, y, w, color) {
  addBox(slide, x, y, w, 120, "#f8fafc", color, 12);
  addText(slide, value, x + 18, y + 13, w - 36, 36, { size: 30, bold: true, color });
  addText(slide, label, x + 18, y + 55, w - 36, 26, { size: 15, bold: true, color: "#111827" });
  addText(slide, sub, x + 18, y + 84, w - 36, 24, { size: 13, color: "#475569" });
}

function addTable(slide, x, y, w, h) {
  const rows = [
    ["Part", "What changed", "Best output"],
    ["Forecast", "Predict wind power from past values", "21.24 MW RMSE"],
    ["Rolling horizon", "One forecast path into Gurobi", "48 h: 20.63% COVE gain"],
    ["Scenarios", "Multiple possible futures", "3 scenarios: 40.18% COVE gain"],
    ["Oracle", "Perfect future information", "168 h: 40.87% COVE gain"],
  ];
  const colW = [0.23, 0.42, 0.35].map((f) => w * f);
  const rowH = h / rows.length;
  for (let r = 0; r < rows.length; r++) {
    let xx = x;
    for (let c = 0; c < 3; c++) {
      const fill = r === 0 ? "#315f5b" : r % 2 ? "#eef5ef" : "#ffffff";
      slide.shapes.add({
        geometry: "rect",
        position: { left: xx, top: y + r * rowH, width: colW[c], height: rowH },
        fill,
        line: { style: "solid", fill: "#9ca3af", width: 1 },
      });
      addText(slide, rows[r][c], xx + 10, y + r * rowH + 8, colW[c] - 20, rowH - 12, {
        size: r === 0 ? 16 : 14,
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

  const deck = Presentation.create({ slideSize: { width: 2880, height: 1920 } });
  const slide = deck.slides.add();
  slide.background.fill = "#f6f7f4";

  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 2880, height: 180 },
    fill: "#315f5b",
    line: { style: "solid", fill: "#315f5b", width: 0 },
  });
  addText(slide, "Forecast-Aware Rolling-Horizon Optimization for Hybrid Wind-Storage Dispatch", 70, 26, 2020, 58, {
    size: 42,
    bold: true,
    color: "#ffffff",
  });
  addText(slide, "David Valenta, North Carolina State University  |  Dr. Chris Qin, Washington State University", 72, 92, 1500, 32, {
    size: 22,
    color: "#dbece8",
  });
  addText(slide, "Summer 2026 REU  |  Pyron wind farm case study  |  ERCOT LMP data  |  PNNL CAES assumptions", 72, 128, 1600, 30, {
    size: 18,
    color: "#eef7f5",
  });
  addBox(slide, 2205, 28, 600, 124, "#eef5ef", "#d6e7df", 12);
  addText(slide, "Main takeaway", 2230, 45, 250, 28, { size: 20, bold: true, color: "#315f5b" });
  addText(slide, "A forecast-aware controller must tune forecast horizon, replanning frequency, storage constraints, and scenario count together.", 2230, 76, 540, 56, {
    size: 17,
    color: "#244743",
  });

  const margin = 62;
  const gutter = 28;
  const top = 215;
  const colW = (2880 - 2 * margin - 3 * gutter) / 4;
  const xs = [margin, margin + colW + gutter, margin + 2 * (colW + gutter), margin + 3 * (colW + gutter)];

  addBox(slide, xs[0], top, colW, 310, "#ffffff", "#b8d7d2");
  addSectionTitle(slide, "1. Problem", xs[0] + 22, top + 18, colW - 44, "#315f5b");
  addBullets(slide, [
    "Wind and electricity price change every hour.",
    "A hybrid wind farm can sell wind now or store energy for later.",
    "The challenge is dispatching storage before the future is known.",
    "The main comparison is the 100 MW constant-output CAES benchmark.",
    "Wind-only is kept as secondary reference information.",
  ], xs[0] + 28, top + 78, colW - 56, 150, 17);
  addText(slide, "Why storage helps", xs[0] + 28, top + 238, colW - 56, 24, { size: 16, bold: true, color: "#315f5b" });
  addText(slide, "If wind arrives during a low-price hour, storage can hold part of that energy and release it when the price is higher. The dispatch problem is deciding when that trade is worth it while keeping the battery feasible.", xs[0] + 28, top + 264, colW - 56, 42, {
    size: 13,
    color: "#334155",
  });

  addBox(slide, xs[0], top + 335, colW, 335, "#ffffff", "#cbd5d8");
  addSectionTitle(slide, "2. Data and Storage", xs[0] + 22, top + 353, colW - 44, "#486a86");
  addBullets(slide, [
    "Pyron wind farm hourly data, 1980-2023.",
    "Forecast trained before 2014; tested on unseen 2014-2023.",
    "ERCOT locational marginal price is used for value.",
    "CAES: 100 MW, 10 h, 1000 MWh.",
    "SoC: 200-1000 MWh, starting at 600 MWh.",
    "RTE: 55%, no grid charging, 249 MW grid cap.",
  ], xs[0] + 28, top + 413, colW - 56, 162, 16);
  addText(slide, "What the model sees", xs[0] + 28, top + 588, colW - 56, 24, { size: 16, bold: true, color: "#486a86" });
  addText(slide, "The controller does not receive the true future in deployable cases. It receives forecasted wind generation and forecasted price, then the realized data is used later for scoring.", xs[0] + 28, top + 614, colW - 56, 42, {
    size: 13,
    color: "#334155",
  });

  await addImage(slide, figures.forecastRmse, xs[0] + 10, top + 705, colW - 20, 250, "Forecast model RMSE comparison");
  addText(slide, "Forecast result: causal lag/ridge was the best power forecast, with 21.24 MW RMSE.", xs[0] + 20, top + 963, colW - 40, 46, {
    size: 14,
    color: "#334155",
  });

  await addImage(slide, figures.pipeline, xs[1] + 10, top, colW - 20, 200, "Pipeline diagram");
  addText(slide, "The pipeline predicts wind/price, sends those forecasts to Gurobi, executes dispatch, then scores revenue and COVE.", xs[1] + 20, top + 208, colW - 40, 42, {
    size: 15,
    color: "#334155",
  });
  addText(slide, "The important idea is separation: forecasts are guesses, Gurobi is the planner, and realized operation is the final truth used for revenue and COVE.", xs[1] + 20, top + 252, colW - 40, 34, {
    size: 13,
    color: "#5f5472",
  });

  addBox(slide, xs[1], top + 292, colW, 368, "#ffffff", "#cfc7dc");
  addSectionTitle(slide, "3. MILP Dispatch", xs[1] + 22, top + 310, colW - 44, "#5f5472");
  addBullets(slide, [
    "Gurobi chooses direct wind, charge, discharge, SoC, and curtailment.",
    "Charging must come from wind, not the grid.",
    "The battery cannot charge and discharge beyond its physical limits.",
    "Revenue is delivered power times realized price.",
    "COVE is lower when energy is delivered at higher value.",
  ], xs[1] + 28, top + 370, colW - 56, 196, 16);
  await addImage(slide, figures.constraints, xs[1] + 12, top + 565, colW - 24, 180, "Storage constraints table");

  await addImage(slide, figures.ladder, xs[1] + 10, top + 785, colW - 20, 220, "Research ladder");
  addText(slide, "The ladder is not just decoration: each step adds one layer of information or control. Forecasting answers what may happen; rolling horizon decides how far to plan; scenarios add uncertainty; oracle shows the ceiling.", xs[1] + 20, top + 1010, colW - 40, 52, {
    size: 13,
    color: "#334155",
  });

  addTable(slide, xs[2], top, colW, 270);
  await addImage(slide, figures.rollingCove, xs[2] + 10, top + 310, colW - 20, 245, "Rolling horizon COVE gain");
  addText(slide, "Deterministic rolling horizon: 48 hours gave the best COVE gain because it looked far enough ahead without trusting a weak long forecast too much.", xs[2] + 20, top + 565, colW - 40, 62, {
    size: 14,
    color: "#334155",
  });
  await addImage(slide, figures.rollingRevenue, xs[2] + 10, top + 660, colW - 20, 235, "Revenue by horizon");
  addText(slide, "Longer horizons did not automatically improve realistic dispatch. Planning value and forecast error have to balance.", xs[2] + 20, top + 905, colW - 40, 50, {
    size: 14,
    color: "#334155",
  });
  addBox(slide, xs[2], top + 975, colW, 88, "#ffffff", "#d6d3d1");
  addText(slide, "How to read these results", xs[2] + 22, top + 990, colW - 44, 24, { size: 16, bold: true, color: "#4b5563" });
  addText(slide, "A higher COVE gain is better because it means the same storage system delivered energy at higher value compared with the 100 MW benchmark.", xs[2] + 22, top + 1018, colW - 44, 34, {
    size: 13,
    color: "#374151",
  });

  addBox(slide, xs[3], top, colW, 145, "#ffffff", "#e5c7aa");
  addSectionTitle(slide, "4. Results", xs[3] + 22, top + 18, colW - 44, "#8a5134");
  addText(slide, "Primary benchmark: 100 MW constant-output CAES. Wind-only remains secondary context.", xs[3] + 28, top + 76, colW - 56, 45, {
    size: 15,
    color: "#1f2937",
  });
  const mw = (colW - 18) / 2;
  addMetric(slide, "Forecast RMSE", "21.24 MW", "causal lag/ridge", xs[3], top + 175, mw, "#3f6575");
  addMetric(slide, "Deterministic", "20.63%", "48 h COVE gain", xs[3] + mw + 18, top + 175, mw, "#5f5472");
  addMetric(slide, "Scenario", "40.18%", "3 scenarios, hourly replan", xs[3], top + 315, mw, "#557a5a");
  addMetric(slide, "Oracle", "40.87%", "168 h perfect future", xs[3] + mw + 18, top + 315, mw, "#8a5134");

  await addImage(slide, figures.scenarioGain, xs[3] + 10, top + 475, colW - 20, 245, "Scenario COVE improvement");
  addText(slide, "Scenario result: 3 scenarios performed best. More scenarios became more cautious and did not add enough value.", xs[3] + 20, top + 730, colW - 40, 50, {
    size: 14,
    color: "#334155",
  });
  await addImage(slide, figures.scenarioTradeoff, xs[3] + 10, top + 800, colW - 20, 200, "Scenario revenue and COVE tradeoff");
  addText(slide, "Revenue and COVE move together here: the strongest scenario case both earns more and lowers COVE against the benchmark.", xs[3] + 20, top + 1010, colW - 40, 40, {
    size: 13,
    color: "#334155",
  });

  const bottomY = 1325;
  addBox(slide, margin, bottomY, 1360, 405, "#ffffff", "#bdd8c1");
  addSectionTitle(slide, "5. Main Conclusion", margin + 26, bottomY + 24, 1280, "#557a5a");
  addBullets(slide, [
    "The strongest realistic result came from the scenario-based controller because it planned under multiple possible futures and corrected decisions quickly.",
    "The deterministic 48 h case is useful because it shows the best one-forecast version of the method.",
    "The oracle is not realistic, but it shows the upper bound if future wind and price were known perfectly.",
    "The core claim is not just that Gurobi optimizes dispatch. The key result is that forecast design and dispatch design have to be tuned together.",
    "This matters for real wind farms because storage decisions are only useful when they respect uncertainty and physical constraints at the same time.",
  ], margin + 32, bottomY + 90, 1280, 245, 17);
  addBox(slide, margin + 32, bottomY + 282, 392, 72, "#eef5ef", "#bdd8c1");
  addText(slide, "Best realistic method", margin + 52, bottomY + 296, 340, 22, { size: 15, bold: true, color: "#335a39" });
  addText(slide, "3 scenarios with hourly replanning", margin + 52, bottomY + 322, 340, 24, { size: 14, color: "#334155" });
  addBox(slide, margin + 456, bottomY + 282, 392, 72, "#f8fafc", "#cbd5d8");
  addText(slide, "Why it worked", margin + 476, bottomY + 296, 340, 22, { size: 15, bold: true, color: "#486a86" });
  addText(slide, "It reacted faster to forecast mistakes.", margin + 476, bottomY + 322, 340, 24, { size: 14, color: "#334155" });
  addBox(slide, margin + 880, bottomY + 282, 392, 72, "#f8fafc", "#d6d3d1");
  addText(slide, "Oracle meaning", margin + 900, bottomY + 296, 340, 22, { size: 15, bold: true, color: "#4b5563" });
  addText(slide, "It is the perfect-future ceiling.", margin + 900, bottomY + 322, 340, 24, { size: 14, color: "#334155" });
  addText(slide, "Best result: 3-scenario forecast-aware rolling-horizon dispatch improved COVE by 40.18% vs the 100 MW benchmark.", margin + 32, bottomY + 362, 1280, 30, {
    size: 19,
    bold: true,
    color: "#335a39",
  });

  addBox(slide, margin + 1395, bottomY, 1360, 405, "#1f2933", "#1f2933");
  addText(slide, "Definitions and Acknowledgements", margin + 1425, bottomY + 24, 720, 34, { size: 27, bold: true, color: "#ffffff" });
  addBullets(slide, [
    "100 MW benchmark: rule-based storage case that tries to deliver 100 MW every hour.",
    "Rolling horizon: solve the future, execute the near-term action, update SoC, then solve again.",
    "Scenario dispatch: solve several possible futures instead of one forecast.",
    "Oracle: perfect future information, used only as a ceiling.",
    "COVE: cost divided by valued delivered energy; lower is better.",
    "All reported runs use chronological SoC and checked storage/grid constraints.",
  ], margin + 1425, bottomY + 76, 760, 220, 16, "#e2e8f0");

  addBox(slide, margin + 1425, bottomY + 302, 230, 64, "#263542", "#475569");
  addText(slide, "Best forecast", margin + 1442, bottomY + 314, 196, 20, { size: 13, bold: true, color: "#ffffff" });
  addText(slide, "21.24 MW RMSE", margin + 1442, bottomY + 338, 196, 20, { size: 13, color: "#cde7e1" });
  addBox(slide, margin + 1672, bottomY + 302, 230, 64, "#263542", "#475569");
  addText(slide, "Best realistic", margin + 1689, bottomY + 314, 196, 20, { size: 13, bold: true, color: "#ffffff" });
  addText(slide, "3 scenarios", margin + 1689, bottomY + 338, 196, 20, { size: 13, color: "#cde7e1" });
  addBox(slide, margin + 1919, bottomY + 302, 230, 64, "#263542", "#475569");
  addText(slide, "Upper bound", margin + 1936, bottomY + 314, 196, 20, { size: 13, bold: true, color: "#ffffff" });
  addText(slide, "40.87% COVE", margin + 1936, bottomY + 338, 196, 20, { size: 13, color: "#cde7e1" });

  addText(slide, "Thank you to Dr. Chris Qin, Nora Hosseiniimeni, Zach Lawrence, Jessica Yao, and the WSU Summer Research Program. Data and assumptions draw from the Pyron wind-storage dataset, ERCOT LMP records, and PNNL CAES storage references.", margin + 2220, bottomY + 76, 500, 170, {
    size: 16,
    color: "#e2e8f0",
  });
  addText(slide, "What I tested", margin + 2220, bottomY + 230, 460, 24, { size: 17, bold: true, color: "#ffffff" });
  addText(slide, "Forecast models, deterministic horizons, scenario counts, oracle ceiling, and constraint checks.", margin + 2220, bottomY + 258, 500, 44, { size: 14, color: "#e2e8f0" });
  addText(slide, "Contact: dvalent2@ncsu.edu", margin + 2220, bottomY + 320, 460, 28, { size: 18, bold: true, color: "#b7d8d2" });
  addText(slide, "Poster size: 30 in x 20 in", margin + 2220, bottomY + 352, 460, 24, { size: 14, color: "#cbd5e1" });

  slide.shapes.add({
    geometry: "rect",
    position: { left: margin, top: 1770, width: 2755, height: 4 },
    fill: "#7aa7a0",
    line: { style: "solid", fill: "#7aa7a0", width: 0 },
  });
  addText(slide, "Primary metrics compare against the 100 MW constant-output CAES benchmark; wind-only is retained only as a secondary reference.", margin, 1787, 2755, 28, {
    size: 15,
    color: "#475569",
    align: "center",
  });

  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(FINAL_PPTX);
  await writeBlob(`${OUT_DIR}/poster_landscape_preview.png`, await deck.export({ slide, format: "png", scale: 1 }));
  await writeBlob(`${OUT_DIR}/poster_landscape_preview_2x.png`, await deck.export({ slide, format: "png", scale: 2 }));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

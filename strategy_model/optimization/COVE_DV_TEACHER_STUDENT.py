"""COVE-DV neural teacher-student experiment.

COVE-DV is the neural student model.  The teacher labels come from the MILP /
Gurobi dispatch runs.  This experiment is kept here because the original COVE
and dispatch work lives under `strategy_model/optimization`.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPT = ROOT / "strategy_model" / "optimization"

FILES = {
    "teacher_label_builder": OPT / "milp_teacher_dispatch.py",
    "chronological_student_training": OPT / "train_cove_dv_chronological.py",
    "older_student_training": OPT / "train_cove_dv.py",
    "key_results": OPT / "cove_dv_results" / "cove_dv_key_results.csv",
    "nora_chronological_results": OPT / "cove_dv_nora_chronological_key_results.csv",
    "chronological_figures": OPT / "cove_dv_nora_chronological_figures",
}


def main() -> None:
    print("COVE-DV TEACHER-STUDENT MAP")
    for name, path in FILES.items():
        print(f"{name}: {path}")
    print()
    print("Meaning:")
    print("- Teacher: Gurobi/MILP creates storage decisions under constraints.")
    print("- Student: neural network learns to imitate those decisions.")
    print("- Status: useful experiment, but the canonical paper baseline should be the deterministic/scenario rolling-horizon MILP.")


if __name__ == "__main__":
    main()

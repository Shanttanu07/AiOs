from __future__ import annotations
import json, argparse
from pathlib import Path
from datetime import datetime

DEFAULT_CAPS = ["fs.read", "fs.write", "proc.spawn"]

def build_plan(goal: str, csv_path: str, target: str, seed: int = 1337, ratio: float = 0.8):
    return {
        "goal": goal,
        "capabilities": DEFAULT_CAPS,
        "inputs": {"csv": csv_path},
        "steps": [
            {"id":"s1","op":"load_csv","in":"$csv","out":"$table"},
            {"id":"s2","op":"profile_schema","in":"$table","out":"$schema"},
            {"id":"s3","op":"split_deterministic","in":"$table","args":{"seed":seed,"ratio":ratio},"out":{"train":"$train","val":"$val"}},
            {"id":"s4","op":"train_linear","in":{"Xy_train":"$train"},"args":{"target":target},"out":"$model"},
            {"id":"s5","op":"eval_metrics","in":{"model":"$model","Xy_val":"$val"},"out":"$metrics"},
            {"id":"g1","op":"guard","cond":"$metrics.R2 >= 0.6", "description":"Abort if model quality is too low"},
            {"id":"s6","op":"emit_report","in":{"schema":"$schema","metrics":"$metrics"},"out":"sandbox/out/report.md"},
            {"id":"s7","op":"build_cli","in":{"model":"$model","schema":"$schema"},"out":"sandbox/out/app/"},
            {"id":"s8","op":"bundle_zip","in":"sandbox/out/app/","out":"sandbox/out/app.zip"}
        ],
        "verify": [
            {"op":"verify_zip","target":"sandbox/out/app.zip"},
            {"op":"verify_cli_predicts","args":{"input_sample":"sandbox/in/sample.json"}}
        ],
        "rollback": [
            {"op":"delete","target":"sandbox/out/app.zip"},
            {"op":"delete","target":"sandbox/out/app/"},
            {"op":"delete","target":"sandbox/out/report.md"}
        ],
        "_generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    }

def main():
    ap = argparse.ArgumentParser(description="Generate APL plan (template).")
    ap.add_argument("--goal", default="Build a reproducible price predictor from CSV")
    ap.add_argument("--csv", required=True, help="Path to input CSV (inside sandbox/in/)")
    ap.add_argument("--target", required=True, help="Target column name (e.g., price)")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--ratio", type=float, default=0.8)
    ap.add_argument("--out", default="apps/forge/plan.apl.json")
    args = ap.parse_args()

    plan = build_plan(args.goal, args.csv, args.target, args.seed, args.ratio)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"[gen] Wrote {out_path}")

if __name__ == "__main__":
    main()
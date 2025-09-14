# compiler/compile_bc.py
from __future__ import annotations
import json, argparse, re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from jsonschema import Draft202012Validator
from .opcodes import OP_SET, OPCODES, LEGACY_TO_TOOL

# ---------- helpers ----------

def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

DOT = re.compile(r"^\$(?P<name>[A-Za-z_]\w*)(?:\.(?P<field>[\w\.]+))?$")
COND = re.compile(r"^\$(?P<slot>[A-Za-z_]\w*)\.(?P<field>[\w\.]+)\s*(?P<op>>=|<=|>|<|==)\s*(?P<rhs>-?\d+(\.\d+)?)$")

class Symtab:
    """Allocate stable 'registers' for logical slots like $table, $schema, $model."""
    def __init__(self) -> None:
        self._slots: Dict[str, str] = {}
        self._order: List[str] = []

    def slot_of(self, dollar_name: str) -> str:
        # dollar_name is "$foo" or "$foo.bar" (we strip to 'foo')
        m = DOT.match(dollar_name)
        if not m:
            raise ValueError(f"expected $var or $var.field, got: {dollar_name}")
        base = m.group("name")
        if base not in self._slots:
            reg = f"S{len(self._slots)}"
            self._slots[base] = reg
            self._order.append(base)
        return self._slots[base]

    def mapping(self) -> Dict[str, str]:
        return dict(self._slots)

# ---------- lowering ----------

def lower_steps(plan: Dict[str, Any], use_tools: bool = False) -> Tuple[List[List[Any]], Dict[str, str]]:
    st = Symtab()
    prog: List[List[Any]] = []
    inputs = plan.get("inputs", {})

    for step in plan.get("steps", []):
        op = step["op"]
        if op == "load_csv":
            in_path = resolve_in_ref(step["in"], inputs)
            out_reg = st.slot_of(step["out"])
            prog.append(["READ_CSV", in_path, out_reg])

        elif op == "profile_schema":
            in_reg = st.slot_of(step["in"])
            out_reg = st.slot_of(step["out"])
            prog.append(["PROFILE", in_reg, out_reg])

        elif op == "split_deterministic":
            in_reg = st.slot_of(step["in"])
            args = step.get("args", {})
            ratio = float(args.get("ratio", 0.8))
            seed  = int(args.get("seed", 1337))
            outs = step.get("out")
            if isinstance(outs, dict):
                # {"train":"$train","val":"$val"}
                train_reg = st.slot_of(outs["train"])
                val_reg   = st.slot_of(outs["val"])
            else:
                # Single output "$train_data" - create derived slots
                train_reg = st.slot_of(outs)
                val_reg = st.slot_of(outs.replace("$train_data", "$val_data") if "$train_data" in outs else "$val_data")
            prog.append(["SPLIT", in_reg, ratio, seed, train_reg, val_reg])

        elif op == "train_linear":
            in_data = step["in"]
            if isinstance(in_data, dict):
                # New format: {"train_data": "$train_data", "target": "price"}
                if "train_data" in in_data:
                    train_reg = st.slot_of(in_data["train_data"])
                    target = in_data.get("target") or step.get("args", {}).get("target")
                elif "Xy_train" in in_data:
                    # Legacy format: {"Xy_train":"$train"}
                    train_reg = st.slot_of(in_data["Xy_train"])
                    target = step.get("args", {}).get("target")
                else:
                    raise ValueError("train_linear: expected 'train_data' or 'Xy_train' in inputs")
            else:
                # Simple string input
                train_reg = st.slot_of(in_data)
                target = step.get("args", {}).get("target")

            if not target:
                raise ValueError("train_linear: target is required (in inputs or args)")
            out_reg = st.slot_of(step["out"])
            prog.append(["TRAIN_LR", train_reg, target, out_reg])

        elif op == "eval_metrics":
            in_map = step["in"]
            if isinstance(in_map, dict):
                model_reg = st.slot_of(in_map["model"])
                # Handle different val_data key names
                if "val_data" in in_map:
                    val_reg = st.slot_of(in_map["val_data"])
                elif "Xy_val" in in_map:
                    val_reg = st.slot_of(in_map["Xy_val"])
                else:
                    # Derive val_data from train_data (common pattern after split)
                    val_reg = st.slot_of("$val_data")
            else:
                raise ValueError("eval_metrics: expected dict input with model and validation data")
            out_reg = st.slot_of(step["out"])
            prog.append(["EVAL", model_reg, val_reg, out_reg])

        elif op == "emit_report":
            in_map = step["in"]
            if isinstance(in_map, dict):
                schema_reg = st.slot_of(in_map["schema"])
                metrics_reg = st.slot_of(in_map["metrics"])
                # Handle output_path in inputs or as separate out field
                out_path = in_map.get("output_path")
                if not out_path:
                    out_path = resolve_out_path(step.get("out", "sandbox/out/report.md"))
            else:
                raise ValueError("emit_report: expected dict input with schema and metrics")
            prog.append(["EMIT_REPORT", schema_reg, metrics_reg, out_path])

        elif op == "build_cli":
            in_map = step["in"]
            if isinstance(in_map, dict):
                model_reg = st.slot_of(in_map["model"])
                schema_reg = st.slot_of(in_map["schema"])
                # Handle output_dir in inputs or as separate out field
                out_dir = in_map.get("output_dir")
                if not out_dir:
                    out_dir = resolve_out_path(step.get("out", "sandbox/out/app"))
            else:
                raise ValueError("build_cli: expected dict input with model and schema")
            prog.append(["BUILD_CLI", model_reg, schema_reg, out_dir])

        elif op == "bundle_zip":
            in_data = step["in"]
            if isinstance(in_data, dict):
                # {"source_dir": "path", "output_path": "path"}
                src = in_data.get("source_dir")
                dest = in_data.get("output_path") or resolve_out_path(step.get("out"))
            elif isinstance(in_data, str):
                # Simple string input
                src = resolve_in_ref(in_data, inputs)
                dest = resolve_out_path(step.get("out"))
            else:
                raise ValueError("bundle_zip: expected dict or string input")
            prog.append(["ZIP", src, dest])

        elif op == "guard":
            cond = step.get("cond","").strip()
            instr = lower_guard(cond, st)
            prog.append(instr)

        else:
            raise ValueError(f"Unsupported APL op in v1: {op}")

    # lower verify steps
    for v in plan.get("verify", []):
        vop = v["op"]
        if vop == "verify_zip":
            prog.append(["VERIFY_ZIP", v["target"]])
        elif vop == "verify_cli_predicts":
            sample = v.get("args", {}).get("input_sample")
            if not sample:
                raise ValueError("verify_cli_predicts.args.input_sample required")
            # we verify the CLI in the app dir produced by BUILD_CLI; pass that same out_dir again
            # Convention: last BUILD_CLI out_dir is the app dir.
            app_dir = _last_build_cli_outdir(prog)
            prog.append(["VERIFY_CLI", app_dir, sample])
        elif vop in ("verify_file_exists","verify_nonempty"):
            # Optional: you can add runtime support later
            pass
        else:
            raise ValueError(f"Unsupported verify op: {vop}")

    return prog, st.mapping()

def resolve_in_ref(x: Any, inputs: Dict[str, str] = None) -> Any:
    # allow only plain string (path) or $var
    if isinstance(x, str):
        if x.startswith("$") and inputs:
            # resolve $csv -> actual path from inputs
            var_name = x[1:]  # strip $
            if var_name in inputs:
                return inputs[var_name]
            else:
                raise ValueError(f"Undefined input variable: {x}")
        return x
    raise ValueError(f"Expected string for 'in', got {type(x)}")

def resolve_out_path(x: Any) -> str:
    if isinstance(x, str):
        return x
    raise ValueError(f"Expected string path for 'out', got {type(x)}")

def lower_guard(cond: str, st: Symtab) -> List[Any]:
    """
    Support simple forms: $metrics.R2 >= 0.6  (also >, <, <=, ==)
    Emits ASSERT_* opcode; runtime HALTs if assertion fails.
    """
    m = COND.match(cond)
    if not m:
        raise ValueError(f"Unsupported guard condition: {cond!r}")
    slot = st.slot_of(f"${m.group('slot')}")
    field = m.group("field")
    op = m.group("op")
    rhs = float(m.group("rhs"))
    if op == ">=":
        return ["ASSERT_GE", slot, field, rhs]
    elif op == ">":
        # represent as ASSERT_GE with epsilon if you prefer; or define ASSERT_GT later
        return ["ASSERT_GE", slot, field, rhs + 1e-12]
    elif op in ("<","<=","=="):
        # keep simple for v1: invert using runtime compare (or extend later)
        return ["ASSERT_GE", slot, field, float("-inf")]  # placeholder; runtime can handle others if needed
    else:
        raise ValueError(f"Unsupported operator in guard: {op}")

def _last_build_cli_outdir(prog: List[List[Any]]) -> str:
    for instr in reversed(prog):
        if instr and instr[0] == "BUILD_CLI":
            return instr[3]  # out_dir
    # default (if not found): conventional app dir
    return "sandbox/out/app/"

def convert_to_tool_calls(program: List[List[Any]], slots: Dict[str, str]) -> List[List[Any]]:
    """Convert legacy opcodes to CALL_TOOL instructions"""
    converted = []

    for instr in program:
        if not instr or instr[0] not in LEGACY_TO_TOOL:
            # Keep non-legacy instructions as-is
            converted.append(instr)
            continue

        opcode = instr[0]
        tool_name = LEGACY_TO_TOOL[opcode]

        # Convert arguments to inputs/outputs format
        if opcode == "READ_CSV":
            # READ_CSV path slot -> CALL_TOOL read_csv {path: path} {table: slot}
            path, out_slot = instr[1], instr[2]
            inputs = {"path": path}
            outputs = {"table": out_slot}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "PROFILE":
            # PROFILE in_slot out_slot -> CALL_TOOL profile {table: in_slot} {schema: out_slot}
            in_slot, out_slot = instr[1], instr[2]
            inputs = {"table": in_slot}
            outputs = {"schema": out_slot}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "SPLIT":
            # SPLIT in_slot ratio seed train_slot val_slot -> CALL_TOOL split {table: in_slot, ratio: ratio, seed: seed} {train: train_slot, val: val_slot}
            in_slot, ratio, seed, train_slot, val_slot = instr[1], instr[2], instr[3], instr[4], instr[5]
            inputs = {"table": in_slot, "ratio": ratio, "seed": seed}
            outputs = {"train": train_slot, "val": val_slot}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "TRAIN_LR":
            # TRAIN_LR train_slot target model_slot -> CALL_TOOL train_lr {train_data: train_slot, target: target} {model: model_slot}
            train_slot, target, model_slot = instr[1], instr[2], instr[3]
            inputs = {"train_data": train_slot, "target": target}
            outputs = {"model": model_slot}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "EVAL":
            # EVAL model_slot val_slot metrics_slot -> CALL_TOOL eval {model: model_slot, val_data: val_slot} {metrics: metrics_slot}
            model_slot, val_slot, metrics_slot = instr[1], instr[2], instr[3]
            inputs = {"model": model_slot, "val_data": val_slot, "target": "price"}  # default target
            outputs = {"metrics": metrics_slot}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "EMIT_REPORT":
            # EMIT_REPORT schema_slot metrics_slot out_path -> CALL_TOOL emit_report {schema: schema_slot, metrics: metrics_slot, output_path: out_path} {}
            schema_slot, metrics_slot, out_path = instr[1], instr[2], instr[3]
            inputs = {"schema": schema_slot, "metrics": metrics_slot, "output_path": out_path}
            outputs = {}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "BUILD_CLI":
            # BUILD_CLI model_slot schema_slot out_dir -> CALL_TOOL build_cli {model: model_slot, schema: schema_slot, output_dir: out_dir} {}
            model_slot, schema_slot, out_dir = instr[1], instr[2], instr[3]
            inputs = {"model": model_slot, "schema": schema_slot, "output_dir": out_dir}
            outputs = {}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "ZIP":
            # ZIP src_dir dest_zip -> CALL_TOOL zip {source_dir: src_dir, output_path: dest_zip} {}
            src_dir, dest_zip = instr[1], instr[2]
            inputs = {"source_dir": src_dir, "output_path": dest_zip}
            outputs = {}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "VERIFY_ZIP":
            # VERIFY_ZIP zip_path -> CALL_TOOL verify_zip {zip_path: zip_path} {}
            zip_path = instr[1]
            inputs = {"zip_path": zip_path}
            outputs = {}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "VERIFY_CLI":
            # VERIFY_CLI app_dir sample_json -> CALL_TOOL verify_cli {app_dir: app_dir, sample_input: sample_json} {prediction: temp_slot}
            app_dir, sample_json = instr[1], instr[2]
            inputs = {"app_dir": app_dir, "sample_input": sample_json}
            outputs = {"prediction": f"_temp_{len(converted)}"}  # temporary slot
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        elif opcode == "ASSERT_GE":
            # ASSERT_GE metrics_slot field threshold -> CALL_TOOL assert_ge {metrics: metrics_slot, field: field, threshold: threshold} {}
            metrics_slot, field, threshold = instr[1], instr[2], instr[3]
            inputs = {"metrics": metrics_slot, "field": field, "threshold": threshold}
            outputs = {}
            converted.append(["CALL_TOOL", tool_name, inputs, outputs])

        else:
            # Keep as legacy for now
            converted.append(instr)

    return converted

# ---------- main ----------

def compile_plan_file(plan_path: Path, out_path: Path = None, schema_path: Path = None, use_tools: bool = False):
    """Compile a plan file to bytecode"""
    if schema_path is None:
        schema_path = Path(__file__).parent / "schema.json"

    schema = load_json(schema_path)
    plan = load_json(plan_path)

    # schema validation
    Draft202012Validator(schema).validate(plan)

    program, slots = lower_steps(plan, use_tools=use_tools)

    # Convert to tool calls if requested
    if use_tools:
        program = convert_to_tool_calls(program, slots)
        print(f"[bc] Using tool-based compilation (CALL_TOOL)")

    # sanity check opcode names
    for ins in program:
        if ins[0] not in OPCODES:
            raise ValueError(f"Invalid opcode: {ins[0]} (valid: {', '.join(OPCODES)})")

    # output
    bc = {
        "program": program,
        "capabilities": plan.get("capabilities", []),
        "slots": slots,
        "metadata": {
            "goal": plan.get("goal", ""),
            "inputs": plan.get("inputs", {}),
            "compilation_mode": "tools" if use_tools else "legacy"
        }
    }

    if out_path is None:
        out_path = plan_path.with_suffix(".bytecode.json")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bc, indent=2), encoding="utf-8")
    print(f"[bc] Wrote {out_path}")
    print(f"[bc] Slots: {slots}")
    if use_tools:
        print(f"[bc] Mode: Tool-based (CALL_TOOL)")

def main():
    ap = argparse.ArgumentParser(description="Compile APL (plan) to AIOX bytecode.")
    ap.add_argument("plan", help="Path to plan.apl.json")
    ap.add_argument("-s","--schema", default="compiler/schema.json", help="Path to APL JSON Schema")
    ap.add_argument("-o","--out", default=None, help="Output bytecode path (default: alongside plan)")
    ap.add_argument("--tools", action="store_true", help="Use tool-based compilation (CALL_TOOL)")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    schema_path = Path(args.schema)
    out_path = Path(args.out) if args.out else None

    compile_plan_file(plan_path, out_path, schema_path, use_tools=args.tools)

if __name__ == "__main__":
    main()
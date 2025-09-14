#!/usr/bin/env python3
"""AI-OS Command Line Interface"""

import argparse
import sys
from pathlib import Path


def cmd_run(args: argparse.Namespace) -> int:
    from .kernel.runtime import run_bytecode
    root = Path(args.root).resolve()
    sbx = root / "sandbox"
    bytecode_path = Path(args.bytecode) if args.bytecode else (root / "apps" / "forge" / "bytecode.json")
    if not bytecode_path.exists():
        print(f"[run] bytecode not found: {bytecode_path}", file=sys.stderr)
        return 2
    try:
        run_bytecode(bytecode_path, sbx, dry_run=args.dry_run, auto_yes=args.yes)
    except Exception as e:
        print(f"[run] ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_compile(args: argparse.Namespace) -> int:
    """Compile APL plan to bytecode"""
    from .compiler.compile_bc import main as compile_main
    import sys
    # Save original argv and replace with compile arguments
    orig_argv = sys.argv
    try:
        sys.argv = ["compile_bc.py"]
        if hasattr(args, 'plan') and args.plan:
            sys.argv.append(args.plan)
        if hasattr(args, 'schema') and args.schema:
            sys.argv.extend(["-s", args.schema])
        if hasattr(args, 'out') and args.out:
            sys.argv.extend(["-o", args.out])
        if hasattr(args, 'tools') and args.tools:
            sys.argv.append("--tools")
        compile_main()
        return 0
    except SystemExit as e:
        return e.code
    except Exception as e:
        print(f"[compile] ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        sys.argv = orig_argv


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate APL plan against schema"""
    from .compiler.validate_apl import main as validate_main
    import sys
    # Save original argv and replace with validate arguments
    orig_argv = sys.argv
    try:
        sys.argv = ["validate_apl.py"]
        if hasattr(args, 'schema') and args.schema:
            sys.argv.append(args.schema)
        if hasattr(args, 'plan') and args.plan:
            sys.argv.append(args.plan)
        validate_main()
        return 0
    except SystemExit as e:
        return e.code
    except Exception as e:
        print(f"[validate] ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        sys.argv = orig_argv


def cmd_pack(args: argparse.Namespace) -> int:
    from .kernel.packaging import make_aiox
    root = Path(args.root).resolve()
    plan = Path(args.plan) if args.plan else (root / "apps" / "forge" / "plan.apl.json")
    bc   = Path(args.bytecode) if args.bytecode else (root / "apps" / "forge" / "bytecode.json")
    out  = Path(args.out) if args.out else (root / "sandbox" / "packages" / "app.aiox")
    try:
        make_aiox(plan, bc, root / "sandbox", out, name=args.name)
        print(f"[pack] Wrote {out}")
        return 0
    except Exception as e:
        print(f"[pack] ERROR: {e}", file=sys.stderr)
        return 1

def cmd_replay(args: argparse.Namespace) -> int:
    from .kernel.replay import replay_aiox
    root = Path(args.root).resolve()
    pkg  = Path(args.package)
    ok, diffs = replay_aiox(pkg, root / "sandbox", auto_yes=True, clean_out=True)
    if ok:
        print("[replay] Deterministic replay PASSED.")
        return 0
    else:
        print("[replay] Deterministic replay FAILED. Diffs:")
        for k, kind, old, new in diffs:
            print(f" - {k}: {kind} (expected {old}, got {new})")
        return 2

def cmd_undo(args: argparse.Namespace) -> int:
    from .kernel.undo import undo_last_run
    root = Path(args.root).resolve()
    n = undo_last_run(root / "sandbox")
    return 0 if n >= 0 else 1

def cmd_ui(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    from .ui.tui import main as tui_main
    tui_main(root)
    return 0

def cmd_prompt(args: argparse.Namespace) -> int:
    """One-liner: prompt -> plan + bytecode"""
    import sys, json
    root = Path(args.root).resolve()
    plan = root / "apps" / "forge" / "plan.apl.json"
    bc   = root / "apps" / "forge" / "bytecode.json"

    try:
        print(f"[prompt] Generating intelligent plan from goal...")

        # Initialize tool registry and planner
        from .kernel.tools import ToolRegistry
        from .planner.core import PlanGenerator
        from .planner.apl_converter import APLConverter

        tools_root = root / "tools"
        registry = ToolRegistry(tools_root)
        registry.discover_tools()

        planner = PlanGenerator(registry, root / "sandbox")
        converter = APLConverter()

        # Generate execution plan from natural language goal
        execution_plan = planner.generate_plan(
            goal=args.goal,
            input_csv=args.csv,
            target_column=args.target,
            seed=getattr(args, 'seed', 1337),
            ratio=getattr(args, 'ratio', 0.8)
        )

        # Convert to APL format
        plan_data = converter.convert_to_apl(execution_plan)

        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

        print(f"[prompt] Plan generated using template: {execution_plan.metadata.get('template', 'unknown')}")
        print(f"[prompt] Complexity: {execution_plan.metadata.get('complexity', 'unknown')}")
        print(f"[prompt] Steps: {len(execution_plan.steps)}")

        print(f"[prompt] Compiling to bytecode...")
        # Import and call compile_bc directly
        from .compiler.compile_bc import compile_plan_file

        compile_plan_file(plan, bc)

        print(f"[prompt] Ready! Plan: {plan.relative_to(root)}")
        print(f"[prompt] Ready! Bytecode: {bc.relative_to(root)}")
        print(f"[prompt] Next: aiox ui (then d/e/p/r/u)")
        return 0

    except Exception as e:
        print(f"[prompt] ERROR: {e}")
        return 1

def cmd_gen_plan(args: argparse.Namespace) -> int:
    """Generate APL plan from parameters"""
    import json
    from pathlib import Path

    try:
        # Initialize tool registry and planner
        from .kernel.tools import ToolRegistry
        from .planner.core import PlanGenerator
        from .planner.apl_converter import APLConverter

        root = Path(args.root if hasattr(args, 'root') else ".").resolve()
        tools_root = root / "tools"
        registry = ToolRegistry(tools_root)
        registry.discover_tools()

        planner = PlanGenerator(registry, root / "sandbox")
        converter = APLConverter()

        # Generate execution plan from natural language goal
        execution_plan = planner.generate_plan(
            goal=args.goal,
            input_csv=args.csv,
            target_column=args.target,
            seed=args.seed,
            ratio=args.ratio
        )

        # Convert to APL format
        plan_data = converter.convert_to_apl(execution_plan)

        # Write plan file
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")

        print(f"[gen-plan] Generated plan using template: {execution_plan.metadata.get('template', 'unknown')}")
        print(f"[gen-plan] Complexity: {execution_plan.metadata.get('complexity', 'unknown')}")
        print(f"[gen-plan] Steps: {len(execution_plan.steps)}")
        print(f"[gen-plan] Wrote {out_path}")

        return 0

    except Exception as e:
        print(f"[gen-plan] ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="AI-OS Command Line Interface")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # run command
    ap_run = subparsers.add_parser("run", help="execute bytecode in sandbox")
    ap_run.add_argument("--root", default=".", help="project root (default .)")
    ap_run.add_argument("--bytecode", default=None, help="path to bytecode.json (default apps/forge/bytecode.json)")
    ap_run.add_argument("--dry-run", action="store_true", help="simulate without writing")
    ap_run.add_argument("--yes", action="store_true", help="auto-grant capabilities (no prompts)")
    ap_run.set_defaults(func=cmd_run)

    # prompt command
    ap_prompt = subparsers.add_parser("prompt", help="one-liner: prompt -> plan + bytecode")
    ap_prompt.add_argument("--root", default=".", help="project root (default .)")
    ap_prompt.add_argument("--goal", required=True, help="Natural language goal/prompt")
    ap_prompt.add_argument("--csv", required=True, help="Path to input CSV")
    ap_prompt.add_argument("--target", required=True, help="Target column name")
    ap_prompt.add_argument("--seed", type=int, default=1337, help="Random seed")
    ap_prompt.add_argument("--ratio", type=float, default=0.8, help="Train/test split ratio")
    ap_prompt.set_defaults(func=cmd_prompt)

    # compile command
    ap_compile = subparsers.add_parser("compile", help="compile APL plan to bytecode")
    ap_compile.add_argument("plan", nargs="?", help="Path to plan.apl.json")
    ap_compile.add_argument("-s", "--schema", default="aiox/compiler/schema.json", help="Path to APL schema")
    ap_compile.add_argument("-o", "--out", default=None, help="Output bytecode path")
    ap_compile.add_argument("--tools", action="store_true", help="Use tool-based compilation (CALL_TOOL)")
    ap_compile.set_defaults(func=cmd_compile)

    # validate command
    ap_validate = subparsers.add_parser("validate", help="validate APL plan against schema")
    ap_validate.add_argument("schema", help="Path to schema.json")
    ap_validate.add_argument("plan", help="Path to plan.apl.json")
    ap_validate.set_defaults(func=cmd_validate)

    # gen-plan command
    ap_gen = subparsers.add_parser("gen-plan", help="generate APL plan template")
    ap_gen.add_argument("--goal", default="Build a reproducible price predictor from CSV")
    ap_gen.add_argument("--csv", required=True, help="Path to input CSV")
    ap_gen.add_argument("--target", required=True, help="Target column name")
    ap_gen.add_argument("--seed", type=int, default=1337)
    ap_gen.add_argument("--ratio", type=float, default=0.8)
    ap_gen.add_argument("--out", default="apps/forge/plan.apl.json")
    ap_gen.set_defaults(func=cmd_gen_plan)

    # pack command
    ap_pack = subparsers.add_parser("pack", help="package plan+bytecode into .aiox")
    ap_pack.add_argument("--root", default=".", help="project root")
    ap_pack.add_argument("--plan", default=None, help="path to plan.apl.json")
    ap_pack.add_argument("--bytecode", default=None, help="path to bytecode.json")
    ap_pack.add_argument("-o","--out", default=None, help="output .aiox path (default sandbox/packages/app.aiox)")
    ap_pack.add_argument("--name", default=None, help="manifest name")
    ap_pack.set_defaults(func=cmd_pack)

    # replay command
    ap_replay = subparsers.add_parser("replay", help="deterministic replay check of a .aiox")
    ap_replay.add_argument("package", help="path to .aiox")
    ap_replay.add_argument("--root", default=".", help="project root")
    ap_replay.set_defaults(func=cmd_replay)

    # undo command
    ap_undo = subparsers.add_parser("undo", help="undo last non-dry run")
    ap_undo.add_argument("--root", default=".", help="project root")
    ap_undo.set_defaults(func=cmd_undo)

    # ui command
    ap_ui = subparsers.add_parser("ui", help="launch Agent Activity Monitor (TUI)")
    ap_ui.add_argument("--root", default=".", help="project root (default .)")
    ap_ui.set_defaults(func=cmd_ui)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
from __future__ import annotations
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    if len(sys.argv) < 3:
        print("usage: python compiler/validate_apl.py compiler/schema.json apps/forge/plan.apl.json", file=sys.stderr)
        sys.exit(2)

    schema_path = Path(sys.argv[1])
    plan_path = Path(sys.argv[2])

    schema = load_json(schema_path)
    plan = load_json(plan_path)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(plan), key=lambda e: e.path)

    if errors:
        print("[INVALID] Plan failed schema validation:")
        for e in errors:
            loc = "/".join(str(x) for x in e.path)
            print(f" - {loc or '<root>'}: {e.message}")
        sys.exit(1)
    else:
        print("[OK] Plan conforms to APL schema.")
        sys.exit(0)

if __name__ == "__main__":
    main()
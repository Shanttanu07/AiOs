# kernel/packaging.py
from __future__ import annotations
import json, zipfile, time
from pathlib import Path
from typing import Dict, Any

def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))

def make_aiox(plan_path: Path, bytecode_path: Path, sandbox_root: Path, out_path: Path, name: str | None = None):
    plan = read_json(plan_path)
    bc = read_json(bytecode_path)

    checks_path = sandbox_root / "out" / "checksums.json"
    checks = read_json(checks_path) if checks_path.exists() else {"run_id": None, "generated_at": None, "checksums": {}}

    manifest = {
        "name": name or (plan.get("goal","app")[:40] or "app"),
        "version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "capabilities": bc.get("capabilities", []),
        "program_len": len(bc.get("program", [])),
        "inputs": bc.get("metadata", {}).get("inputs", {}),
        "checksums": checks
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("plan.apl.json", json.dumps(plan, indent=2))
        z.writestr("bytecode.json", json.dumps(bc, indent=2))
        # minimal policy derived from capabilities
        policy = {"capabilities": bc.get("capabilities", [])}
        z.writestr("policy.json", json.dumps(policy, indent=2))
        # embed checksums as well
        z.writestr("checksums.json", json.dumps(checks, indent=2))
    return out_path
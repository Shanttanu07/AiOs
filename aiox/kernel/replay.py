# kernel/replay.py
from __future__ import annotations
import json, zipfile, shutil, os
from pathlib import Path
from typing import Dict, Any
from .runtime import run_bytecode, sha256_file

def _extract_to_tmp(zpath: Path, tmpdir: Path) -> Dict[str, Any]:
    tmpdir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "r") as z:
        z.extractall(tmpdir)
    plan = json.loads((tmpdir / "plan.apl.json").read_text(encoding="utf-8"))
    bc   = json.loads((tmpdir / "bytecode.json").read_text(encoding="utf-8"))
    checks = json.loads((tmpdir / "checksums.json").read_text(encoding="utf-8"))
    return {"plan": plan, "bytecode": bc, "checks": checks}

def compute_out_checksums(sandbox_root: Path) -> Dict[str, str]:
    out_dir = sandbox_root / "out"
    checks: Dict[str, str] = {}
    if out_dir.exists():
        for r, _, files in os.walk(out_dir):
            for fn in files:
                p = Path(r) / fn
                rel = str(p.relative_to(sandbox_root))
                checks[rel] = sha256_file(p)
    return checks

def replay_aiox(zpath: Path, sandbox_root: Path, auto_yes: bool = True, clean_out: bool = True) -> bool:
    tmp = sandbox_root / "tmp" / ("replay-" + zpath.stem)
    payload = _extract_to_tmp(zpath, tmp)

    # Optionally clean sandbox/out before replay to avoid leftover files
    out_dir = sandbox_root / "out"
    if clean_out and out_dir.exists():
        shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    # Write extracted bytecode to tmp and run
    tmp_bc = tmp / "bytecode.json"
    (sandbox_root / "logs").mkdir(parents=True, exist_ok=True)

    # Execute (not dry-run) to regenerate artifacts
    run_bytecode(tmp_bc, sandbox_root, dry_run=False, auto_yes=auto_yes)

    # Compare checksums
    prev = payload["checks"].get("checksums", {})
    now  = compute_out_checksums(sandbox_root)
    # Only compare keys present in previous (ignore extra files)
    diffs = []
    for k, h in prev.items():
        if k not in now:
            diffs.append((k, "missing-now", h, None))
        elif now[k] != h:
            diffs.append((k, "hash-mismatch", h, now[k]))

    ok = (len(diffs) == 0)
    return ok, diffs
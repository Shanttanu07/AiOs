# kernel/undo.py
from __future__ import annotations
import json, os, shutil
from pathlib import Path
from typing import List, Dict, Any

def _read_tx(log_path: Path) -> List[Dict[str, Any]]:
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]

def undo_last_run(sandbox_root: Path) -> int:
    tx_path = sandbox_root / "logs" / "tx.jsonl"
    recs = _read_tx(tx_path)
    if not recs:
        print("[undo] No transactions logged.")
        return 0

    # find last RUN_START / RUN_END block
    last_run_id = None
    for r in reversed(recs):
        if r.get("op") == "RUN_START":
            last_run_id = r.get("run_id")
            break
    if not last_run_id:
        print("[undo] No complete run found.")
        return 0

    # collect created paths for that run, in order
    created: List[Path] = []
    for r in recs:
        if r.get("run_id") != last_run_id:
            continue
        op = r.get("op")
        if op in ("WRITE_FILE","WRITE_JSON"):
            if r.get("created"):
                created.append(Path(r["path"]))
        elif op == "ZIP":
            if r.get("created"):
                created.append(Path(r["dest"]))
        elif op == "MAKE_DIR":
            if r.get("created"):
                created.append(Path(r["path"]))
        elif op == "WRITE_CHECKSUMS":
            created.append(Path(r["path"]))

    # Undo in reverse order (files then dirs)
    n = 0
    for p in reversed(created):
        try:
            p = p.resolve()
            if p.is_file():
                p.unlink(missing_ok=True)
                n += 1
            elif p.is_dir():
                # remove dir if empty; ignore if not empty
                try:
                    os.rmdir(p)
                    n += 1
                except OSError:
                    pass
        except Exception as e:
            print(f"[undo] WARN: failed to remove {p}: {e}")

    print(f"[undo] Reverted {n} created paths from {last_run_id}.")
    return n
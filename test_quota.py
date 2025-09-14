#!/usr/bin/env python3
"""Test quota enforcement"""

import json
from pathlib import Path
from kernel.runtime import run_bytecode

# Set very low limits to trigger quota enforcement
sandbox = Path("sandbox")
policy_path = sandbox / "policy.json"

policy_data = {
    "grants": {
        "978955fec6d2": {  # app_id for our forge app
            "fs.read": True,
            "fs.write": True,
            "proc.spawn": True
        }
    },
    "limits": {
        "io_bytes": 100,      # very low - 100 bytes
        "files_written": 1,   # very low - 1 file
        "cpu_ms": 100,        # very low - 100ms
        "model_calls": 1
    }
}

policy_path.parent.mkdir(parents=True, exist_ok=True)
policy_path.write_text(json.dumps(policy_data, indent=2))

print("Testing quota enforcement with very low limits...")
try:
    run_bytecode(Path("apps/forge/bytecode.json"), sandbox, auto_yes=True)
    print("ERROR: Should have failed due to quota limits!")
except Exception as e:
    print(f"SUCCESS: Quota enforcement worked - {e}")
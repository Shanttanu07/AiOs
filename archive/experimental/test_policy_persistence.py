#!/usr/bin/env python3
"""Test policy persistence"""

import json
from pathlib import Path
from kernel.runtime import run_bytecode

print("Testing policy persistence...")

# First run - should persist grants
sandbox = Path("sandbox")
policy_path = sandbox / "policy.json"

# Remove existing policy
if policy_path.exists():
    policy_path.unlink()

print("1. Running with normal limits and auto-yes (should persist grants)...")
try:
    run_bytecode(Path("apps/forge/bytecode.json"), sandbox, auto_yes=True)
    print("* First run completed - grants should be persisted")
except Exception as e:
    print(f"First run failed: {e}")

# Check if policy was persisted
if policy_path.exists():
    policy = json.loads(policy_path.read_text())
    print(f"* Policy persisted with grants: {list(policy['grants'].keys())}")

    # Second run - should use cached grants (no prompts)
    print("2. Running again - should use cached grants...")
    try:
        run_bytecode(Path("apps/forge/bytecode.json"), sandbox, auto_yes=False)  # auto_yes=False!
        print("* Second run completed using cached grants (no prompts needed)")
    except Exception as e:
        print(f"Second run failed: {e}")
else:
    print("X Policy was not persisted")
#!/usr/bin/env python3
"""Demo: Tool Registry + CALL_TOOL ISA Upgrade"""

import json
from pathlib import Path

def demo_tool_transformation():
    print("AI-OS Tool Registry + CALL_TOOL ISA Demo")
    print("=" * 50)

    print("\n1. BEFORE: Hardcoded Opcodes")
    print("-" * 30)
    print("X Fixed operations: READ_CSV, TRAIN_LR, EVAL, etc.")
    print("X Runtime dispatch by opcode name")
    print("X Adding new operations requires kernel changes")

    print("\n2. NOW: Dynamic Tool Discovery")
    print("-" * 30)
    tools_count = len(list(Path("tools").rglob("tool.json")))
    print(f"+ Discovered {tools_count} tools at runtime")
    print("+ Tools organized by category: data, ml, io, verify")
    print("+ Capabilities automatically extracted")

    print("\n3. Compilation Modes")
    print("-" * 30)

    # Show legacy vs tool compilation
    legacy_path = Path("apps/forge/bytecode.json")
    tools_path = Path("apps/forge/bytecode.tools.json")

    if legacy_path.exists():
        legacy = json.loads(legacy_path.read_text())
        print(f"Legacy mode: {legacy.get('metadata', {}).get('compilation_mode', 'legacy')}")
        print(f"  First instruction: {legacy['program'][0]}")

    if tools_path.exists():
        tools = json.loads(tools_path.read_text())
        print(f"Tools mode: {tools['metadata']['compilation_mode']}")
        print(f"  First instruction: {tools['program'][0][0]} -> {tools['program'][0][1]}")

    print("\n4. Execution Comparison")
    print("-" * 30)
    print("Legacy: [vm] 00 READ_CSV ['sandbox/in/housing.csv', 'S0']")
    print("Tools:  [vm] 00 CALL_TOOL ['read_csv', {'path': '...'}, {'table': 'S0'}]")

    print("\n5. Benefits Unlocked")
    print("-" * 30)
    print("+ Task-agnostic platform - no more hardcoded ML pipeline")
    print("+ Plugin architecture - drop new tools in tools/ directory")
    print("+ Uniform interface - all tools use same inputs/outputs pattern")
    print("+ Capability-aware - system knows what permissions tools need")
    print("+ Backwards compatible - legacy opcodes still work")

    print("\n6. Next Steps")
    print("-" * 30)
    print("* Planner/Orchestrator - AI selects and chains tools")
    print("* Cost/Carbon meters - track resource usage per tool")
    print("* Parallel scheduler - concurrent CALL_TOOL execution")
    print("* Model cache - deterministic replay for LLM tools")

    print("\n** Platform transformed from ML-specific to truly task-agnostic!")

if __name__ == "__main__":
    demo_tool_transformation()
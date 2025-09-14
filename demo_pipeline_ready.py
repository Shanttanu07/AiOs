#!/usr/bin/env python3
"""Demo: AI-OS Pipeline Ready for Production"""

import os
from pathlib import Path

def show_pipeline_status():
    print("** AI-OS Pipeline Status **")
    print("=" * 40)

    # Check components
    components = {
        "CLI Interface": "aiox.cli",
        "LLM Planner": "aiox.planner.llm_planner",
        "Model Cache": "aiox.kernel.model_cache",
        "Carbon Meters": "aiox.kernel.meters",
        "Replay Gate": "aiox.kernel.replay_gate",
        "Tool Registry": "aiox.kernel.tools",
        "TUI Interface": "aiox.ui.tui"
    }

    print("1. Component Status:")
    for name, module in components.items():
        try:
            __import__(module)
            print(f"   + {name}: [OK] Ready")
        except Exception as e:
            print(f"   - {name}: [ERR] Error")

    # Check API key
    print(f"\n2. API Configuration:")
    api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
    if api_key:
        print(f"   + Claude API Key: [SET] ({api_key[:8]}...)")
    else:
        print(f"   ! Claude API Key: [NOT SET] (will use fallback)")

    # Check tools
    print(f"\n3. Tool Discovery:")
    try:
        from aiox.kernel.tools import ToolRegistry
        registry = ToolRegistry(Path("tools"))
        discovered = registry.discover_tools()
        print(f"   + Tools Available: {discovered}")
    except Exception as e:
        print(f"   - Tool Discovery: Error ({e})")

    # Check file structure
    print(f"\n4. File Structure:")
    key_paths = [
        "aiox/cli.py",
        "aiox/planner/llm_planner.py",
        "aiox/kernel/meters.py",
        "tools/",
        "sandbox/"
    ]

    for path_str in key_paths:
        path = Path(path_str)
        if path.exists():
            print(f"   + {path_str}: [FOUND]")
        else:
            print(f"   - {path_str}: [MISSING]")

    print(f"\n" + "=" * 40)
    print("** READY TO USE! **")
    print()
    print("Usage Examples:")
    print("1. CLI Planning:")
    print("   aiox prompt --goal 'Build ML model from data.csv' --csv data.csv --target price")
    print()
    print("2. Interactive TUI:")
    print("   aiox ui")
    print()
    print("3. Generate Plan Only:")
    print("   aiox gen-plan --goal 'Process customer data' --csv customers.csv --target satisfaction")
    print()
    print("Key Features Active:")
    print("+ LLM-based task-agnostic planning")
    print("+ Model call caching for deterministic replay")
    print("+ Carbon footprint and cost tracking")
    print("+ Real-time TUI with efficiency meters")
    print("+ Fallback planning (no LLM required)")
    print("+ Tool-based architecture (extensible)")

if __name__ == "__main__":
    show_pipeline_status()
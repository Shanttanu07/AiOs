#!/usr/bin/env python3
"""
Real-Time Terminal Interface for AI-OS
======================================

Simple terminal interface that:
1. Accepts natural language prompts
2. Generates APL in real-time
3. Compiles to bytecode
4. Shows execution in TUI with carbon/cost tracking

Usage:
    python realtime_terminal.py
"""

import sys
import json
import subprocess
from pathlib import Path

# Add aiox to path
sys.path.insert(0, str(Path(__file__).parent))

from aiox.kernel.tools import ToolRegistry
from aiox.planner.core import PlanGenerator
from aiox.planner.apl_converter import APLConverter


def main():
    """Real-time terminal interface"""
    root = Path('.').resolve()

    # Initialize components
    print("AI-OS Real-Time Terminal Interface")
    print("==================================")
    print("Initializing...")

    registry = ToolRegistry(root / 'tools')
    count = registry.discover_tools()
    print(f"Discovered {count} tools")

    planner = PlanGenerator(registry, root / 'sandbox')
    converter = APLConverter(registry)

    print("Ready for real-time prompts!")
    print("Type 'tui' to launch TUI interface")
    print("Type 'quit' to exit")
    print()

    while True:
        # Get prompt
        try:
            prompt = input("AI-OS> ").strip()
        except KeyboardInterrupt:
            break

        if not prompt:
            continue

        if prompt.lower() in ['quit', 'exit', 'q']:
            break

        if prompt.lower() == 'tui':
            # Launch TUI
            print("Launching TUI...")
            try:
                subprocess.run([sys.executable, '-m', 'aiox.ui.tui'], cwd=root)
            except Exception as e:
                print(f"TUI error: {e}")
            continue

        # Process prompt
        print(f"Processing: {prompt}")
        try:
            # Generate APL
            execution_plan = planner.generate_plan(goal=prompt)
            apl_data = converter.convert_to_apl(execution_plan)

            # Save APL
            plan_path = root / 'apps' / 'forge' / 'plan.apl.json'
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(json.dumps(apl_data, indent=2))

            print(f"Generated APL with {len(execution_plan.steps)} steps")

            # Compile bytecode
            compile_result = subprocess.run([
                sys.executable, '-m', 'aiox.compiler.compile_bc',
                str(plan_path), '--tools'
            ], capture_output=True, text=True, cwd=root)

            if compile_result.returncode == 0:
                print("Bytecode compiled successfully")

                # Execute - use correct bytecode filename pattern (same as compiler)
                bc_path = plan_path.with_suffix('.bytecode.json')
                exec_result = subprocess.run([
                    sys.executable, '-m', 'aiox', 'run',
                    '--bytecode', str(bc_path), '--yes'
                ], capture_output=True, text=True, cwd=root)

                if exec_result.returncode == 0:
                    print("Execution completed")
                    print("Launch TUI to see carbon/cost metrics and results")
                else:
                    print(f"Execution issue: {exec_result.stderr.strip()}")

            else:
                print(f"Compilation failed: {compile_result.stderr.strip()}")

        except Exception as e:
            print(f"Error: {e}")

        print()

    print("Goodbye!")


if __name__ == '__main__':
    main()
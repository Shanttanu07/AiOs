#!/usr/bin/env python3
"""
AI-OS Real-Time Demo Script
===========================

This script demonstrates the complete AI-OS pipeline:
1. Natural language prompt input
2. LLM-based APL generation
3. Dynamic bytecode compilation
4. Real-time execution with carbon/cost tracking
5. FlightFixer tool chain showcase

Usage:
    python demo_real_time.py

The demo will:
- Show TUI with prominent carbon/cost meters
- Accept natural language prompts
- Generate APL plans dynamically
- Execute with real-time metrics
- Display results with cost analysis
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add aiox to Python path
sys.path.insert(0, str(Path(__file__).parent))

from aiox.kernel.tools import ToolRegistry
from aiox.planner.core import PlanGenerator
from aiox.planner.apl_converter import APLConverter
from aiox.kernel.meters import CarbonCostMeter
from aiox.ui.tui import ActivityUI
import curses


class DemoOrchestrator:
    """Orchestrate the real-time demo"""

    def __init__(self):
        self.root = Path('.').resolve()
        self.sandbox = self.root / 'sandbox'
        self.tools_path = self.root / 'tools'

        # Initialize components
        print("Initializing AI-OS Demo Platform...")
        self.registry = ToolRegistry(self.tools_path)
        discovered = self.registry.discover_tools()
        print(f"  - Discovered {discovered} tools")

        self.planner = PlanGenerator(self.registry, self.sandbox)
        self.converter = APLConverter(self.registry)
        self.meter = CarbonCostMeter(self.sandbox)

        # Create demo directories
        self._setup_demo_environment()

        print("  - AI-OS Demo Platform Ready!")
        print()

    def _setup_demo_environment(self):
        """Set up demo environment with sample data"""
        # Ensure directories exist
        (self.sandbox / 'in').mkdir(parents=True, exist_ok=True)
        (self.sandbox / 'out').mkdir(parents=True, exist_ok=True)
        (self.root / 'apps' / 'forge').mkdir(parents=True, exist_ok=True)

        # Create sample data if it doesn't exist
        twitter_data = self.sandbox / 'in' / 'twitter_airline_sentiment.csv'
        bts_data = self.sandbox / 'in' / 'bts_ontime_feb2015.csv'

        if not twitter_data.exists() or not bts_data.exists():
            print("  - Setting up FlightFixer demo data...")
            try:
                from create_simple_sample_data import main as create_data
                create_data()
            except Exception as e:
                print(f"    Warning: Could not create sample data: {e}")

    def show_welcome_banner(self):
        """Display welcome banner with platform capabilities"""
        print("=" * 80)
        print("  AI-OS :: Real-Time Task-Agnostic Automation Platform")
        print("=" * 80)
        print()
        print("CAPABILITIES:")
        print("  - Natural language -> APL generation (LLM-based)")
        print("  - Dynamic tool discovery (20+ tools)")
        print("  - Real-time bytecode compilation")
        print("  - Carbon footprint & cost tracking")
        print("  - FlightFixer: Messy data -> Actionable outputs")
        print()
        print("FLIGHTFIXER DEMO TOOLS:")
        ff_tools = [t for t in self.registry.get_all_tool_names()
                   if any(w in t.lower() for w in ['flight', 'tweets', 'bts', 'parse', 'refund', 'action'])]
        print(f"  {', '.join(ff_tools)}")
        print()
        print("CARBON & COST TRACKING:")
        historical = self.meter.get_historical_stats()
        totals = historical.get('totals', {})
        print(f"  Total runs: {totals.get('runs_analyzed', 0)}")
        print(f"  Total CO2: {totals.get('total_co2_grams', 0):.1f}g")
        print(f"  Total cost: ${totals.get('total_cost_usd', 0):.6f}")
        print()

    def get_demo_prompt(self) -> Optional[str]:
        """Get natural language prompt from user"""
        print("DEMO PROMPTS (or enter custom):")
        print("1. 'Process airline complaints and identify refunds using DOT 2024 rules'")
        print("2. 'Analyze flight delay patterns and generate insights report'")
        print("3. 'Match customer tweets with flight data for refund processing'")
        print("4. Custom prompt")
        print("5. Launch TUI interface")
        print("6. Exit")
        print()

        choice = input("Select option [1-6]: ").strip()

        if choice == '1':
            return "Process airline complaint tweets and match them with flight data to identify refund eligibility using DOT 2024 rules and generate actionable outputs"
        elif choice == '2':
            return "Analyze flight delay patterns from BTS data and generate comprehensive insights report with business recommendations"
        elif choice == '3':
            return "Load customer complaint tweets, parse flight details, match with BTS flight data, and create refund claims using DOT regulations"
        elif choice == '4':
            return input("Enter your custom prompt: ").strip()
        elif choice == '5':
            return "LAUNCH_TUI"
        elif choice == '6':
            return None
        else:
            print("Invalid choice. Try again.")
            return self.get_demo_prompt()

    def process_prompt_to_execution(self, prompt: str) -> Dict[str, Any]:
        """Complete pipeline: prompt → APL → bytecode → execution"""
        results = {
            'prompt': prompt,
            'success': False,
            'apl_generated': False,
            'bytecode_compiled': False,
            'executed': False,
            'carbon_cost': {},
            'outputs': []
        }

        print("REAL-TIME PROCESSING PIPELINE")
        print("=" * 60)

        # Step 1: Generate APL
        print("STEP 1: Natural Language -> APL Generation")
        print(f"Prompt: {prompt}")
        print("Generating execution plan...")

        try:
            start_time = time.time()
            execution_plan = self.planner.generate_plan(
                goal=prompt,
                input_csv="twitter_airline_sentiment.csv"
            )
            apl_data = self.converter.convert_to_apl(execution_plan)

            # Save APL
            plan_path = self.root / 'apps' / 'forge' / 'demo_plan.apl.json'
            plan_path.write_text(json.dumps(apl_data, indent=2))

            apl_time = time.time() - start_time
            results['apl_generated'] = True

            print(f"  ✓ APL generated ({apl_time:.2f}s)")
            print(f"  ✓ Planner: {execution_plan.metadata.get('planner_type', 'unknown')}")
            print(f"  ✓ Steps: {len(execution_plan.steps)}")

            # Show operations
            ops = [step.get('op', '?') for step in apl_data.get('steps', [])]
            print(f"  - Operations: {' -> '.join(ops)}")
            print()

        except Exception as e:
            print(f"  ERROR: APL generation failed: {e}")
            return results

        # Step 2: Compile bytecode
        print("STEP 2: APL -> Bytecode Compilation")
        try:
            import subprocess
            compile_cmd = [
                sys.executable, '-m', 'aiox.compiler.compile_bc',
                str(plan_path), '--tools'
            ]

            start_time = time.time()
            result = subprocess.run(compile_cmd, capture_output=True, text=True, cwd=self.root)
            compile_time = time.time() - start_time

            if result.returncode == 0:
                results['bytecode_compiled'] = True
                print(f"  SUCCESS: Bytecode compiled ({compile_time:.2f}s)")
                # Correct bytecode filename: .apl.json -> .apl.bytecode.json
                bc_path = plan_path.with_suffix('.apl.bytecode.json')
                print(f"  Saved: {bc_path.name}")
                print()
            else:
                print(f"  ERROR: Compilation failed: {result.stderr}")
                return results

        except Exception as e:
            print(f"  ERROR: Compilation error: {e}")
            return results

        # Step 3: Execute with carbon/cost tracking
        print("STEP 3: Bytecode -> Execution (with carbon/cost tracking)")
        try:
            # Start carbon tracking
            current_stats_before = self.meter.get_current_run_stats()

            exec_cmd = [
                sys.executable, '-m', 'aiox', 'run',
                '--bytecode', str(bc_path), '--yes'
            ]

            start_time = time.time()
            result = subprocess.run(exec_cmd, capture_output=True, text=True, cwd=self.root)
            exec_time = time.time() - start_time

            # Get carbon/cost metrics
            current_stats_after = self.meter.get_current_run_stats()

            if result.returncode == 0:
                results['executed'] = True
                results['success'] = True
                print(f"  ✓ Execution completed ({exec_time:.2f}s)")

                # Show carbon/cost metrics
                if current_stats_after.get('status') == 'active_run':
                    co2 = current_stats_after.get('total_co2_grams', 0)
                    cost = current_stats_after.get('total_cost_usd', 0)
                    tokens = current_stats_after.get('total_tokens', 0)
                    tools_count = current_stats_after.get('tools_executed', 0)

                    print(f"  ✓ Carbon footprint: {co2:.2f}g CO2")
                    print(f"  ✓ Cost: ${cost:.6f}")
                    print(f"  ✓ Tokens: {tokens}")
                    print(f"  ✓ Tools executed: {tools_count}")

                    results['carbon_cost'] = {
                        'co2_grams': co2,
                        'cost_usd': cost,
                        'tokens': tokens,
                        'tools_executed': tools_count
                    }

                # Check for outputs
                out_dir = self.sandbox / 'out'
                if out_dir.exists():
                    outputs = list(out_dir.rglob('*'))
                    if outputs:
                        print(f"  ✓ Generated {len(outputs)} output files")
                        results['outputs'] = [str(f.relative_to(self.sandbox)) for f in outputs if f.is_file()]

                print()
            else:
                print(f"  ⚠  Execution completed with issues: {result.stderr}")
                results['executed'] = True  # Mark as executed even with issues
                print()

        except Exception as e:
            print(f"  ❌ Execution error: {e}")
            return results

        return results

    def show_results_summary(self, results: Dict[str, Any]):
        """Display comprehensive results summary"""
        print("🎯 DEMO RESULTS SUMMARY")
        print("=" * 60)

        # Pipeline status
        print("PIPELINE STATUS:")
        print(f"  APL Generation: {'✓' if results['apl_generated'] else '❌'}")
        print(f"  Bytecode Compile: {'✓' if results['bytecode_compiled'] else '❌'}")
        print(f"  Execution: {'✓' if results['executed'] else '❌'}")
        print(f"  Overall Success: {'✓' if results['success'] else '❌'}")
        print()

        # Carbon & Cost metrics
        if results['carbon_cost']:
            metrics = results['carbon_cost']
            print("CARBON & COST IMPACT:")
            print(f"  CO2 Footprint: {metrics['co2_grams']:.2f}g")
            print(f"  Cost: ${metrics['cost_usd']:.6f}")
            print(f"  Tokens: {metrics['tokens']}")
            print(f"  Tools Used: {metrics['tools_executed']}")

            # Impact assessment
            co2 = metrics['co2_grams']
            cost = metrics['cost_usd']
            if co2 < 1 and cost < 0.01:
                print("  Impact Level: 🟢 MINIMAL")
            elif co2 < 10 and cost < 0.1:
                print("  Impact Level: 🟡 MODERATE")
            else:
                print("  Impact Level: 🔴 SIGNIFICANT")
            print()

        # Generated outputs
        if results['outputs']:
            print("GENERATED OUTPUTS:")
            for output in results['outputs'][:10]:  # Show first 10
                print(f"  📄 {output}")
            if len(results['outputs']) > 10:
                print(f"  ... and {len(results['outputs']) - 10} more files")
            print()

        # Historical totals
        historical = self.meter.get_historical_stats()
        totals = historical.get('totals', {})
        print("HISTORICAL TOTALS:")
        print(f"  Total Runs: {totals.get('runs_analyzed', 0)}")
        print(f"  Total CO2: {totals.get('total_co2_grams', 0):.1f}g")
        print(f"  Total Cost: ${totals.get('total_cost_usd', 0):.6f}")
        print()

    def launch_tui(self):
        """Launch the TUI interface"""
        print("🖥️  Launching AI-OS TUI Interface...")
        print("   (Press 'q' to exit TUI and return to demo)")
        print()
        time.sleep(1)

        def tui_wrapper(stdscr):
            ui = ActivityUI(stdscr, self.root)
            ui.loop()

        try:
            curses.wrapper(tui_wrapper)
            print("🖥️  TUI session ended, returning to demo...")
            print()
        except Exception as e:
            print(f"TUI error: {e}")

    def run_demo(self):
        """Main demo loop"""
        self.show_welcome_banner()

        while True:
            prompt = self.get_demo_prompt()

            if prompt is None:
                print("👋 Demo session ended. Thank you!")
                break
            elif prompt == "LAUNCH_TUI":
                self.launch_tui()
                continue

            print()
            print("-" * 80)
            results = self.process_prompt_to_execution(prompt)
            print("-" * 80)

            self.show_results_summary(results)

            # Ask to continue
            print("Press Enter to continue demo, or 'q' to quit...")
            if input().strip().lower() == 'q':
                break

        print()
        print("🎬 AI-OS Real-Time Demo Complete!")
        print("   Thank you for exploring task-agnostic automation!")


def main():
    """Main demo entry point"""
    try:
        demo = DemoOrchestrator()
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
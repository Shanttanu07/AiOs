#!/usr/bin/env python3
"""Test the LLM-based Planner/Orchestrator v1 with diverse task types"""

import json
import os
from pathlib import Path
from aiox.kernel.tools import ToolRegistry
from aiox.planner.core import PlanGenerator
from aiox.planner.apl_converter import APLConverter

def test_llm_planner():
    print("Testing LLM-based Planner/Orchestrator v1")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("⚠️  No Claude API key found in environment variables.")
        print("   Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY")
        print("   The system will prompt for the key when needed.")
        print()

    # Initialize tools and planner
    root = Path(".").resolve()
    tools_root = root / "tools"
    registry = ToolRegistry(tools_root)
    discovered = registry.discover_tools()
    print(f"Discovered {discovered} tools")
    print()

    planner = PlanGenerator(registry)
    converter = APLConverter()

    # Test diverse goal types (task-agnostic!)
    test_goals = [
        {
            "description": "Data Analysis Task",
            "goal": "Analyze the sales_data.csv file and create a comprehensive report",
            "csv": "sales_data.csv"
        },
        {
            "description": "File Processing Task",
            "goal": "Read customer_list.csv, clean the data, and export to JSON format",
            "csv": "customer_list.csv"
        },
        {
            "description": "Research Task",
            "goal": "Process research_papers.csv and generate summary statistics",
            "csv": "research_papers.csv"
        },
        {
            "description": "ML Pipeline Task",
            "goal": "Build a price predictor from housing.csv: train model, evaluate, and package as CLI app",
            "csv": "housing.csv",
            "target": "price"
        },
        {
            "description": "Visualization Task",
            "goal": "Load stock_prices.csv and create visualizations showing trends over time",
            "csv": "stock_prices.csv"
        },
        {
            "description": "General Automation Task",
            "goal": "Process inventory.csv, check for low stock items, and generate alerts",
            "csv": "inventory.csv"
        }
    ]

    successful_tests = 0

    for i, test_case in enumerate(test_goals, 1):
        print(f"{i}. Test Case: {test_case['description']}")
        print("-" * 50)
        print(f"Goal: {test_case['goal']}")

        try:
            # Generate execution plan using LLM
            execution_plan = planner.generate_plan(
                goal=test_case["goal"],
                input_csv=test_case.get("csv"),
                target_column=test_case.get("target")
            )

            # Print plan details
            metadata = execution_plan.metadata
            print(f"Planner: {metadata.get('planner_type', 'unknown')}")
            print(f"Task Type: {metadata.get('task_type', 'unknown')}")
            print(f"Complexity: {metadata.get('complexity', 'unknown')}")
            print(f"Intent: {metadata.get('intent', 'N/A')}")
            print(f"Steps: {len(execution_plan.steps)}")
            print(f"Capabilities: {', '.join(sorted(execution_plan.capabilities))}")

            # Show execution steps
            print("\nPlanned Steps:")
            for j, step in enumerate(execution_plan.steps[:8], 1):  # Show first 8 steps
                inputs_str = str(step.inputs)[:60] + "..." if len(str(step.inputs)) > 60 else str(step.inputs)
                print(f"  {j}. {step.tool} - {step.description}")
                print(f"     Inputs: {inputs_str}")
                if step.outputs:
                    print(f"     Outputs: {step.outputs}")

            if len(execution_plan.steps) > 8:
                print(f"     ... and {len(execution_plan.steps) - 8} more steps")

            # Convert to APL format
            apl_data = converter.convert_to_apl(execution_plan)

            print(f"\n✓ SUCCESS - Generated {len(apl_data.get('steps', []))} APL steps")
            successful_tests += 1

        except Exception as e:
            print(f"✗ ERROR: {e}")

        print()

    # Summary
    print("=" * 60)
    print(f"LLM Planner Test Results: {successful_tests}/{len(test_goals)} successful")

    if successful_tests == len(test_goals):
        print("🎉 All tests passed! LLM-based task-agnostic planning is working!")
    elif successful_tests > 0:
        print(f"⚠️  Some tests passed. Check failed cases above.")
    else:
        print("❌ All tests failed. Check API key and implementation.")

    print()
    print("Key Benefits of LLM-based Planning:")
    print("- Task-agnostic: Works with any goal, not just ML")
    print("- Intelligent tool selection based on available tools")
    print("- Dynamic workflow generation with proper data flow")
    print("- Context-aware parameter filling")
    print("- Handles complex multi-step workflows")

if __name__ == "__main__":
    test_llm_planner()
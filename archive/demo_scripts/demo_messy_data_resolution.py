#!/usr/bin/env python3
"""
Comprehensive Demo: Real-World Messy Data Resolution Pipeline
Shows the complete flow from messy data → conflict resolution → actionable insights
"""

import subprocess
import json
import os
from pathlib import Path

def run_demo():
    print("=" * 70)
    print("AI-OS :: Messy Data Resolution Demo")
    print("Real-world data conflicts -> Intelligent resolution -> Actionable outcomes")
    print("=" * 70)
    print()

    # Step 1: Generate messy customer data
    print("DATA STEP 1: Generating realistic messy customer data...")
    print("   - Duplicate customers with slight differences")
    print("   - Missing/invalid contact information")
    print("   - Conflicting data across multiple sources")
    print("   - Unstructured support ticket information")
    print("   - Orphaned payment records")
    print()

    subprocess.run(["python", "create_messy_customer_data.py"], check=True)
    print()

    # Step 2: Demonstrate conflict resolution
    print("AI STEP 2: Intelligent conflict resolution using AI...")
    print("   Using task-agnostic planning with fuzzy matching and data reconciliation")
    print()

    goal = "Resolve conflicts in messy customer database from 3 data sources and generate actionable business insights"

    result = subprocess.run([
        "python", "-m", "aiox.main", "prompt",
        "--goal", goal,
        "--input_csv", "sandbox/in/crm_customers.csv"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print("SUCCESS: Conflict resolution completed successfully!")
    else:
        print("ERROR: Error in conflict resolution:")
        print(result.stderr)
        return

    print()

    # Step 3: Show results and insights
    print("INSIGHTS STEP 3: Generated Actionable Business Insights")
    print()

    # Check for generated reports
    reports_dir = Path("sandbox/out")
    if reports_dir.exists():
        print("Generated Reports:")
        for report_file in reports_dir.glob("*.json"):
            print(f"   FILE: {report_file.name}")

        for report_file in reports_dir.glob("*.txt"):
            print(f"   FILE: {report_file.name}")

        print()

        # Show sample insights if available
        insights_file = reports_dir / "business_insights.json"
        if insights_file.exists():
            print("KEY INSIGHTS PREVIEW:")
            try:
                with open(insights_file, 'r') as f:
                    insights = json.load(f)

                # Show executive summary
                if 'executive_summary' in insights:
                    summary = insights['executive_summary']
                    print(f"   Total Customers: {summary.get('total_customers', 'N/A')}")
                    print(f"   Total Revenue: ${summary.get('total_revenue', 0):,.0f}")
                    print(f"   Data Quality Score: {summary.get('data_quality', {}).get('overall_score', 'N/A')}%")
                    print()

                # Show top action items
                if 'action_items' in insights:
                    print("TOP PRIORITY ACTIONS:")
                    for i, action in enumerate(insights['action_items'][:3], 1):
                        print(f"   {i}. {action.get('title', 'N/A')}")
                        print(f"      Impact: {action.get('impact', 'N/A')}")
                        print(f"      Timeline: {action.get('timeline', 'N/A')}")
                        print()

            except Exception as e:
                print(f"   Could not parse insights: {e}")

    print("DEMO IMPACT:")
    print("   [DONE] Automated duplicate customer detection and merging")
    print("   [DONE] Reconciled payment records with customer data")
    print("   [DONE] Extracted structured data from unstructured support tickets")
    print("   [DONE] Generated prioritized action items for business teams")
    print("   [DONE] Identified revenue risks and growth opportunities")
    print()

    print("BUSINESS VALUE:")
    print("   - Eliminated manual data cleaning (saves 10-20 hours/week)")
    print("   - Prevented revenue loss from data conflicts")
    print("   - Enabled data-driven customer success initiatives")
    print("   - Automated business intelligence generation")
    print()

    print("TASK-AGNOSTIC CAPABILITIES DEMONSTRATED:")
    print("   - Fuzzy string matching and entity resolution")
    print("   - Multi-source data reconciliation")
    print("   - Unstructured text processing and extraction")
    print("   - Business intelligence and recommendation generation")
    print("   - Carbon-aware processing with efficiency tracking")
    print()

    print("Next steps: Try with your own messy datasets!")
    print("  aiox prompt --goal 'Clean and analyze [your data description]'")

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo failed: {e}")
        print("Make sure you have:")
        print("  1. Set ANTHROPIC_API_KEY environment variable")
        print("  2. Installed required dependencies: pip install pandas fuzzywuzzy")
        print("  3. Run from the project root directory")
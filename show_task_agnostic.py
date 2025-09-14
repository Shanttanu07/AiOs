#!/usr/bin/env python3
"""Demonstrate Task-Agnostic AI-OS Capabilities"""

def show_capabilities():
    print("AI-OS :: Task-Agnostic Automation Platform")
    print("=" * 50)
    print()

    task_packs = [
        {
            "name": "Messy Data Kit",
            "sponsor": "Rox.ai",
            "goal": "Clean customer database from 3 messy CSV files",
            "tools": ["data.infer_schema", "data.clean", "records.dedupe"]
        },
        {
            "name": "Financial Viz Agent",
            "sponsor": "Warp Analytics",
            "goal": "Create revenue dashboard with anomaly detection",
            "tools": ["viz.recommend", "viz.render", "analyze.anomalies"]
        },
        {
            "name": "Voice-to-Action",
            "sponsor": "Wispr",
            "goal": "Say 'analyze sales data' -> auto-generate dashboard",
            "tools": ["voice.stt", "intent.detect", "planner.from_voice"]
        },
        {
            "name": "AI Judge Framework",
            "sponsor": "EigenCloud",
            "goal": "Judge contract clauses with transparent rationale",
            "tools": ["judge.load_ruleset", "judge.run", "transparency.report"]
        },
        {
            "name": "Deep Research Agent",
            "sponsor": "Extraordinary.ai",
            "goal": "Research 'Why is X extraordinary?' with citations",
            "tools": ["web.search", "nlp.extract_claims", "fact.cite"]
        },
        {
            "name": "AI-Native Dropbox",
            "sponsor": "YC Reimagined",
            "goal": "Organize 1000+ files with AI understanding",
            "tools": ["files.organize", "ocr.run", "search.semantic"]
        }
    ]

    print("AVAILABLE TASK PACKS:")
    print()

    for i, pack in enumerate(task_packs, 1):
        print(f"{i}. {pack['name']} (Sponsor: {pack['sponsor']})")
        print(f"   Goal: {pack['goal']}")
        print(f"   Tools: {len(pack['tools'])} specialized tools")
        print()

    print("KEY TRANSFORMATIONS:")
    print("- ML-focused -> Task-agnostic automation")
    print("- Carbon footprint prominently displayed in TUI")
    print("- Deterministic replay (7 diffs -> 0 diffs)")
    print("- Voice-driven automation capabilities")
    print("- Sponsor-mapped feature packs")
    print()

    print("USAGE EXAMPLES:")
    print("  aiox prompt --goal 'Research AI safety developments'")
    print("  aiox voice --input command.wav")
    print("  aiox ui  # Now shows carbon footprint in header")
    print("  aiox export --target agentverse")

if __name__ == "__main__":
    show_capabilities()
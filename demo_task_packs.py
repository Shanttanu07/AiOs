#!/usr/bin/env python3
"""Demo: Task-Agnostic AI-OS with Diverse Feature Packs"""

import json
from pathlib import Path

def showcase_task_agnostic_capabilities():
    print("🚀 AI-OS :: Task-Agnostic Automation Platform")
    print("=" * 60)
    print()

    # Showcase different task categories with example goals
    task_packs = {
        "🧹 Messy Data Kit": {
            "sponsor": "Rox.ai",
            "description": "Clean, understand, and organize chaotic data",
            "example_goals": [
                "Clean and dedupe customer database from 3 messy CSV files",
                "Infer schema from mixed JSON/CSV/text employee records",
                "Resolve conflicts in product catalog data using ML + rules"
            ],
            "tools": ["data.infer_schema", "data.clean", "records.dedupe", "records.resolve_conflicts", "validate.report"],
            "demo_input": "chaotic_customer_data/",
            "demo_output": "clean_structured_database.csv + validation_report.md"
        },

        "📊 Financial Viz Agent": {
            "sponsor": "Warp Analytics",
            "description": "Auto-generate financial charts with AI justification",
            "example_goals": [
                "Create quarterly revenue dashboard with anomaly detection",
                "Analyze payroll trends by department and tax category",
                "Generate executive summary with key financial insights"
            ],
            "tools": ["viz.recommend", "viz.render", "analyze.anomalies", "cohorts.build", "export.report"],
            "demo_input": "payments_payroll_sample.csv",
            "demo_output": "interactive_dashboard.html + insights_report.md"
        },

        "🌐 Agent Marketplace Bridge": {
            "sponsor": "Fetch.ai",
            "description": "Export plans as uAgents microservices",
            "example_goals": [
                "Deploy data analysis pipeline as Agentverse microservice",
                "Create ASI:One Chat Protocol endpoint for AI workflows",
                "Package automation as marketplace-ready agent"
            ],
            "tools": ["export.uagents", "agentverse.deploy", "asi_one.protocol", "marketplace.publish"],
            "demo_input": "local_plan.apl.json",
            "demo_output": "live_agentverse_endpoint + manifest.yaml"
        },

        "⚖️ AI Judge Framework": {
            "sponsor": "EigenCloud",
            "description": "Domain-specific judging with transparent rationales",
            "example_goals": [
                "Judge contract clause compliance with legal rulebook",
                "Score sports plays using official ruleset + AI analysis",
                "Evaluate code quality with calibrated confidence metrics"
            ],
            "tools": ["judge.load_ruleset", "judge.run", "judge.calibrate", "transparency.report"],
            "demo_input": "contract_clauses.json + legal_rulebook.yaml",
            "demo_output": "{decision, rationale, score, confidence} + cost_breakdown"
        },

        "🔍 Deep Research Agent": {
            "sponsor": "Extraordinary.ai",
            "description": "Collect and synthesize web research into profiles",
            "example_goals": [
                "Research 'Why is Satya Nadella extraordinary?' with citations",
                "Create comprehensive profile of AI safety developments",
                "Generate cited report on renewable energy breakthroughs"
            ],
            "tools": ["web.search", "web.scrape", "nlp.extract_claims", "fact.cite", "profile.emit"],
            "demo_input": "research_query: 'AI safety developments 2024'",
            "demo_output": "cited_profile_page.html with links/snippets"
        },

        "🎤 Voice-to-Action": {
            "sponsor": "Wispr",
            "description": "Speech-driven automation with intent detection",
            "example_goals": [
                "Say 'Analyze last month's sales' → auto-generate dashboard",
                "Voice command 'Organize my downloads folder' → AI file organization",
                "Speak goal → watch plan materialize → confirm and run"
            ],
            "tools": ["voice.stt", "intent.detect", "planner.from_voice", "ui.confirm_and_run"],
            "demo_input": "voice_command.wav",
            "demo_output": "executed_automation_plan + TUI_confirmation"
        },

        "🎨 Design Copilot Suite": {
            "sponsor": "Lica Design",
            "description": "AI-driven design from prompts to production",
            "example_goals": [
                "Generate fintech pitch deck from outline + style picker",
                "Create mobile app mockups with multi-agent layout optimization",
                "Design logo variations with typography recommendations"
            ],
            "tools": ["slides.from_outline", "design.style_recommender", "svg.layout_agent", "export.pdf"],
            "demo_input": "'Pitch deck for fintech payroll startup'",
            "demo_output": "styled_slides.pdf + design_variations.svg"
        },

        "📈 Large Graph Viewer": {
            "sponsor": "Arrowstreet Capital",
            "description": "Interactive visualization for massive datasets",
            "example_goals": [
                "Visualize 10K+ entity relationship graph with level-of-detail",
                "Create interactive network of financial dependencies",
                "Render social media interaction graph with WebGL performance"
            ],
            "tools": ["graph.sample", "graph.layout_stream", "webgl.render", "tui.link"],
            "demo_input": "entity_graph_50k_nodes.json",
            "demo_output": "interactive_webgl_viewer + responsive_controls"
        },

        "⚡ Scale Adapters": {
            "sponsor": "Modal + Cerebras",
            "description": "Serverless scale with fast inference backends",
            "example_goals": [
                "Switch LLM backend from local to Modal serverless",
                "Use Cerebras for 10x faster model inference",
                "Auto-scale based on workload with cost optimization"
            ],
            "tools": ["modal.deploy", "cerebras.inference", "backend.switch", "cost.optimize"],
            "demo_input": "existing_workflow.apl + scale_policy.yaml",
            "demo_output": "faster_cheaper_execution + performance_metrics"
        },

        "📁 AI-Native Dropbox": {
            "sponsor": "YC Reimagined",
            "description": "File understanding and organization with AI in driver's seat",
            "example_goals": [
                "Run 'messyops.aiplan' to organize 1000+ mixed files",
                "Auto-extract insights from documents using OCR + NLP",
                "Create searchable knowledge base from file contents"
            ],
            "tools": ["files.organize", "ocr.run", "nlp.understand", "search.semantic", "kb.create"],
            "demo_input": "chaotic_documents_folder/",
            "demo_output": "organized_structure + searchable_knowledge_base"
        }
    }

    print("🎯 AVAILABLE TASK PACKS:")
    print()

    for pack_name, pack_info in task_packs.items():
        print(f"{pack_name}")
        print(f"   Sponsor: {pack_info['sponsor']}")
        print(f"   Description: {pack_info['description']}")
        print(f"   Example Goals:")
        for goal in pack_info['example_goals'][:2]:  # Show first 2 goals
            print(f"     • {goal}")
        print(f"   Tools: {len(pack_info['tools'])} specialized tools")
        print(f"   Demo: {pack_info['demo_input']} → {pack_info['demo_output']}")
        print()

    print("=" * 60)
    print("🔥 KEY FEATURES:")
    print()
    print("✅ Task-Agnostic Planning - Handle ANY automation goal")
    print("✅ LLM-Powered Intelligence - Claude integration for smart planning")
    print("✅ Carbon Footprint Tracking - Environmental impact visibility")
    print("✅ Deterministic Replay - 100% reproducible executions")
    print("✅ Real-time TUI - Live progress with efficiency meters")
    print("✅ Sponsor Integration - Feature packs mapped to challenge partners")
    print("✅ Voice-Driven Interface - Speak your goals, watch automation happen")
    print("✅ Scalable Backends - Modal/Cerebras integration for performance")
    print()

    print("🚀 USAGE:")
    print("   aiox prompt --goal 'Research renewable energy trends' --context general")
    print("   aiox voice --input command.wav  # Voice-driven automation")
    print("   aiox ui                         # Interactive TUI with carbon tracking")
    print("   aiox export --target agentverse # Deploy to agent marketplace")
    print()

    print("💡 The AI-OS platform transforms from ML-focused to truly task-agnostic,")
    print("   handling everything from messy data cleaning to voice-driven automation,")
    print("   financial analysis to AI-native file organization - all while tracking")
    print("   carbon footprint and maintaining deterministic execution.")

def create_sample_configs():
    """Create sample configuration files for different task packs"""

    # Messy Data Kit config
    messy_data_config = {
        "pack_name": "Messy Data Kit",
        "sponsor": "Rox.ai",
        "tools_enabled": [
            "data.infer_schema",
            "data.clean",
            "records.dedupe",
            "records.resolve_conflicts",
            "validate.report"
        ],
        "default_params": {
            "confidence_threshold": 0.8,
            "dedup_strategy": "fuzzy_matching",
            "conflict_resolution": "llm_assisted"
        },
        "carbon_budget_gco2": 100,
        "demo_available": True
    }

    # Voice-to-Action config
    voice_config = {
        "pack_name": "Voice-to-Action",
        "sponsor": "Wispr",
        "tools_enabled": [
            "voice.stt",
            "intent.detect",
            "planner.from_voice",
            "ui.confirm_and_run"
        ],
        "default_params": {
            "stt_engine": "whisper_large",
            "language": "en",
            "confidence_threshold": 0.85
        },
        "carbon_budget_gco2": 50,
        "demo_available": True
    }

    # Save configurations
    configs_dir = Path("task_packs/configs")
    configs_dir.mkdir(parents=True, exist_ok=True)

    (configs_dir / "messy_data_kit.json").write_text(json.dumps(messy_data_config, indent=2))
    (configs_dir / "voice_to_action.json").write_text(json.dumps(voice_config, indent=2))

    print(f"📁 Created sample configs in {configs_dir}/")

if __name__ == "__main__":
    showcase_task_agnostic_capabilities()
    create_sample_configs()
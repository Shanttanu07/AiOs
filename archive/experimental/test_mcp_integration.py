# test_mcp_integration.py - Demonstrate MCP Server Integration
import asyncio
import json
from pathlib import Path
from aiox.kernel.mcp_registry import MCPToolRegistry
from aiox.compiler.dynamic_schema import DynamicAPLSchema


async def demo_mcp_integration():
    """Demonstrate real-time MCP tool discovery and integration"""

    print("MCP Server Integration Demo")
    print("=" * 50)

    # Initialize MCP-enabled tool registry
    tools_root = Path("tools")
    mcp_registry = MCPToolRegistry(tools_root, Path("mcp_servers.json"))

    print("\n1. Loading MCP server configurations...")
    mcp_registry.load_mcp_config()

    # Show configured servers
    servers_status = mcp_registry.get_mcp_servers_status()
    print(f"\nServers Configured MCP Servers ({len(servers_status)}):")
    for server_id, status in servers_status.items():
        enabled_status = "ENABLED Enabled" if status["enabled"] else "DISABLED Disabled"
        print(f"   {status['name']}: {enabled_status}")
        print(f"     URL: {status['url']}")
        print(f"     Prefix: {server_id}_")
        print(f"     Capabilities: {', '.join(status['capabilities'])}")
        print()

    print("2. Discovering local tools...")
    local_count = len([t for t in mcp_registry.list_tools() if not t.category.startswith("mcp_")])

    print(f"3. Simulating MCP tool discovery...")
    # Simulate discovered MCP tools since we don't have actual MCP servers running
    simulated_mcp_tools = simulate_mcp_discovery(mcp_registry)

    total_tools = local_count + simulated_mcp_tools
    print(f"\nTools Total Tools Available: {total_tools}")
    print(f"   Local Tools: {local_count}")
    print(f"   MCP Tools: {simulated_mcp_tools}")

    print("\n4. Generating dynamic APL schema with MCP support...")
    schema_gen = DynamicAPLSchema(mcp_registry)
    schema = schema_gen.generate_schema()

    operations = schema['$defs']['step']['properties']['op']['enum']
    capabilities = schema['properties']['capabilities']['items']['enum']

    print(f"   APL Operations: {len(operations)} (includes MCP tools)")
    print(f"   Capabilities: {len(capabilities)} (includes MCP capabilities)")

    # Show MCP operations
    mcp_operations = [op for op in operations if any(op.startswith(f"{server_id}_") for server_id in servers_status.keys())]
    if mcp_operations:
        print(f"\nMCP MCP Operations ({len(mcp_operations)}):")
        for op in mcp_operations[:10]:  # Show first 10
            print(f"   - {op}")
        if len(mcp_operations) > 10:
            print(f"   ... and {len(mcp_operations) - 10} more")

    print("\n5. Demo APL Plans with MCP Integration:")
    demo_plans = [
        "apps/forge/mcp_calendar_demo.apl.json",
        "apps/forge/mcp_cross_platform_demo.apl.json"
    ]

    for plan_path in demo_plans:
        if Path(plan_path).exists():
            with open(plan_path) as f:
                plan = json.load(f)

            print(f"\n   Plan {plan['goal']}")
            mcp_ops = [step['op'] for step in plan['steps'] if any(step['op'].startswith(f"{s}_") for s in servers_status.keys())]
            if mcp_ops:
                print(f"      MCP Operations: {', '.join(mcp_ops)}")
            print(f"      Capabilities: {', '.join(plan['capabilities'])}")

    print("\nENABLED MCP Integration Architecture Complete!")
    print("\nKey Features:")
    print("   * Real-time tool discovery from MCP servers")
    print("   Servers WebSocket connections to external applications")
    print("   Tools Dynamic APL schema expansion")
    print("   * Cross-platform workflow automation")
    print("   * Live tool registry updates")

    return mcp_registry


def simulate_mcp_discovery(mcp_registry: MCPToolRegistry) -> int:
    """Simulate MCP tool discovery for demo purposes"""
    simulated_tools = []

    # Google Calendar tools
    simulated_tools.extend([
        {"name": "gcal_get_events", "category": "mcp_google_calendar", "description": "Get calendar events"},
        {"name": "gcal_create_event", "category": "mcp_google_calendar", "description": "Create calendar event"},
        {"name": "gcal_update_event", "category": "mcp_google_calendar", "description": "Update calendar event"},
        {"name": "gcal_delete_event", "category": "mcp_google_calendar", "description": "Delete calendar event"},
    ])

    # Gmail tools
    simulated_tools.extend([
        {"name": "gmail_search_emails", "category": "mcp_gmail", "description": "Search emails"},
        {"name": "gmail_send_email", "category": "mcp_gmail", "description": "Send email"},
        {"name": "gmail_get_thread", "category": "mcp_gmail", "description": "Get email thread"},
    ])

    # Slack tools
    simulated_tools.extend([
        {"name": "slack_get_messages", "category": "mcp_slack", "description": "Get channel messages"},
        {"name": "slack_send_message", "category": "mcp_slack", "description": "Send message"},
        {"name": "slack_get_channels", "category": "mcp_slack", "description": "List channels"},
    ])

    # Notion tools
    simulated_tools.extend([
        {"name": "notion_create_page", "category": "mcp_notion", "description": "Create Notion page"},
        {"name": "notion_search_pages", "category": "mcp_notion", "description": "Search Notion pages"},
        {"name": "notion_update_page", "category": "mcp_notion", "description": "Update Notion page"},
    ])

    # Add simulated tools to registry (simplified for demo)
    for tool_data in simulated_tools:
        from aiox.kernel.tools import ToolSpec
        tool_spec = ToolSpec(
            name=tool_data["name"],
            version="1.0.0",
            description=tool_data["description"],
            category=tool_data["category"],
            inputs={"input": {"type": "object", "description": "Tool input"}},
            outputs={"result": {"type": "object", "description": "Tool result"}},
            capabilities=["mcp.call"],
            implementation=f"mcp:simulated:{tool_data['name']}",
            manifest_path=Path(f"mcp://simulated/{tool_data['name']}")
        )
        mcp_registry.tools[tool_data["name"]] = tool_spec
        mcp_registry.mcp_tools[tool_data["name"]] = tool_spec

    return len(simulated_tools)


if __name__ == "__main__":
    asyncio.run(demo_mcp_integration())
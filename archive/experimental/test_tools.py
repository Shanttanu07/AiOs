#!/usr/bin/env python3
"""Test tool discovery and basic functionality"""

from pathlib import Path
from aiox.kernel.tools import ToolRegistry

def test_tool_discovery():
    print("Testing tool discovery...")

    tools_root = Path("tools")
    registry = ToolRegistry(tools_root)

    count = registry.discover_tools()
    print(f"Discovered {count} tools")

    # List all tools
    tools = registry.list_tools()
    for tool in tools:
        print(f"  - {tool.name} ({tool.category}): {tool.description}")

    # Test tool categories
    data_tools = registry.get_tools_by_category("data")
    ml_tools = registry.get_tools_by_category("ml")

    print(f"\nData tools: {[t.name for t in data_tools]}")
    print(f"ML tools: {[t.name for t in ml_tools]}")

    # Test capability requirements
    caps = registry.get_required_capabilities(["read_csv", "emit_report"])
    print(f"Required capabilities: {caps}")

if __name__ == "__main__":
    test_tool_discovery()
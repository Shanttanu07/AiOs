# aiox/compiler/dynamic_schema.py - Dynamic APL Schema Generation
from __future__ import annotations
import json
from typing import Dict, Any, List, Set
from ..kernel.tools import ToolRegistry
from ..kernel.mcp_registry import MCPToolRegistry


class DynamicAPLSchema:
    """Generate APL schema dynamically from discovered tools"""

    def __init__(self, tools_registry: ToolRegistry):
        self.tools = tools_registry
        self.is_mcp_registry = isinstance(tools_registry, MCPToolRegistry)

    def generate_schema(self) -> Dict[str, Any]:
        """Generate complete APL JSON schema from discovered tools"""

        # Get all tool names for operation enum
        tool_names = self.tools.get_all_tool_names()

        # Base schema structure
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://aiox/schema/apl.json",
            "title": "Agent Plan Language (APL) - Dynamic",
            "type": "object",
            "required": ["goal", "capabilities", "steps"],
            "additionalProperties": False,
            "properties": {
                "goal": {"type": "string", "minLength": 1},
                "capabilities": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "string",
                        "enum": self._get_all_capabilities()
                    },
                    "uniqueItems": True
                },
                "inputs": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                },
                "triggers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {"type": "string"},
                            "path": {"type": "string"},
                            "cron": {"type": "string"}
                        },
                        "additionalProperties": True
                    }
                },
                "steps": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/step"}
                },
                "verify": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/verifyStep"}
                },
                "rollback": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/rollbackStep"}
                },
                "_generated_at": {"type": "string"}
            },

            "$defs": {
                "ioStringOrMap": {
                    "oneOf": [
                        {"type": "string", "minLength": 1},
                        {"type": "object", "additionalProperties": True}
                    ]
                },

                "step": {
                    "type": "object",
                    "required": ["id", "op"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "op": {
                            "type": "string",
                            "enum": sorted(tool_names)  # DYNAMIC: All discovered tool names
                        },
                        "in": {"$ref": "#/$defs/ioStringOrMap"},
                        "out": {"$ref": "#/$defs/ioStringOrMap"},
                        "args": {"type": "object", "additionalProperties": True},
                        "cond": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "allOf": [
                        {
                            "if": {"properties": {"op": {"const": "guard"}}},
                            "then": {"required": ["cond"]}
                        }
                    ]
                },

                "verifyStep": {
                    "type": "object",
                    "required": ["op"],
                    "additionalProperties": False,
                    "properties": {
                        "op": {
                            "type": "string",
                            "enum": [
                                "verify_zip",
                                "verify_cli_predicts",
                                "verify_file_exists",
                                "verify_nonempty"
                            ]
                        },
                        "target": {"type": "string"},
                        "args": {"type": "object", "additionalProperties": True}
                    }
                },

                "rollbackStep": {
                    "type": "object",
                    "required": ["op"],
                    "additionalProperties": False,
                    "properties": {
                        "op": {"type": "string", "enum": ["delete", "move_back"]},
                        "target": {"type": "string"},
                        "from": {"type": "string"},
                        "to": {"type": "string"}
                    }
                }
            }
        }

        return schema

    def _get_all_capabilities(self) -> List[str]:
        """Get all capabilities from discovered tools"""
        capabilities: Set[str] = set()

        for tool in self.tools.list_tools():
            capabilities.update(tool.capabilities)

        # Add standard system capabilities
        capabilities.update([
            "fs.read", "fs.write", "proc.spawn",
            "net.get", "ocr.run", "table.extract", "model.call"
        ])

        # Add MCP capabilities if using MCP registry
        if self.is_mcp_registry:
            capabilities.update([
                "mcp.call", "calendar.read", "calendar.write",
                "email.read", "email.send", "notion.read", "notion.write",
                "slack.messages", "crm.read", "project.read"
            ])

        return sorted(list(capabilities))

    def get_tool_operation_mapping(self) -> Dict[str, str]:
        """Get mapping of tool names to their APL operations (1:1 now)"""
        mapping = {}
        for tool_name in self.tools.get_all_tool_names():
            mapping[tool_name] = tool_name  # Direct mapping: tool name = operation name
        return mapping

    def get_tools_by_category_for_llm(self) -> Dict[str, List[str]]:
        """Get categorized tool list for LLM prompt generation"""
        categories = {}

        for tool in self.tools.list_tools():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool.name)

        return categories

    def save_dynamic_schema(self, output_path: str) -> None:
        """Save the generated dynamic schema to file"""
        schema = self.generate_schema()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, sort_keys=True)
        print(f"[schema] Dynamic APL schema saved to {output_path}")
        print(f"[schema] Schema supports {len(schema['$defs']['step']['properties']['op']['enum'])} operations")
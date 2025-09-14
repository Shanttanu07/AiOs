# aiox/kernel/mcp_registry.py - MCP Server Integration for Real-time Tool Discovery
from __future__ import annotations
import json
import asyncio
import websockets
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
from .tools import ToolRegistry, ToolSpec
import logging

logger = logging.getLogger(__name__)


@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    url: str
    auth_token: Optional[str] = None
    enabled: bool = True
    capabilities: List[str] = None
    tools_prefix: Optional[str] = None  # e.g., "gcal_" for Google Calendar tools


class MCPToolRegistry(ToolRegistry):
    """Extended ToolRegistry with real-time MCP server integration"""

    def __init__(self, tools_root: Path, mcp_config_path: Optional[Path] = None):
        super().__init__(tools_root)
        self.mcp_servers: Dict[str, MCPServer] = {}
        self.mcp_tools: Dict[str, ToolSpec] = {}  # Tools from MCP servers
        self.mcp_config_path = mcp_config_path or Path("mcp_servers.json")
        self._websocket_connections: Dict[str, Any] = {}

    def load_mcp_config(self) -> None:
        """Load MCP server configurations"""
        if not self.mcp_config_path.exists():
            # Create default config
            default_config = {
                "servers": {
                    "google_calendar": {
                        "name": "Google Calendar",
                        "url": "ws://localhost:3001/mcp",
                        "auth_token": None,
                        "enabled": True,
                        "capabilities": ["calendar.read", "calendar.write", "calendar.events"],
                        "tools_prefix": "gcal_"
                    },
                    "gmail": {
                        "name": "Gmail",
                        "url": "ws://localhost:3002/mcp",
                        "auth_token": None,
                        "enabled": False,
                        "capabilities": ["email.read", "email.send", "email.search"],
                        "tools_prefix": "gmail_"
                    },
                    "notion": {
                        "name": "Notion",
                        "url": "ws://localhost:3003/mcp",
                        "auth_token": None,
                        "enabled": False,
                        "capabilities": ["notion.read", "notion.write", "notion.search"],
                        "tools_prefix": "notion_"
                    },
                    "slack": {
                        "name": "Slack",
                        "url": "ws://localhost:3004/mcp",
                        "auth_token": None,
                        "enabled": False,
                        "capabilities": ["slack.messages", "slack.channels", "slack.users"],
                        "tools_prefix": "slack_"
                    }
                }
            }
            with open(self.mcp_config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"[mcp] Created default MCP config at {self.mcp_config_path}")

        with open(self.mcp_config_path) as f:
            config = json.load(f)

        for server_id, server_config in config.get("servers", {}).items():
            self.mcp_servers[server_id] = MCPServer(**server_config)

        print(f"[mcp] Loaded {len(self.mcp_servers)} MCP server configurations")

    async def discover_mcp_tools(self) -> int:
        """Discover tools from enabled MCP servers"""
        discovered_count = 0

        for server_id, server in self.mcp_servers.items():
            if not server.enabled:
                continue

            try:
                tools_count = await self._discover_from_server(server_id, server)
                discovered_count += tools_count
                print(f"[mcp] Discovered {tools_count} tools from {server.name}")

            except Exception as e:
                print(f"[mcp] Failed to connect to {server.name}: {e}")

        print(f"[mcp] Total MCP tools discovered: {discovered_count}")
        return discovered_count

    async def _discover_from_server(self, server_id: str, server: MCPServer) -> int:
        """Discover tools from a single MCP server"""
        try:
            # Connect to MCP server via WebSocket
            headers = {}
            if server.auth_token:
                headers["Authorization"] = f"Bearer {server.auth_token}"

            async with websockets.connect(
                server.url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                self._websocket_connections[server_id] = websocket

                # Send MCP discovery request
                discovery_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }

                await websocket.send(json.dumps(discovery_request))
                response = await websocket.recv()
                result = json.loads(response)

                if "result" not in result:
                    raise Exception(f"Invalid MCP response: {result}")

                tools_data = result["result"].get("tools", [])
                return self._register_mcp_tools(server_id, server, tools_data)

        except Exception as e:
            logger.error(f"MCP discovery failed for {server.name}: {e}")
            raise

    def _register_mcp_tools(self, server_id: str, server: MCPServer, tools_data: List[Dict]) -> int:
        """Register tools discovered from MCP server"""
        count = 0

        for tool_data in tools_data:
            try:
                # Convert MCP tool format to ToolSpec
                tool_name = tool_data["name"]
                if server.tools_prefix:
                    tool_name = f"{server.tools_prefix}{tool_name}"

                # Convert MCP schema to ToolSpec format
                inputs = {}
                outputs = {}

                # Parse MCP tool schema
                if "inputSchema" in tool_data:
                    schema = tool_data["inputSchema"]
                    if "properties" in schema:
                        for prop_name, prop_def in schema["properties"].items():
                            inputs[prop_name] = {
                                "type": prop_def.get("type", "string"),
                                "description": prop_def.get("description", ""),
                                "required": prop_name in schema.get("required", [])
                            }

                # MCP tools typically return unstructured results
                outputs["result"] = {
                    "type": "object",
                    "description": "Tool execution result"
                }

                tool_spec = ToolSpec(
                    name=tool_name,
                    version="1.0.0",
                    description=tool_data.get("description", f"MCP tool from {server.name}"),
                    category=f"mcp_{server_id}",
                    inputs=inputs,
                    outputs=outputs,
                    capabilities=server.capabilities or ["mcp.call"],
                    implementation=f"mcp:{server_id}:{tool_data['name']}",  # Special MCP implementation
                    manifest_path=Path(f"mcp://{server_id}/{tool_data['name']}")
                )

                # Register in both MCP tools and main registry
                self.mcp_tools[tool_name] = tool_spec
                self.tools[tool_name] = tool_spec
                count += 1

            except Exception as e:
                logger.error(f"Failed to register MCP tool {tool_data.get('name', 'unknown')}: {e}")

        return count

    async def call_mcp_tool(self, tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP tool via WebSocket"""
        tool_spec = self.mcp_tools.get(tool_name)
        if not tool_spec:
            raise RuntimeError(f"MCP tool not found: {tool_name}")

        # Parse implementation to get server and original tool name
        impl_parts = tool_spec.implementation.split(":")
        if len(impl_parts) != 3 or impl_parts[0] != "mcp":
            raise RuntimeError(f"Invalid MCP tool implementation: {tool_spec.implementation}")

        server_id, original_tool_name = impl_parts[1], impl_parts[2]

        websocket = self._websocket_connections.get(server_id)
        if not websocket:
            raise RuntimeError(f"No active connection to MCP server: {server_id}")

        # Send MCP tool call request
        request = {
            "jsonrpc": "2.0",
            "id": asyncio.current_task().get_name() if asyncio.current_task() else "mcp_call",
            "method": "tools/call",
            "params": {
                "name": original_tool_name,
                "arguments": inputs
            }
        }

        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        result = json.loads(response)

        if "error" in result:
            raise RuntimeError(f"MCP tool error: {result['error']}")

        return result.get("result", {})

    def discover_tools(self) -> int:
        """Enhanced discovery including both local and MCP tools"""
        # First discover local tools
        local_count = super().discover_tools()

        # Then discover MCP tools asynchronously
        try:
            self.load_mcp_config()
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, schedule the discovery
                task = asyncio.create_task(self.discover_mcp_tools())
                mcp_count = 0  # Will be updated when task completes
            else:
                # Run the async discovery
                mcp_count = loop.run_until_complete(self.discover_mcp_tools())
        except Exception as e:
            print(f"[mcp] MCP discovery failed: {e}")
            mcp_count = 0

        total_count = local_count + mcp_count
        print(f"[registry] Total tools: {total_count} ({local_count} local + {mcp_count} MCP)")
        return total_count

    def get_mcp_servers_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all MCP servers"""
        status = {}
        for server_id, server in self.mcp_servers.items():
            mcp_tools_count = len([t for t in self.mcp_tools.values() if t.category == f"mcp_{server_id}"])
            status[server_id] = {
                "name": server.name,
                "url": server.url,
                "enabled": server.enabled,
                "connected": server_id in self._websocket_connections,
                "tools_discovered": mcp_tools_count,
                "capabilities": server.capabilities
            }
        return status

    async def refresh_mcp_tools(self, server_id: Optional[str] = None) -> int:
        """Refresh tools from specific MCP server or all servers"""
        if server_id:
            servers_to_refresh = [server_id] if server_id in self.mcp_servers else []
        else:
            servers_to_refresh = list(self.mcp_servers.keys())

        total_refreshed = 0
        for sid in servers_to_refresh:
            server = self.mcp_servers[sid]
            if server.enabled:
                try:
                    count = await self._discover_from_server(sid, server)
                    total_refreshed += count
                    print(f"[mcp] Refreshed {count} tools from {server.name}")
                except Exception as e:
                    print(f"[mcp] Failed to refresh {server.name}: {e}")

        return total_refreshed

    async def close_mcp_connections(self):
        """Close all MCP WebSocket connections"""
        for server_id, websocket in self._websocket_connections.items():
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing MCP connection {server_id}: {e}")
        self._websocket_connections.clear()
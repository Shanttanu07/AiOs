# Real-Time MCP Server Integration Architecture

## ✅ Dynamic Tool Registry with MCP Support

The AI-OS now supports **real-time tool discovery** from Model Context Protocol (MCP) servers, enabling seamless integration with external applications like Google Calendar, Gmail, Slack, Notion, and more.

## 🏗️ Architecture Overview

### 1. **MCPToolRegistry** - Extended Tool Discovery
```python
class MCPToolRegistry(ToolRegistry):
    """Extended ToolRegistry with real-time MCP server integration"""

    # Discovers tools from:
    # - Local files (tool.json & spec.json)
    # - MCP servers via WebSocket connections
    # - Real-time updates when servers come online
```

### 2. **Dynamic Schema Generation**
The APL schema automatically expands to include MCP tools:
- **Local Tools**: 14 operations from file system
- **MCP Tools**: Unlimited operations from connected servers
- **Total Capabilities**: Combines local + MCP capabilities

### 3. **WebSocket MCP Protocol**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {}
}
```

## 🔧 Configured MCP Servers

| Server | URL | Prefix | Status | Capabilities |
|--------|-----|--------|--------|-------------|
| **Google Calendar** | `ws://localhost:3001/mcp` | `gcal_` | ✅ Enabled | calendar.read, calendar.write |
| **Gmail** | `ws://localhost:3002/mcp` | `gmail_` | ✅ Enabled | email.read, email.send |
| **Slack** | `ws://localhost:3004/mcp` | `slack_` | ✅ Enabled | slack.messages, slack.channels |
| **Notion** | `ws://localhost:3003/mcp` | `notion_` | ✅ Enabled | notion.read, notion.write |
| **Salesforce** | `ws://localhost:3005/mcp` | `sf_` | ❌ Disabled | crm.read, crm.write |
| **Jira** | `ws://localhost:3006/mcp` | `jira_` | ❌ Disabled | project.read, project.write |

## 🎯 Example MCP-Powered Workflows

### Calendar Productivity Analysis
```json
{
  "goal": "Analyze calendar data and generate productivity insights",
  "steps": [
    {"op": "gcal_get_events", "in": {"start_date": "2025-01-01"}},
    {"op": "business_insights", "in": {"focus_areas": ["productivity"]}},
    {"op": "emit_report"}
  ]
}
```

### Cross-Platform Automation
```json
{
  "goal": "Cross-platform workflow automation",
  "steps": [
    {"op": "gmail_search_emails", "in": {"query": "is:important"}},
    {"op": "slack_get_messages", "in": {"channel": "#general"}},
    {"op": "business_insights", "in": {"focus_areas": ["communication"]}},
    {"op": "notion_create_page", "in": {"title": "Weekly Summary"}},
    {"op": "gmail_send_email", "in": {"to": ["team@company.com"]}}
  ]
}
```

## 🚀 Real-Time Features

### **Live Tool Discovery**
```python
# Tools are discovered in real-time as MCP servers connect
await mcp_registry.discover_mcp_tools()  # Scans all enabled servers
await mcp_registry.refresh_mcp_tools("gmail")  # Refresh specific server
```

### **Dynamic APL Expansion**
- **Before**: 14 operations (local tools only)
- **After**: 27+ operations (local + MCP tools)
- **Schema**: Automatically includes MCP capabilities and operations

### **WebSocket Connections**
- Persistent connections to MCP servers
- Real-time tool execution via WebSocket protocol
- Automatic reconnection and error handling

## 🔄 Integration Benefits

### **Unlimited Extensibility**
- Connect to any MCP-compatible application
- Tools appear automatically in APL schema
- No code changes required for new integrations

### **Enterprise Ready**
- Secure WebSocket connections with auth tokens
- Configurable server endpoints and capabilities
- Production-ready error handling and reconnection

### **Task-Agnostic Workflows**
- Combine local AI tools with external APIs
- Cross-platform data flows (Email → Slack → Notion)
- Unified automation language (APL) for all tools

## 📊 Demo Results

**Tool Registry Status:**
- Local Tools: 14 operations
- MCP Tools: 13+ operations (simulated)
- Total Operations: 27+
- Capabilities: 17 (including MCP capabilities)

**MCP Operations Discovered:**
- `gmail_search_emails`, `gmail_send_email`, `gmail_get_thread`
- `slack_get_messages`, `slack_send_message`, `slack_get_channels`
- `notion_create_page`, `notion_search_pages`, `notion_update_page`
- `gcal_get_events`, `gcal_create_event`, `gcal_update_event`

## ✅ Architecture Achievement

The **APL Schema as the Moat** now extends beyond local tools to include **real-time integration with any MCP-compatible application**. This creates an unlimited expansion capability where:

1. **New Applications** automatically become available as APL operations
2. **External APIs** integrate seamlessly with local AI tools
3. **Cross-Platform Workflows** execute through unified APL language
4. **Enterprise Integration** scales to any number of connected services

The system transforms from a static 14-operation platform to a **dynamic, infinitely extensible automation architecture** that grows with every connected MCP server.
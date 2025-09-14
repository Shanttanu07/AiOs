# kernel/tools.py - Tool Registry and Dynamic Discovery
from __future__ import annotations
import json
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass


@dataclass
class ToolSpec:
    """Tool specification from tool.json"""
    name: str
    version: str
    description: str
    category: str
    inputs: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    capabilities: List[str]
    implementation: str
    manifest_path: Path


class ToolRegistry:
    """Registry for dynamic tool discovery and loading"""

    def __init__(self, tools_root: Path):
        self.tools_root = tools_root
        self.tools: Dict[str, ToolSpec] = {}
        self.loaded_modules: Dict[str, Any] = {}

    def discover_tools(self) -> int:
        """Scan tools directory and load manifests"""
        discovered = 0

        if not self.tools_root.exists():
            return discovered

        # Find all tool.json files
        for tool_json in self.tools_root.rglob("tool.json"):
            try:
                manifest = json.loads(tool_json.read_text(encoding="utf-8"))

                # Validate required fields
                required = ["name", "version", "description", "category", "inputs", "outputs", "capabilities", "implementation"]
                if not all(field in manifest for field in required):
                    print(f"[tools] Invalid manifest: {tool_json} (missing required fields)")
                    continue

                spec = ToolSpec(
                    name=manifest["name"],
                    version=manifest["version"],
                    description=manifest["description"],
                    category=manifest["category"],
                    inputs=manifest["inputs"],
                    outputs=manifest["outputs"],
                    capabilities=manifest["capabilities"],
                    implementation=manifest["implementation"],
                    manifest_path=tool_json
                )

                self.tools[spec.name] = spec
                discovered += 1

            except Exception as e:
                print(f"[tools] Failed to load manifest {tool_json}: {e}")

        print(f"[tools] Discovered {discovered} tools")
        return discovered

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """Get tool specification by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[ToolSpec]:
        """List all discovered tools"""
        return list(self.tools.values())

    def get_tools_by_category(self, category: str) -> List[ToolSpec]:
        """Get tools filtered by category"""
        return [tool for tool in self.tools.values() if tool.category == category]

    def get_required_capabilities(self, tool_names: List[str]) -> Set[str]:
        """Get all capabilities required by a list of tools"""
        capabilities = set()
        for name in tool_names:
            tool = self.get_tool(name)
            if tool:
                capabilities.update(tool.capabilities)
        return capabilities

    def load_tool_module(self, tool_name: str) -> Optional[Any]:
        """Dynamically load tool implementation module"""
        if tool_name in self.loaded_modules:
            return self.loaded_modules[tool_name]

        tool = self.get_tool(tool_name)
        if not tool:
            return None

        try:
            # Convert relative path to absolute
            impl_path = self.tools_root.parent / tool.implementation

            if not impl_path.exists():
                print(f"[tools] Implementation not found: {impl_path}")
                return None

            # Load module dynamically
            spec = importlib.util.spec_from_file_location(f"tool_{tool_name}", impl_path)
            if spec is None or spec.loader is None:
                print(f"[tools] Failed to create module spec for {tool_name}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.loaded_modules[tool_name] = module
            return module

        except Exception as e:
            print(f"[tools] Failed to load tool {tool_name}: {e}")
            return None

    def call_tool(self, tool_name: str, inputs: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """Call a tool with given inputs"""
        module = self.load_tool_module(tool_name)
        if not module:
            raise RuntimeError(f"Tool not found or failed to load: {tool_name}")

        if not hasattr(module, 'execute'):
            raise RuntimeError(f"Tool {tool_name} missing execute() function")

        try:
            # Call the tool's execute function
            result = module.execute(inputs, context)
            return result if isinstance(result, dict) else {"result": result}

        except Exception as e:
            raise RuntimeError(f"Tool {tool_name} execution failed: {e}")

    def validate_tool_inputs(self, tool_name: str, inputs: Dict[str, Any]) -> List[str]:
        """Validate inputs against tool specification"""
        tool = self.get_tool(tool_name)
        if not tool:
            return [f"Tool not found: {tool_name}"]

        errors = []

        # Check required inputs
        for input_name, input_spec in tool.inputs.items():
            if input_name not in inputs:
                if "default" not in input_spec:
                    errors.append(f"Missing required input: {input_name}")
            else:
                # Basic type checking could go here
                pass

        # Check for unexpected inputs
        expected_inputs = set(tool.inputs.keys())
        actual_inputs = set(inputs.keys())
        unexpected = actual_inputs - expected_inputs

        if unexpected:
            errors.append(f"Unexpected inputs: {', '.join(unexpected)}")

        return errors
# aiox/planner/llm_planner.py - LLM-based task-agnostic planning
from __future__ import annotations
import os
import json
import getpass
import time
from typing import Dict, Any, List, Optional, Set
import anthropic
from .core import ExecutionPlan, PlanStep
from ..kernel.tools import ToolRegistry
from ..kernel.model_cache import ModelCallCache
from ..kernel.replay_gate import ReplayGate


class APIKeyManager:
    """Secure API key management"""

    @staticmethod
    def get_claude_api_key() -> Optional[str]:
        """Get Claude API key from environment or user input"""
        # Try environment variable first
        api_key = "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"
        # os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            return api_key

        api_key = os.getenv('CLAUDE_API_KEY')  # Alternative env var
        if api_key:
            return api_key

        # Prompt user securely
        try:
            print("Claude API key not found in environment variables.")
            print("Please set ANTHROPIC_API_KEY or CLAUDE_API_KEY, or enter it now:")
            api_key = getpass.getpass("Claude API Key: ").strip()
            return api_key if api_key else None
        except (KeyboardInterrupt, EOFError):
            print("\nAPI key input cancelled.")
            return None


class LLMPlanner:
    """LLM-based task-agnostic workflow planner with caching"""

    def __init__(self, tools_registry: ToolRegistry, sandbox_root=None):
        self.tools = tools_registry
        self._client = None
        self.sandbox_root = sandbox_root or "sandbox"
        self.cache = ModelCallCache(self.sandbox_root)
        self.replay_gate = ReplayGate(self.sandbox_root)

    def _get_client(self) -> anthropic.Anthropic:
        """Get Anthropic client with API key"""
        if self._client is None:
            api_key = APIKeyManager.get_claude_api_key()
            if not api_key:
                raise RuntimeError("Claude API key is required for LLM-based planning")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _get_tools_context(self) -> str:
        """Generate tools context for LLM"""
        tools_info = []
        tools_info.append("Available Tools:")

        for tool in self.tools.list_tools():
            inputs_desc = []
            for name, spec in tool.inputs.items():
                type_info = spec.get('type', 'any')
                desc = spec.get('description', '')
                inputs_desc.append(f"{name} ({type_info}): {desc}")

            outputs_desc = []
            for name, spec in tool.outputs.items():
                type_info = spec.get('type', 'any')
                desc = spec.get('description', '')
                outputs_desc.append(f"{name} ({type_info}): {desc}")

            tools_info.append(f"\n- {tool.name} ({tool.category})")
            tools_info.append(f"  Description: {tool.description}")
            tools_info.append(f"  Inputs: {', '.join(inputs_desc) if inputs_desc else 'none'}")
            tools_info.append(f"  Outputs: {', '.join(outputs_desc) if outputs_desc else 'none'}")
            tools_info.append(f"  Capabilities: {', '.join(tool.capabilities)}")

        return "\n".join(tools_info)

    def plan_workflow(self, goal: str, **kwargs) -> ExecutionPlan:
        """Use LLM to plan workflow for any goal"""
        client = self._get_client()
        tools_context = self._get_tools_context()

        # Extract any provided parameters
        context_info = []
        if kwargs:
            context_info.append("Additional Context:")
            for key, value in kwargs.items():
                if value is not None:
                    context_info.append(f"- {key}: {value}")

        context_str = "\n".join(context_info) if context_info else ""

        prompt = f"""You are an AI workflow planner for a task-agnostic automation system. Your job is to analyze a user's goal and create an execution plan using available tools.

{tools_context}

{context_str}

User Goal: {goal}

CRITICAL: Your response will be converted to APL (Agent Plan Language) format. You MUST use only these exact operation names:
- load_csv (for reading CSV files)
- profile_schema (for data analysis/profiling)
- split_deterministic (for data splitting)
- train_linear (for training models)
- eval_metrics (for model evaluation)
- emit_report (for generating reports)
- build_cli (for building CLI tools)
- bundle_zip (for creating zip files)
- guard (for assertions/conditions)

Please create a step-by-step execution plan and respond with ONLY a JSON object with this exact structure:
{{
  "goal_analysis": {{
    "intent": "brief description of what user wants",
    "complexity": "low|medium|high",
    "task_type": "data_processing|analysis|ml|visualization|research|file_ops|web|general"
  }},
  "steps": [
    {{
      "id": "step1",
      "tool": "exact_apl_operation_name",
      "description": "what this step does",
      "inputs": {{"param": "value or $variable"}},
      "outputs": {{"result_name": "$variable_name"}}
    }}
  ],
  "inputs": {{"main_input": "expected input file or data"}},
  "outputs": {{"final_result": "expected output location"}},
  "capabilities": ["fs.read", "fs.write", "proc.spawn"]
}}

Important constraints:
- ONLY use the exact APL operation names listed above
- Use $ variables to connect outputs from one step to inputs of the next
- For file paths, use sandbox/in/ for inputs and sandbox/out/ for outputs
- Do not add extra fields like "cleanup", "guards", or "_planner_metadata"
- Keep the response as clean JSON only"""

        try:
            model_name = "claude-3-5-haiku-20241022"

            # Prepare inputs for caching
            model_inputs = {
                "model": model_name,
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }

            # Check replay gate and cache
            replay_allowed, replay_result = self.replay_gate.check_model_call(model_name, model_inputs)

            if not replay_allowed:
                raise RuntimeError("Model call not allowed during deterministic replay (missing from cache)")

            if replay_result:
                print("[planner] Using cached LLM response (replay mode)")
                response_text = replay_result.get("response_text", "")
            else:
                print("[planner] Making LLM API call...")
                start_time = time.time()

                response = client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )

                response_text = response.content[0].text
                latency_ms = (time.time() - start_time) * 1000

                # Store in cache
                if self.cache:
                    # Extract token usage if available
                    token_usage = None
                    if hasattr(response, 'usage') and response.usage:
                        token_usage = {
                            "input": response.usage.input_tokens,
                            "output": response.usage.output_tokens
                        }

                    model_outputs = {
                        "response_text": response_text,
                        "usage": token_usage
                    }

                    self.cache.store_result(
                        model_name,
                        model_inputs,
                        model_outputs,
                        latency_ms,
                        token_usage
                    )

            # Extract JSON from response (in case LLM adds explanation)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in LLM response")

            plan_data = json.loads(response_text[json_start:json_end])

            return self._convert_llm_plan_to_execution_plan(plan_data, goal)

        except Exception as e:
            # Fallback to simple plan if LLM fails
            print(f"LLM planning failed: {e}")
            print("Falling back to simple generic plan...")
            return self._create_fallback_plan(goal, **kwargs)

    def _convert_llm_plan_to_execution_plan(self, plan_data: Dict[str, Any], original_goal: str) -> ExecutionPlan:
        """Convert LLM response to ExecutionPlan object"""
        goal_analysis = plan_data.get("goal_analysis", {})

        # Convert steps
        steps = []
        for step_data in plan_data.get("steps", []):
            step = PlanStep(
                id=step_data.get("id", f"step{len(steps)+1}"),
                tool=step_data.get("tool", "unknown"),
                inputs=step_data.get("inputs", {}),
                outputs=step_data.get("outputs", {}),
                description=step_data.get("description", "")
            )
            steps.append(step)

        # Collect capabilities from selected tools
        capabilities = set()
        for step in steps:
            tool_spec = self.tools.get_tool(step.tool)
            if tool_spec:
                capabilities.update(tool_spec.capabilities)

        # Add any additional capabilities from the plan
        capabilities.update(plan_data.get("capabilities", []))

        return ExecutionPlan(
            goal=original_goal,
            steps=steps,
            capabilities=capabilities,
            inputs=plan_data.get("inputs", {}),
            outputs=plan_data.get("outputs", {}),
            metadata={
                "planner_type": "llm",
                "goal_analysis": goal_analysis,
                "complexity": goal_analysis.get("complexity", "medium"),
                "task_type": goal_analysis.get("task_type", "general"),
                "intent": goal_analysis.get("intent", ""),
                "llm_model": "claude-3-5-haiku-20241022"
            }
        )

    def _create_fallback_plan(self, goal: str, **kwargs) -> ExecutionPlan:
        """Create a simple fallback plan if LLM fails"""
        # Try to detect if there's a file mentioned
        input_file = None
        for key, value in kwargs.items():
            if key in ['csv', 'input_csv', 'file'] and value:
                input_file = value
                break

        if not input_file:
            # Look for file in goal text
            import re
            file_match = re.search(r'(\w+\.\w+)', goal)
            if file_match:
                input_file = file_match.group(1)

        # Create basic read and analyze steps
        steps = []
        if input_file:
            steps.append(PlanStep(
                id="load",
                tool="read_csv" if input_file.endswith('.csv') else "read_file",
                inputs={"path": f"sandbox/in/{input_file}"},
                outputs={"data": "$data"},
                description=f"Load {input_file}"
            ))

            # Only add profile if the tool exists
            if self.tools.get_tool("profile"):
                steps.append(PlanStep(
                    id="analyze",
                    tool="profile",
                    inputs={"table": "$data"},
                    outputs={"summary": "$summary"},
                    description="Analyze data structure"
                ))

        # Collect capabilities
        capabilities = set()
        for step in steps:
            tool_spec = self.tools.get_tool(step.tool)
            if tool_spec:
                capabilities.update(tool_spec.capabilities)

        return ExecutionPlan(
            goal=goal,
            steps=steps,
            capabilities=capabilities,
            inputs={"file": f"sandbox/in/{input_file}" if input_file else ""},
            outputs={"summary": "sandbox/out/summary.txt"},
            metadata={
                "planner_type": "fallback",
                "complexity": "low",
                "task_type": "general"
            }
        )
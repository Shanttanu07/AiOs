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
        api_key = os.getenv('ANTHROPIC_API_KEY')
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

        # Generate dynamic operation list from discovered tools
        from ..compiler.dynamic_schema import DynamicAPLSchema
        self._schema_gen = DynamicAPLSchema(self.tools)
        self._dynamic_operations = self._schema_gen.get_tools_by_category_for_llm()

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


    def _get_dynamic_operations_prompt(self) -> str:
        """Generate dynamic operations section for LLM prompt"""
        lines = []
        lines.append("AVAILABLE OPERATIONS (from discovered tools):")

        for category, tool_names in self._dynamic_operations.items():
            lines.append(f"\n{category.upper()} OPERATIONS:")
            for tool_name in sorted(tool_names):
                tool = self.tools.get_tool(tool_name)
                if tool:
                    lines.append(f"- {tool_name}: {tool.description}")

        # Add standard operations that are always available
        lines.append("\nSTANDARD OPERATIONS:")
        lines.append("- guard: Assert conditions for validation")

        return "\n".join(lines)

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

        # Get dynamic operations prompt
        operations_prompt = self._get_dynamic_operations_prompt()

        prompt = f"""You are an AI workflow planner for a TASK-AGNOSTIC automation system. Your job is to analyze ANY type of user goal and create an execution plan using available tools.

SUPPORTED TASK CATEGORIES:
- Data Processing & Analysis (any data type: CSV, JSON, text, images)
- Messy Data Resolution & Conflict Resolution
- Business Intelligence & Actionable Insights
- Cross-System Data Validation & Enterprise Integration
- Web Research & Information Gathering
- File Organization & Management (OCR, semantic search, AI understanding)
- Visualization & Dashboard Creation
- Voice-Driven Automation (speech-to-text, intent detection)
- Design & Content Creation
- Financial Analysis & Reporting
- Research & Knowledge Extraction
- Document Processing & Understanding
- General Automation & Workflows

{tools_context}

{context_str}

User Goal: {goal}

CRITICAL: Your response will be converted to APL (Agent Plan Language) format. You MUST use only the operation names from the list below:

{operations_prompt}

ADVANCED OPERATIONS USAGE:
For messy data and business intelligence tasks, you can now use specialized operations:
- resolve_conflicts: For deduplication, conflict resolution, and data reconciliation
- business_insights: For generating actionable business recommendations and risk analysis
- cross_reference: For data validation and consistency checking across systems

IMPORTANT: Be creative and task-agnostic! The goal could be:
- "Research renewable energy trends and create a summary report"
- "Organize my messy file directory using AI"
- "Analyze website traffic data and recommend optimizations"
- "Create a financial dashboard from expense reports"
- "Convert voice commands into automated workflows"
- "Generate design mockups for a mobile app"
- Or any other automation task!

CRITICAL: You must respond with ONLY a JSON object using this EXACT structure:
{{
  "goal_analysis": {{
    "intent": "brief description of what user wants",
    "complexity": "low|medium|high",
    "task_type": "data_processing|analysis|ml|visualization|research|file_ops|web|general"
  }},
  "steps": [
    {{
      "id": "step1",
      "op": "exact_apl_operation_name",
      "description": "what this step does",
      "in": "input_reference_or_$variable",
      "out": "$output_variable_name"
    }}
  ],
  "inputs": {{"main_input": "expected input file or data"}},
  "outputs": {{"final_result": "expected output location"}},
  "capabilities": ["fs.read", "fs.write", "proc.spawn"]
}}

STEP FORMAT EXAMPLE for "Clean and analyze customer database":
{{
  "steps": [
    {{
      "id": "step1",
      "op": "read_csv",
      "description": "Load customer data",
      "in": "sandbox/in/crm_customers.csv",
      "out": "$customer_data"
    }},
    {{
      "id": "step2",
      "op": "resolve_conflicts",
      "description": "Clean and deduplicate customer data",
      "in": {{"crm_data": "$customer_data"}},
      "out": "$clean_data"
    }},
    {{
      "id": "step3",
      "op": "business_insights",
      "description": "Generate actionable business insights",
      "in": {{"customer_data": "$clean_data"}},
      "out": "$insights"
    }}
  ]
}}

CRITICAL OPERATION NAME MAPPING:
- For loading CSV files: use "read_csv" (NOT "load_csv")
- For data profiling/analysis: use "profile" (NOT "profile_schema")
- For ML training: use "train_lr" (NOT "train_linear")
- For model evaluation: use "eval" (NOT "eval_metrics")
- For file compression: use "zip" (NOT "bundle_zip")
- For assertions: use "assert_ge" (NOT "guard")

REQUIREMENTS:
- Use "op" field with exact APL operation names from the discovered tools list
- Every step needs "in" and "out" fields
- Use the most appropriate operation for the task (not limited to basic operations)
- For complex data: use resolve_conflicts for cleaning, business_insights for analysis
- For simple data: use profile for basic analysis, emit_report for simple reports

Important constraints:
- ONLY use operation names from the AVAILABLE OPERATIONS list above
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
            # Use 'op' field from LLM response, not 'tool'
            operation = step_data.get("op", step_data.get("tool", "unknown"))

            # Handle different input formats
            step_inputs = step_data.get("in", step_data.get("inputs", {}))
            if isinstance(step_inputs, str):
                # Convert string input to dict
                if step_inputs.startswith("$"):
                    step_inputs = {"data": step_inputs}
                else:
                    step_inputs = {"input": step_inputs}
            elif not isinstance(step_inputs, dict):
                step_inputs = {"input": step_inputs}

            # Handle different output formats
            step_outputs = step_data.get("out", step_data.get("outputs", {}))
            if isinstance(step_outputs, str):
                # Convert string output to dict
                step_outputs = {"result": step_outputs}
            elif not isinstance(step_outputs, dict):
                step_outputs = {"result": step_outputs}

            step = PlanStep(
                id=step_data.get("id", f"step{len(steps)+1}"),
                tool=operation,  # Use operation name as tool name
                inputs=step_inputs,
                outputs=step_outputs,
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
                outputs={"table": "$data"},  # Use correct output name
                description=f"Load {input_file}"
            ))

            # Only add profile if the tool exists
            if self.tools.get_tool("profile"):
                steps.append(PlanStep(
                    id="analyze",
                    tool="profile",
                    inputs={"table": "$data"},
                    outputs={"schema": "$summary"},  # Use correct output name
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
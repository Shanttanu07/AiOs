# aiox/planner/core.py - Planner/Orchestrator v1 (LLM-based)
from __future__ import annotations
from typing import Dict, Any, List, Set
from dataclasses import dataclass
from ..kernel.tools import ToolRegistry


@dataclass
class PlanStep:
    """A single step in the execution plan"""
    id: str
    tool: str
    inputs: Dict[str, Any]
    outputs: Dict[str, str]
    description: str


@dataclass
class ExecutionPlan:
    """Complete execution plan with metadata"""
    goal: str
    steps: List[PlanStep]
    capabilities: Set[str]
    inputs: Dict[str, str]
    outputs: Dict[str, str]
    metadata: Dict[str, Any]


# Legacy classes removed - Now using LLM-based planning only
# APIKeyManager is now in llm_planner.py to avoid duplication


class PlanGenerator:
    """Generate execution plans using LLM-based planning"""

    def __init__(self, tools_registry: ToolRegistry, sandbox_root=None):
        self.tools = tools_registry
        # Import here to avoid circular imports
        from .llm_planner import LLMPlanner
        self.llm_planner = LLMPlanner(tools_registry, sandbox_root)

    def generate_plan(self, goal: str, input_csv: str = None, target_column: str = None, **kwargs) -> ExecutionPlan:
        """Generate execution plan from natural language goal using LLM"""

        # Prepare context for LLM
        context = {}
        if input_csv:
            context['input_csv'] = input_csv
        if target_column:
            context['target_column'] = target_column
        context.update(kwargs)

        # Use LLM planner for task-agnostic planning
        return self.llm_planner.plan_workflow(goal, **context)
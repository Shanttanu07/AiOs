# aiox/planner/apl_converter.py - Convert ExecutionPlan to APL format
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any, List, Optional
from .core import ExecutionPlan, PlanStep


class APLConverter:
    """Convert ExecutionPlan to APL JSON format"""

    def __init__(self):
        # Map tool names to APL operations (schema compliant ONLY)
        self.tool_to_op = {
            # Data loading operations
            'read_csv': 'load_csv',
            'load_csv': 'load_csv',

            # Data analysis operations
            'profile': 'profile_schema',
            'profile_schema': 'profile_schema',
            'analyze_data': 'profile_schema',

            # Data processing operations
            'split': 'split_deterministic',
            'split_data': 'split_deterministic',
            'split_deterministic': 'split_deterministic',

            # Model training operations
            'train': 'train_linear',
            'train_lr': 'train_linear',
            'train_linear': 'train_linear',
            'train_linear_regression': 'train_linear',
            'train_model': 'train_linear',

            # Model evaluation operations
            'eval': 'eval_metrics',
            'evaluate': 'eval_metrics',
            'eval_metrics': 'eval_metrics',
            'evaluate_model': 'eval_metrics',
            'test_model': 'eval_metrics',

            # Reporting operations
            'report': 'emit_report',
            'emit_report': 'emit_report',
            'emit_markdown_report': 'emit_report',
            'generate_report': 'emit_report',
            'create_report': 'emit_report',

            # CLI building operations
            'build_cli': 'build_cli',
            'build_prediction_cli': 'build_cli',
            'create_cli': 'build_cli',

            # Packaging operations
            'zip': 'bundle_zip',
            'package': 'bundle_zip',
            'bundle_zip': 'bundle_zip',
            'zip_directory': 'bundle_zip',
            'create_package': 'bundle_zip',

            # Assertion/guard operations
            'assert': 'guard',
            'assert_ge': 'guard',
            'assert_metric_ge': 'guard',
            'check': 'guard',
            'guard': 'guard',
            'verify_performance': 'guard',

            # Verification operations (note: these are for verify section, not main steps)
            'verify_zip': 'load_csv',  # Map to safe operation since verify ops go in verify section
            'verify_zip_integrity': 'load_csv',
            'verify_cli': 'load_csv'
        }

    def convert_to_apl(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Convert ExecutionPlan to APL JSON format (schema compliant only)"""

        apl_steps = []
        symbol_map = {}  # Track variable mappings

        for step in plan.steps:
            apl_step = self._convert_step(step, symbol_map)
            if apl_step:  # Only add valid steps
                apl_steps.append(apl_step)

        # Generate APL structure (STRICTLY schema compliant - only allowed fields)
        apl = {
            "goal": plan.goal,
            "capabilities": sorted(list(plan.capabilities)),
            "steps": apl_steps
        }

        # Only add optional fields if they have content and are schema-valid
        if plan.inputs:
            apl["inputs"] = plan.inputs

        # Add _generated_at as it's in the schema (optional field)
        apl["_generated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # IMPORTANT: Do not add any fields that are not in the schema
        # Schema allows: goal, capabilities, steps, inputs, triggers, verify, rollback, _generated_at
        # We do NOT add: guards, cleanup, _planner_metadata, etc.

        return apl

    def _convert_step(self, step: PlanStep, symbol_map: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Convert a single PlanStep to APL step format"""

        # Valid APL operations from schema
        valid_ops = {
            "load_csv", "profile_schema", "split_deterministic",
            "train_linear", "eval_metrics", "emit_report",
            "build_cli", "bundle_zip", "guard"
        }

        # Map tool name to APL operation
        op = self.tool_to_op.get(step.tool, step.tool)

        # Skip steps with invalid operations
        if op not in valid_ops:
            print(f"Warning: Skipping invalid APL operation '{op}' from tool '{step.tool}'")
            return None

        # Process inputs - resolve variable references
        apl_inputs = {}
        apl_args = {}

        for key, value in step.inputs.items():
            if isinstance(value, str) and value.startswith('$'):
                # Variable reference
                var_name = value[1:]  # Remove $
                if var_name in symbol_map:
                    apl_inputs[key] = symbol_map[var_name]
                else:
                    apl_inputs[key] = value  # Keep as-is if not mapped
            else:
                # Literal value or argument
                if key in ['ratio', 'seed', 'threshold']:
                    apl_args[key] = value
                else:
                    apl_inputs[key] = value

        # Process outputs - create variable mappings
        apl_out = None
        if step.outputs:
            # For single output, use the variable name directly
            if len(step.outputs) == 1:
                output_var = list(step.outputs.values())[0]
                if output_var.startswith('$'):
                    output_var = output_var[1:]
                    apl_out = f"${output_var}"
                    symbol_map[output_var] = f"${output_var}"
            else:
                # Multiple outputs - use first one for now
                first_output = list(step.outputs.values())[0]
                if first_output.startswith('$'):
                    output_var = first_output[1:]
                    apl_out = f"${output_var}"
                    symbol_map[output_var] = f"${output_var}"

        # Build APL step (schema compliant only)
        apl_step = {
            "id": step.id,
            "op": op
        }

        # Add description if present
        if step.description:
            apl_step["description"] = step.description

        # Add input specification
        if len(apl_inputs) == 1:
            apl_step["in"] = list(apl_inputs.values())[0]
        elif len(apl_inputs) > 1:
            apl_step["in"] = apl_inputs

        # Add output specification
        if apl_out:
            apl_step["out"] = apl_out

        # Add arguments if present
        if apl_args:
            apl_step["args"] = apl_args

        # Handle special cases for schema compliance
        if op == "guard":
            # For guard operations, we need a condition (required by schema)
            if "threshold" in apl_args:
                threshold = apl_args.pop("threshold")
                field = apl_inputs.get("field", "metric")
                apl_step["cond"] = f"${apl_inputs.get('metrics', 'metrics')}.{field} >= {threshold}"
            elif step.description and "threshold" in step.description:
                apl_step["cond"] = f"$metrics.r2 >= 0.5"  # Default condition
            else:
                apl_step["cond"] = f"$metrics.accuracy >= 0.5"  # Fallback condition

        return apl_step

    def _generate_guards(self, plan: ExecutionPlan) -> List[Dict[str, Any]]:
        """Generate guard conditions for plan validation"""
        guards = []

        # Add quality check if model evaluation is present
        has_eval = any(step.tool == 'eval' for step in plan.steps)
        has_assert = any(step.tool == 'assert_ge' for step in plan.steps)

        if has_eval and not has_assert:
            guards.append({
                "condition": "$metrics.R2 >= 0.6",
                "message": "Model R² must be at least 0.6"
            })

        return guards

    def _generate_cleanup(self, plan: ExecutionPlan) -> List[Dict[str, str]]:
        """Generate cleanup operations for plan artifacts"""
        cleanup = []

        # Standard cleanup for ML pipelines
        if plan.metadata.get('template') in ['ml_full_pipeline', 'linear_regression_basic']:
            cleanup.extend([
                {"op": "delete", "target": "sandbox/out/app/"},
                {"op": "delete", "target": "sandbox/out/report.md"}
            ])

        return cleanup


# Utility functions for plan manipulation
def plan_to_dict(plan: ExecutionPlan) -> Dict[str, Any]:
    """Convert ExecutionPlan to dictionary format"""
    return {
        'goal': plan.goal,
        'steps': [
            {
                'id': step.id,
                'tool': step.tool,
                'inputs': step.inputs,
                'outputs': step.outputs,
                'description': step.description
            }
            for step in plan.steps
        ],
        'capabilities': list(plan.capabilities),
        'inputs': plan.inputs,
        'outputs': plan.outputs,
        'metadata': plan.metadata
    }


def visualize_plan_dag(plan: ExecutionPlan) -> str:
    """Create ASCII DAG visualization of execution plan"""
    lines = []
    lines.append(f"Execution Plan: {plan.goal}")
    lines.append("=" * 60)

    for i, step in enumerate(plan.steps):
        # Show step with inputs/outputs
        arrow = "+->" if i == len(plan.steps) - 1 else "+->"
        lines.append(f"{arrow} {step.id}: {step.tool}")
        lines.append(f"   |  {step.description}")

        # Show inputs
        if step.inputs:
            inputs_str = ", ".join(f"{k}={v}" for k, v in step.inputs.items())
            lines.append(f"   |  inputs: {inputs_str}")

        # Show outputs
        if step.outputs:
            outputs_str = ", ".join(f"{k}={v}" for k, v in step.outputs.items())
            lines.append(f"   |  outputs: {outputs_str}")

        if i < len(plan.steps) - 1:
            lines.append("   |")

    lines.append("")
    lines.append(f"Required capabilities: {', '.join(sorted(plan.capabilities))}")
    lines.append(f"Template: {plan.metadata.get('template', 'unknown')}")
    lines.append(f"Complexity: {plan.metadata.get('complexity', 'unknown')}")

    return "\n".join(lines)
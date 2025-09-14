# aiox/kernel/meters.py - Carbon & Cost meters with step pruning
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ToolCall:
    """Record of a tool execution with metrics"""
    timestamp: str
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    latency_ms: float
    tokens_used: int
    cost_usd: float
    co2_grams: float
    cache_hit: bool
    step_id: str
    run_id: str


@dataclass
class RunMetrics:
    """Aggregate metrics for a complete run"""
    run_id: str
    start_time: str
    end_time: str
    total_tools: int
    total_tokens: int
    total_cost_usd: float
    total_co2_grams: float
    total_latency_ms: float
    cache_hit_rate: float
    tools_by_category: Dict[str, int]
    most_expensive_tool: str
    most_carbon_intensive_tool: str


class CarbonCostMeter:
    """Track carbon emissions, costs, and performance metrics per tool call"""

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = Path(sandbox_root)
        self.logs_dir = self.sandbox_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.calls_log = self.logs_dir / "tool_calls.jsonl"
        self.runs_log = self.logs_dir / "run_metrics.jsonl"

        # Current run tracking
        self.current_run_id = None
        self.current_run_calls = []
        self.run_start_time = None

        # Emission factors (grams CO2 per unit)
        self.co2_factors = {
            # Model calls (per 1000 tokens)
            "model_calls": {
                "claude-3-5-sonnet": 0.5,
                "gpt-4": 8.5,
                "gpt-3.5-turbo": 1.2,
                "default": 2.0
            },
            # Compute operations (per second of CPU)
            "cpu_ops": 0.8,  # grams per CPU second
            # Network operations (per MB transferred)
            "network_ops": 0.1,  # grams per MB
            # Storage operations (per MB read/written)
            "storage_ops": 0.05  # grams per MB
        }

        # Cost estimates (USD)
        self.cost_factors = {
            "model_calls": {
                "claude-3-5-sonnet": {"input": 3.0e-6, "output": 15.0e-6},
                "gpt-4": {"input": 30.0e-6, "output": 60.0e-6},
                "gpt-3.5-turbo": {"input": 0.5e-6, "output": 1.5e-6}
            },
            "cpu_seconds": 0.0001,  # $0.0001 per CPU second
            "storage_mb": 0.00001,  # $0.00001 per MB
            "network_mb": 0.00005   # $0.00005 per MB
        }

    def start_run(self, run_id: Optional[str] = None) -> str:
        """Start tracking a new run"""
        if run_id is None:
            run_id = f"run_{int(time.time())}"

        self.current_run_id = run_id
        self.current_run_calls = []
        self.run_start_time = time.time()

        print(f"[meters] Started tracking run: {run_id}")
        return run_id

    def record_tool_call(self, tool_name: str, step_id: str, inputs: Dict[str, Any],
                        outputs: Dict[str, Any], latency_ms: float,
                        tokens_used: int = 0, cache_hit: bool = False,
                        model_name: Optional[str] = None) -> ToolCall:
        """Record a tool call with estimated costs and emissions"""

        if not self.current_run_id:
            self.start_run()

        # Estimate costs and emissions based on tool type
        cost_usd, co2_grams = self._estimate_tool_impact(
            tool_name, inputs, outputs, latency_ms, tokens_used, model_name
        )

        call = ToolCall(
            timestamp=datetime.utcnow().isoformat() + "Z",
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            co2_grams=co2_grams,
            cache_hit=cache_hit,
            step_id=step_id,
            run_id=self.current_run_id
        )

        # Store call
        self.current_run_calls.append(call)

        # Log to file
        with open(self.calls_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(call)) + '\n')

        return call

    def end_run(self) -> RunMetrics:
        """End current run and compute aggregate metrics"""
        if not self.current_run_id or not self.current_run_calls:
            raise ValueError("No active run to end")

        end_time = time.time()

        # Compute aggregates
        total_tokens = sum(call.tokens_used for call in self.current_run_calls)
        total_cost = sum(call.cost_usd for call in self.current_run_calls)
        total_co2 = sum(call.co2_grams for call in self.current_run_calls)
        total_latency = sum(call.latency_ms for call in self.current_run_calls)

        cache_hits = sum(1 for call in self.current_run_calls if call.cache_hit)
        cache_hit_rate = (cache_hits / len(self.current_run_calls)) * 100

        # Tools by category
        tools_by_category = {}
        for call in self.current_run_calls:
            category = self._get_tool_category(call.tool_name)
            tools_by_category[category] = tools_by_category.get(category, 0) + 1

        # Find most expensive tools
        most_expensive = max(self.current_run_calls, key=lambda c: c.cost_usd, default=None)
        most_carbon = max(self.current_run_calls, key=lambda c: c.co2_grams, default=None)

        run_metrics = RunMetrics(
            run_id=self.current_run_id,
            start_time=datetime.fromtimestamp(self.run_start_time).isoformat() + "Z",
            end_time=datetime.fromtimestamp(end_time).isoformat() + "Z",
            total_tools=len(self.current_run_calls),
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            total_co2_grams=total_co2,
            total_latency_ms=total_latency,
            cache_hit_rate=cache_hit_rate,
            tools_by_category=tools_by_category,
            most_expensive_tool=most_expensive.tool_name if most_expensive else "none",
            most_carbon_intensive_tool=most_carbon.tool_name if most_carbon else "none"
        )

        # Log run metrics
        with open(self.runs_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(run_metrics)) + '\n')

        print(f"[meters] Run {self.current_run_id} completed:")
        print(f"[meters]   Tools: {run_metrics.total_tools}, Tokens: {run_metrics.total_tokens}")
        print(f"[meters]   Cost: ${run_metrics.total_cost_usd:.6f}, CO2: {run_metrics.total_co2_grams:.2f}g")
        print(f"[meters]   Cache hit rate: {run_metrics.cache_hit_rate:.1f}%")

        # Reset current run
        self.current_run_id = None
        self.current_run_calls = []
        self.run_start_time = None

        return run_metrics

    def _estimate_tool_impact(self, tool_name: str, inputs: Dict[str, Any], outputs: Dict[str, Any],
                             latency_ms: float, tokens_used: int, model_name: Optional[str]) -> Tuple[float, float]:
        """Estimate cost and CO2 impact for a tool call"""
        cost_usd = 0.0
        co2_grams = 0.0

        # Model-based tools
        if model_name and tokens_used > 0:
            model_costs = self.cost_factors["model_calls"].get(model_name,
                                                               self.cost_factors["model_calls"]["gpt-3.5-turbo"])
            # Rough split between input/output tokens
            input_tokens = int(tokens_used * 0.7)
            output_tokens = tokens_used - input_tokens
            cost_usd += (input_tokens * model_costs["input"]) + (output_tokens * model_costs["output"])

            co2_factor = self.co2_factors["model_calls"].get(model_name,
                                                           self.co2_factors["model_calls"]["default"])
            co2_grams += (tokens_used / 1000.0) * co2_factor

        # CPU-intensive operations
        cpu_seconds = latency_ms / 1000.0
        if tool_name in ['train_lr', 'eval', 'split', 'profile']:
            # These are compute-heavy
            cost_usd += cpu_seconds * self.cost_factors["cpu_seconds"] * 10  # 10x multiplier for heavy ops
            co2_grams += cpu_seconds * self.co2_factors["cpu_ops"] * 10
        else:
            # Light operations
            cost_usd += cpu_seconds * self.cost_factors["cpu_seconds"]
            co2_grams += cpu_seconds * self.co2_factors["cpu_ops"]

        # Storage operations
        if tool_name in ['read_csv', 'write_file', 'write_json', 'zip']:
            # Estimate data size from inputs/outputs
            data_size_mb = self._estimate_data_size_mb(inputs, outputs)
            cost_usd += data_size_mb * self.cost_factors["storage_mb"]
            co2_grams += data_size_mb * self.co2_factors["storage_ops"]

        return cost_usd, co2_grams

    def _estimate_data_size_mb(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> float:
        """Rough estimate of data size in MB"""
        # Very rough estimation based on JSON size
        input_size = len(json.dumps(inputs)) / (1024 * 1024)
        output_size = len(json.dumps(outputs)) / (1024 * 1024)
        return max(0.01, input_size + output_size)  # Minimum 0.01 MB

    def _get_tool_category(self, tool_name: str) -> str:
        """Categorize tool for reporting"""
        categories = {
            "data": ["read_csv", "write_file", "write_json", "profile"],
            "ml": ["train_lr", "eval", "split"],
            "processing": ["zip", "verify_zip"],
            "reporting": ["emit_report"],
            "system": ["build_cli", "verify_cli"],
            "model": ["generate", "plan", "analyze"]
        }

        for category, tools in categories.items():
            if tool_name in tools:
                return category
        return "other"

    def get_current_run_stats(self) -> Dict[str, Any]:
        """Get stats for current run in progress"""
        if not self.current_run_calls:
            return {"status": "no_active_run"}

        total_cost = sum(call.cost_usd for call in self.current_run_calls)
        total_co2 = sum(call.co2_grams for call in self.current_run_calls)
        total_tokens = sum(call.tokens_used for call in self.current_run_calls)

        cache_hits = sum(1 for call in self.current_run_calls if call.cache_hit)
        cache_rate = (cache_hits / len(self.current_run_calls)) * 100

        return {
            "status": "active_run",
            "run_id": self.current_run_id,
            "tools_executed": len(self.current_run_calls),
            "total_cost_usd": total_cost,
            "total_co2_grams": total_co2,
            "total_tokens": total_tokens,
            "cache_hit_rate": cache_rate,
            "runtime_seconds": time.time() - self.run_start_time if self.run_start_time else 0
        }

    def get_historical_stats(self, limit: int = 10) -> Dict[str, Any]:
        """Get historical run statistics"""
        if not self.runs_log.exists():
            return {"runs": [], "totals": {}}

        runs = []
        lines = self.runs_log.read_text(encoding='utf-8').strip().split('\n')
        for line in lines[-limit:]:
            if line.strip():
                runs.append(json.loads(line))

        # Compute totals
        total_cost = sum(run.get("total_cost_usd", 0) for run in runs)
        total_co2 = sum(run.get("total_co2_grams", 0) for run in runs)
        total_tokens = sum(run.get("total_tokens", 0) for run in runs)

        return {
            "runs": runs,
            "totals": {
                "runs_analyzed": len(runs),
                "total_cost_usd": total_cost,
                "total_co2_grams": total_co2,
                "total_tokens": total_tokens,
                "avg_cost_per_run": total_cost / len(runs) if runs else 0,
                "avg_co2_per_run": total_co2 / len(runs) if runs else 0
            }
        }

    def suggest_pruning_opportunities(self) -> List[Dict[str, Any]]:
        """Analyze current/recent runs for pruning opportunities"""
        suggestions = []

        if not self.current_run_calls:
            return suggestions

        # Find redundant or expensive operations
        tool_counts = {}
        expensive_calls = []

        for call in self.current_run_calls:
            tool_counts[call.tool_name] = tool_counts.get(call.tool_name, 0) + 1

            if call.cost_usd > 0.001 or call.co2_grams > 1.0:  # Expensive threshold
                expensive_calls.append(call)

        # Suggest caching for repeated tools
        for tool, count in tool_counts.items():
            if count > 2:  # Called more than twice
                suggestions.append({
                    "type": "cache_opportunity",
                    "tool": tool,
                    "count": count,
                    "potential_savings": f"Could cache {tool} results (called {count} times)"
                })

        # Suggest reviewing expensive operations
        for call in expensive_calls:
            suggestions.append({
                "type": "expensive_operation",
                "tool": call.tool_name,
                "cost": call.cost_usd,
                "co2": call.co2_grams,
                "suggestion": f"Review {call.tool_name} - high cost/emissions"
            })

        return suggestions
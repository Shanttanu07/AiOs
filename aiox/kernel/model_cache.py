# aiox/kernel/model_cache.py - Model call caching for deterministic replay
from __future__ import annotations
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ModelCall:
    """Record of a model API call"""
    timestamp: str
    model: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    tokens_used: int
    latency_ms: float
    cost_usd: float
    co2_grams: float
    cache_hit: bool


class ModelCallCache:
    """Cache system for model API calls with deterministic replay"""

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = Path(sandbox_root)
        self.cache_root = self.sandbox_root / "cache" / "model"
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.call_log = self.sandbox_root / "logs" / "model_calls.jsonl"
        self.call_log.parent.mkdir(parents=True, exist_ok=True)

        # Cost/emission estimates (rough approximations)
        self.cost_per_token = {
            "claude-3-5-sonnet-20241022": {"input": 3.0e-6, "output": 15.0e-6},  # $3/$15 per 1M tokens
            "gpt-4": {"input": 30.0e-6, "output": 60.0e-6},
            "gpt-3.5-turbo": {"input": 0.5e-6, "output": 1.5e-6}
        }

        # CO2 estimates (grams per 1000 tokens, rough estimates)
        self.co2_per_1k_tokens = {
            "claude-3-5-sonnet-20241022": 0.5,  # Conservative estimate
            "gpt-4": 8.5,  # Based on published research
            "gpt-3.5-turbo": 1.2
        }

    def _compute_cache_key(self, model: str, inputs: Dict[str, Any]) -> str:
        """Compute deterministic hash for model call inputs"""
        # Sort inputs for consistent hashing
        normalized = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        content = f"{model}:{normalized}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key"""
        # Store in subdirectories to avoid filesystem limits
        subdir = cache_key[:2]
        cache_dir = self.cache_root / subdir
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / f"{cache_key}.json"

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return max(1, len(text) // 4)

    def _estimate_cost_and_emissions(self, model: str, input_tokens: int, output_tokens: int) -> Tuple[float, float]:
        """Estimate cost in USD and CO2 emissions in grams"""
        # Cost estimation
        costs = self.cost_per_token.get(model, {"input": 1.0e-6, "output": 2.0e-6})
        cost_usd = (input_tokens * costs["input"]) + (output_tokens * costs["output"])

        # CO2 estimation
        co2_per_1k = self.co2_per_1k_tokens.get(model, 2.0)
        total_tokens = input_tokens + output_tokens
        co2_grams = (total_tokens / 1000.0) * co2_per_1k

        return cost_usd, co2_grams

    def get_cached_result(self, model: str, inputs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if result exists in cache"""
        cache_key = self._compute_cache_key(model, inputs)
        cache_path = self._get_cache_path(cache_key)

        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding='utf-8'))
                # Log cache hit
                self._log_cache_access(model, inputs, cached, cache_hit=True)
                return cached["outputs"]
            except Exception as e:
                print(f"[cache] Failed to load cached result: {e}")
                return None

        return None

    def store_result(self, model: str, inputs: Dict[str, Any], outputs: Dict[str, Any],
                    latency_ms: float, actual_tokens: Optional[Dict[str, int]] = None) -> str:
        """Store model call result in cache"""
        cache_key = self._compute_cache_key(model, inputs)
        cache_path = self._get_cache_path(cache_key)

        # Estimate tokens if not provided
        if actual_tokens:
            input_tokens = actual_tokens.get("input", 0)
            output_tokens = actual_tokens.get("output", 0)
        else:
            # Rough estimation from text content
            input_text = json.dumps(inputs)
            output_text = json.dumps(outputs)
            input_tokens = self._estimate_tokens(input_text)
            output_tokens = self._estimate_tokens(output_text)

        # Estimate cost and emissions
        cost_usd, co2_grams = self._estimate_cost_and_emissions(model, input_tokens, output_tokens)

        # Prepare cache entry
        cache_entry = {
            "cache_key": cache_key,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model": model,
            "inputs": inputs,
            "outputs": outputs,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            },
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "co2_grams": co2_grams
        }

        # Store to cache file
        cache_path.write_text(json.dumps(cache_entry, indent=2), encoding='utf-8')

        # Log the call
        self._log_cache_access(model, inputs, cache_entry, cache_hit=False)

        return cache_key

    def _log_cache_access(self, model: str, inputs: Dict[str, Any], cache_entry: Dict[str, Any], cache_hit: bool):
        """Log model call to activity log"""
        call_record = ModelCall(
            timestamp=datetime.utcnow().isoformat() + "Z",
            model=model,
            inputs=inputs,
            outputs=cache_entry.get("outputs", {}),
            tokens_used=cache_entry.get("tokens", {}).get("total", 0),
            latency_ms=cache_entry.get("latency_ms", 0.0),
            cost_usd=cache_entry.get("cost_usd", 0.0),
            co2_grams=cache_entry.get("co2_grams", 0.0),
            cache_hit=cache_hit
        )

        # Append to log file
        with open(self.call_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(call_record)) + '\n')

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_root.rglob("*.json"))
        total_cached = len(cache_files)

        # Read recent call logs for stats
        stats = {
            "total_cached_calls": total_cached,
            "cache_size_mb": sum(f.stat().st_size for f in cache_files) / (1024 * 1024),
            "recent_calls": [],
            "total_cost_usd": 0.0,
            "total_co2_grams": 0.0,
            "total_tokens": 0,
            "cache_hit_rate": 0.0
        }

        if self.call_log.exists():
            try:
                recent_calls = []
                total_calls = 0
                cache_hits = 0

                # Read last 100 calls for recent stats
                lines = self.call_log.read_text(encoding='utf-8').strip().split('\n')
                for line in lines[-100:]:
                    if line.strip():
                        call = json.loads(line)
                        recent_calls.append(call)
                        total_calls += 1
                        if call.get("cache_hit"):
                            cache_hits += 1
                        stats["total_cost_usd"] += call.get("cost_usd", 0.0)
                        stats["total_co2_grams"] += call.get("co2_grams", 0.0)
                        stats["total_tokens"] += call.get("tokens_used", 0)

                stats["recent_calls"] = recent_calls[-10:]  # Last 10 calls
                stats["cache_hit_rate"] = (cache_hits / total_calls * 100) if total_calls > 0 else 0.0

            except Exception as e:
                print(f"[cache] Error reading call log: {e}")

        return stats

    def verify_replay_deterministic(self, expected_calls: list) -> Tuple[bool, list]:
        """Verify that replay uses only cached results"""
        issues = []

        for call in expected_calls:
            cache_key = self._compute_cache_key(call["model"], call["inputs"])
            cache_path = self._get_cache_path(cache_key)

            if not cache_path.exists():
                issues.append(f"Missing cache for call: {cache_key[:8]}...")
            else:
                # Verify cached result matches expected
                try:
                    cached = json.loads(cache_path.read_text(encoding='utf-8'))
                    if cached["outputs"] != call.get("expected_outputs"):
                        issues.append(f"Cache mismatch for call: {cache_key[:8]}...")
                except Exception as e:
                    issues.append(f"Cache read error for call: {cache_key[:8]}... - {e}")

        return len(issues) == 0, issues

    def clear_cache(self):
        """Clear all cached model calls"""
        import shutil
        if self.cache_root.exists():
            shutil.rmtree(self.cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)

        # Clear call log
        if self.call_log.exists():
            self.call_log.unlink()
        self.call_log.touch()
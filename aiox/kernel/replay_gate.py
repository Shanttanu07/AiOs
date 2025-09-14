# aiox/kernel/replay_gate.py - Deterministic replay enforcement
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from .model_cache import ModelCallCache


class ReplayGate:
    """Enforce deterministic replay by ensuring all model calls hit cache"""

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = Path(sandbox_root)
        self.cache = ModelCallCache(sandbox_root)
        self.replay_mode = False
        self.expected_calls = []
        self.actual_calls = []

    def enable_replay_mode(self, expected_model_calls: List[Dict[str, Any]]):
        """Enable replay mode with expected model calls"""
        self.replay_mode = True
        self.expected_calls = expected_model_calls
        self.actual_calls = []
        print(f"[replay] Enabled replay mode with {len(expected_model_calls)} expected model calls")

    def disable_replay_mode(self):
        """Disable replay mode"""
        self.replay_mode = False
        self.expected_calls = []
        self.actual_calls = []
        print("[replay] Disabled replay mode")

    def check_model_call(self, model: str, inputs: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if model call is allowed and return cached result if in replay mode

        Returns:
            (is_allowed, cached_result)
        """
        if not self.replay_mode:
            # Normal mode - allow all calls
            return True, None

        # Replay mode - only allow cached calls
        cached_result = self.cache.get_cached_result(model, inputs)
        if cached_result is None:
            print(f"[replay] ERROR: Model call not found in cache during replay")
            print(f"[replay]        Model: {model}")
            print(f"[replay]        Inputs: {str(inputs)[:100]}...")
            return False, None

        # Log the call for verification
        self.actual_calls.append({
            "model": model,
            "inputs": inputs,
            "outputs": cached_result,
            "cache_hit": True
        })

        return True, cached_result

    def verify_replay_completeness(self) -> Tuple[bool, List[str]]:
        """Verify that replay matched all expected calls"""
        if not self.replay_mode:
            return True, []

        issues = []

        # Check if we made the expected number of calls
        if len(self.actual_calls) != len(self.expected_calls):
            issues.append(f"Call count mismatch: expected {len(self.expected_calls)}, got {len(self.actual_calls)}")

        # Verify each call matched expectations
        for i, expected in enumerate(self.expected_calls):
            if i >= len(self.actual_calls):
                issues.append(f"Missing call {i+1}: {expected.get('model', 'unknown')}")
                continue

            actual = self.actual_calls[i]

            # Verify model matches
            if actual.get('model') != expected.get('model'):
                issues.append(f"Call {i+1} model mismatch: expected {expected.get('model')}, got {actual.get('model')}")

            # Note: We don't strictly verify inputs/outputs during replay since cache lookup handles that

        return len(issues) == 0, issues

    def get_replay_summary(self) -> Dict[str, Any]:
        """Get summary of replay verification"""
        if not self.replay_mode:
            return {"replay_mode": False}

        success, issues = self.verify_replay_completeness()

        return {
            "replay_mode": True,
            "success": success,
            "expected_calls": len(self.expected_calls),
            "actual_calls": len(self.actual_calls),
            "issues": issues,
            "cache_stats": self.cache.get_cache_stats()
        }

    def record_successful_run(self) -> str:
        """Record a successful run's model calls for future replay verification"""
        if self.replay_mode:
            return "Cannot record during replay mode"

        # Get recent model calls from cache log
        cache_stats = self.cache.get_cache_stats()
        recent_calls = cache_stats.get("recent_calls", [])

        if not recent_calls:
            return "No model calls to record"

        # Save call log for this run
        run_log_path = self.sandbox_root / "logs" / "last_run_model_calls.json"
        run_log_path.parent.mkdir(parents=True, exist_ok=True)

        recorded_calls = []
        for call in recent_calls:
            if not call.get("cache_hit", False):  # Only record original calls, not cache hits
                recorded_calls.append({
                    "model": call.get("model"),
                    "inputs": call.get("inputs"),
                    "expected_outputs": call.get("outputs")
                })

        run_log_path.write_text(json.dumps({
            "recorded_at": cache_stats.get("recent_calls", [{}])[-1].get("timestamp", "unknown"),
            "model_calls": recorded_calls
        }, indent=2), encoding='utf-8')

        return f"Recorded {len(recorded_calls)} model calls for replay verification"

    def load_run_for_replay(self) -> bool:
        """Load last run's model calls for replay verification"""
        run_log_path = self.sandbox_root / "logs" / "last_run_model_calls.json"

        if not run_log_path.exists():
            print("[replay] No previous run log found for replay verification")
            return False

        try:
            run_data = json.loads(run_log_path.read_text(encoding='utf-8'))
            model_calls = run_data.get("model_calls", [])

            if not model_calls:
                print("[replay] No model calls found in run log")
                return False

            self.enable_replay_mode(model_calls)
            print(f"[replay] Loaded {len(model_calls)} model calls from previous run")
            return True

        except Exception as e:
            print(f"[replay] Failed to load run log: {e}")
            return False
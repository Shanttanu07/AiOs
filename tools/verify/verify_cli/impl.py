# tools/verify/verify_cli/impl.py

def execute(inputs, context):
    """Test CLI application with sample input"""
    app_dir = inputs["app_dir"]
    sample_input = inputs["sample_input"]

    # Delegate to context if available
    if hasattr(context, '_proc_spawn_cli_predict'):
        result = context._proc_spawn_cli_predict(app_dir, sample_input)
        return {"prediction": result}
    else:
        # Basic implementation
        import subprocess
        import sys
        from pathlib import Path

        app_path = Path(app_dir)
        predict_py = app_path / "predict.py"

        if not predict_py.exists():
            raise FileNotFoundError(f"predict.py not found in {app_dir}")

        try:
            result = subprocess.run(
                [sys.executable, "predict.py", "--input", sample_input],
                cwd=app_path,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"CLI failed: {result.stderr}")

            output = result.stdout.strip()
            prediction = float(output)
            return {"prediction": prediction}

        except (ValueError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"CLI verification failed: {e}")

    return {}
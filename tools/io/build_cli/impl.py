# tools/io/build_cli/impl.py

def execute(inputs, context):
    """Build CLI application from trained model"""
    model = inputs["model"]
    schema = inputs["schema"]
    output_dir = inputs["output_dir"]

    # Delegate to context if available
    if hasattr(context, 'mem') and hasattr(context, '_build_cli'):
        # Store in memory slots temporarily for legacy method
        model_slot = "_temp_model"
        schema_slot = "_temp_schema"
        context.mem[model_slot] = model
        context.mem[schema_slot] = schema
        context._build_cli(model_slot, schema_slot, output_dir)
    else:
        # Basic stub - create minimal CLI
        from pathlib import Path
        import json

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Create predict.py
        predict_code = f'''#!/usr/bin/env python3
import json
import argparse

def predict(features):
    # Simple prediction using model
    coef = {model.get('coef', [0.0])}
    intercept = {model.get('intercept', 0.0)}

    result = intercept
    feature_names = {model.get('features', [])}

    for i, (name, val) in enumerate(zip(feature_names, features)):
        if i < len(coef):
            result += coef[i] * val

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    features = [data.get(name, 0) for name in {model.get('features', [])}]
    pred = predict(features)
    print(pred)
'''

        (out_path / "predict.py").write_text(predict_code)

    return {}
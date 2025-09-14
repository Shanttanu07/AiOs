# tools/ml/eval/impl.py

def execute(inputs, context):
    """Evaluate model performance on validation data"""
    model = inputs["model"]
    val_data = inputs["val_data"]
    target = inputs.get("target", "price")

    # Use context's evaluation method if available
    if hasattr(context, '_eval'):
        header = val_data["header"]
        rows = val_data["rows"]
        return {"metrics": context._eval(model, header, rows, target)}

    # Fallback basic implementation
    header = val_data["header"]
    rows = val_data["rows"]

    if target not in header:
        raise ValueError(f"Target column '{target}' not found in validation data")

    target_idx = header.index(target)
    feature_names = model.get("features", [])
    coef = model.get("coef", [])
    intercept = model.get("intercept", 0.0)

    # Make predictions
    y_true = []
    y_pred = []

    for row in rows:
        target_val = row[target_idx]
        if not isinstance(target_val, (int, float)):
            continue

        # Make prediction
        pred = intercept
        for i, feat_name in enumerate(feature_names):
            if feat_name in header:
                feat_idx = header.index(feat_name)
                feat_val = row[feat_idx] if feat_idx < len(row) else 0
                if isinstance(feat_val, (int, float)) and i < len(coef):
                    pred += coef[i] * feat_val

        y_true.append(float(target_val))
        y_pred.append(pred)

    if len(y_true) == 0:
        raise ValueError("No valid predictions could be made")

    # Calculate metrics
    n = len(y_true)
    mse = sum((y_true[i] - y_pred[i]) ** 2 for i in range(n)) / n
    mae = sum(abs(y_true[i] - y_pred[i]) for i in range(n)) / n

    # R² calculation
    y_mean = sum(y_true) / n
    ss_tot = sum((y - y_mean) ** 2 for y in y_true)
    ss_res = sum((y_true[i] - y_pred[i]) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "metrics": {
            "MSE": mse,
            "MAE": mae,
            "R2": r2
        }
    }
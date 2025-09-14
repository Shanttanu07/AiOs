# tools/ml/train_lr/impl.py

def execute(inputs, context):
    """Train linear regression model"""
    train_data = inputs["train_data"]
    target = inputs["target"]

    # Use context's training method if available
    if hasattr(context, '_train_lr'):
        header = train_data["header"]
        rows = train_data["rows"]
        return {"model": context._train_lr(header, rows, target)}

    # Fallback basic implementation
    header = train_data["header"]
    rows = train_data["rows"]

    # Find target column
    if target not in header:
        raise ValueError(f"Target column '{target}' not found in data")

    target_idx = header.index(target)
    feature_names = [h for i, h in enumerate(header) if i != target_idx]
    feature_indices = [i for i, h in enumerate(header) if i != target_idx]

    # Extract features and targets
    X = []
    y = []

    for row in rows:
        target_val = row[target_idx]
        if not isinstance(target_val, (int, float)):
            continue

        feature_vals = []
        valid = True
        for idx in feature_indices:
            val = row[idx] if idx < len(row) else 0
            if isinstance(val, (int, float)):
                feature_vals.append(float(val))
            else:
                valid = False
                break

        if valid:
            X.append(feature_vals)
            y.append(float(target_val))

    if len(X) < 2:
        raise ValueError("Insufficient valid training data")

    # Simple linear regression (single feature for simplicity)
    if len(X[0]) == 1:
        # y = mx + b
        n = len(X)
        sum_x = sum(row[0] for row in X)
        sum_y = sum(y)
        sum_xy = sum(X[i][0] * y[i] for i in range(n))
        sum_x2 = sum(row[0] ** 2 for row in X)

        m = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        b = (sum_y - m * sum_x) / n

        return {
            "model": {
                "features": feature_names,
                "coef": [m],
                "intercept": b,
                "type": "linear_regression"
            }
        }
    else:
        # Multi-feature - return simple mean predictor
        mean_y = sum(y) / len(y)
        return {
            "model": {
                "features": feature_names,
                "coef": [0.0] * len(feature_names),
                "intercept": mean_y,
                "type": "mean_predictor"
            }
        }
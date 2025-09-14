# tools/ml/train_lr/impl.py - Use sklearn for proper ML instead of reinventing the wheel

def execute(inputs, context):
    """Train linear regression model using sklearn"""
    train_data = inputs["train_data"]
    target = inputs["target"]

    # Use context's training method if available (for compatibility)
    if hasattr(context, '_train_lr'):
        header = train_data["header"]
        rows = train_data["rows"]
        return {"model": context._train_lr(header, rows, target)}

    # Use sklearn for proper ML implementation
    try:
        import pandas as pd
        from sklearn.linear_model import LinearRegression
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        import numpy as np
    except ImportError:
        # Fallback to basic implementation if sklearn not available
        return _fallback_linear_regression(train_data, target)

    # Convert to pandas DataFrame for easier handling
    header = train_data["header"]
    rows = train_data["rows"]
    df = pd.DataFrame(rows, columns=header)

    # Validate target column
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in data")

    # Separate features and target
    feature_cols = [col for col in df.columns if col != target]
    X = df[feature_cols]
    y = df[target]

    # Handle missing values and data cleaning
    # Remove rows where target is missing
    valid_mask = pd.notna(y)
    X = X[valid_mask]
    y = y[valid_mask]

    if len(X) < 2:
        raise ValueError("Insufficient valid training data after cleaning")

    # Convert non-numeric columns to numeric (handle messy data)
    for col in X.columns:
        if X[col].dtype == 'object':
            # Try to convert strings to numbers, fill non-convertible with median
            X[col] = pd.to_numeric(X[col], errors='coerce')

    # Impute missing values with median (robust to outliers)
    imputer = SimpleImputer(strategy='median')
    X_imputed = imputer.fit_transform(X)

    # Ensure target is numeric
    y = pd.to_numeric(y, errors='coerce')
    y = y.dropna()

    if len(y) != len(X_imputed):
        # Align after target cleaning
        X_imputed = X_imputed[:len(y)]

    # Train sklearn LinearRegression
    model = LinearRegression()
    model.fit(X_imputed, y)

    # Calculate R² score for model quality
    r2_score = model.score(X_imputed, y)

    # Package model in our format
    model_data = {
        "features": feature_cols,
        "coef": model.coef_.tolist(),
        "intercept": float(model.intercept_),
        "type": "sklearn_linear_regression",
        "imputer_medians": imputer.statistics_.tolist(),
        "r2_score": float(r2_score),
        "n_samples": len(X_imputed),
        "n_features": len(feature_cols)
    }

    return {"model": model_data}

def _fallback_linear_regression(train_data, target):
    """Fallback implementation when sklearn is not available"""
    header = train_data["header"]
    rows = train_data["rows"]

    if target not in header:
        raise ValueError(f"Target column '{target}' not found in data")

    target_idx = header.index(target)
    feature_names = [h for i, h in enumerate(header) if i != target_idx]

    # Simple mean predictor as fallback
    target_values = []
    for row in rows:
        if target_idx < len(row) and isinstance(row[target_idx], (int, float)):
            target_values.append(float(row[target_idx]))

    if not target_values:
        raise ValueError("No valid target values found")

    mean_target = sum(target_values) / len(target_values)

    return {
        "model": {
            "features": feature_names,
            "coef": [0.0] * len(feature_names),
            "intercept": mean_target,
            "type": "fallback_mean_predictor",
            "r2_score": 0.0,
            "n_samples": len(target_values)
        }
    }
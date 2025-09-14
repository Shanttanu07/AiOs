# tools/verify/assert_ge/impl.py

def execute(inputs, context):
    """Assert that metric is greater than or equal to threshold"""
    metrics = inputs["metrics"]
    field = inputs["field"]
    threshold = inputs["threshold"]

    if field not in metrics:
        raise ValueError(f"Field '{field}' not found in metrics")

    value = metrics[field]
    if not isinstance(value, (int, float)):
        raise ValueError(f"Field '{field}' is not numeric: {value}")

    if value < threshold:
        raise RuntimeError(f"Assertion failed: {field}={value} < {threshold}")

    print(f"[assert] {field}={value} >= {threshold} OK")
    return {}
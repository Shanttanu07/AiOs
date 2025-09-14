# tools/data/profile/impl.py

def execute(inputs, context):
    """Profile dataset schema and generate metadata"""
    table = inputs["table"]
    header = table["header"]
    rows = table["rows"]

    # Use context's profiling method if available
    if hasattr(context, '_profile'):
        return {"schema": context._profile(header, rows)}

    # Fallback implementation
    n = len(rows)
    cols = []

    for i, name in enumerate(header):
        # Collect column values
        values = []
        for row in rows:
            if i < len(row):
                values.append(row[i])

        # Determine type and missing count
        numeric_count = 0
        string_count = 0
        null_count = 0

        for val in values:
            if val is None or val == "":
                null_count += 1
            elif isinstance(val, (int, float)):
                numeric_count += 1
            else:
                string_count += 1

        # Determine predominant type
        if numeric_count > string_count:
            dtype = "number"
        else:
            dtype = "string"

        missing_rate = null_count / max(1, len(values))

        cols.append({
            "name": name,
            "dtype": dtype,
            "missing": missing_rate
        })

    return {"schema": {"rows": n, "cols": cols}}
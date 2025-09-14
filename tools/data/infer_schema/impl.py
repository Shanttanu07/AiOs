# tools/data/infer_schema/impl.py - Smart schema inference for messy data

def execute(inputs, context):
    """Infer schema from messy, unstructured data"""
    data = inputs["data"]
    confidence_threshold = inputs.get("confidence_threshold", 0.8)

    # Handle different input types
    if isinstance(data, dict) and "rows" in data:
        # Table data
        header = data.get("header", [])
        rows = data.get("rows", [])
        return _infer_table_schema(header, rows, confidence_threshold)
    elif isinstance(data, list):
        # List of records
        return _infer_records_schema(data, confidence_threshold)
    elif isinstance(data, str):
        # Text data - try to parse
        return _infer_text_schema(data, confidence_threshold)
    else:
        return {
            "schema": {"type": "unknown", "confidence": 0.0},
            "report": {"status": "error", "message": f"Unsupported data type: {type(data)}"}
        }

def _infer_table_schema(header, rows, threshold):
    """Infer schema from table data"""
    schema_fields = []
    issues = []

    for i, col_name in enumerate(header):
        # Collect values from this column
        values = []
        missing_count = 0

        for row in rows:
            if i < len(row):
                val = row[i]
                if val is None or val == "" or val == "NULL":
                    missing_count += 1
                else:
                    values.append(val)

        # Infer type from values
        field_type, confidence = _infer_field_type(values)
        missing_rate = missing_count / len(rows) if rows else 0

        field_schema = {
            "name": col_name,
            "type": field_type,
            "confidence": confidence,
            "missing_rate": missing_rate,
            "sample_values": values[:5]  # First 5 non-null values
        }

        schema_fields.append(field_schema)

        # Track issues
        if confidence < threshold:
            issues.append(f"Low confidence for field '{col_name}': {confidence:.2f}")
        if missing_rate > 0.5:
            issues.append(f"High missing rate for field '{col_name}': {missing_rate:.1%}")

    return {
        "schema": {
            "type": "table",
            "fields": schema_fields,
            "row_count": len(rows),
            "confidence": sum(f["confidence"] for f in schema_fields) / len(schema_fields) if schema_fields else 0
        },
        "report": {
            "status": "success" if not issues else "warnings",
            "issues": issues,
            "recommendations": _generate_recommendations(schema_fields)
        }
    }

def _infer_field_type(values):
    """Infer type of a field from sample values"""
    if not values:
        return "empty", 0.0

    # Type counters
    int_count = 0
    float_count = 0
    date_count = 0
    bool_count = 0
    string_count = 0

    for val in values:
        if isinstance(val, bool):
            bool_count += 1
        elif isinstance(val, int):
            int_count += 1
        elif isinstance(val, float):
            float_count += 1
        elif isinstance(val, str):
            # Try to parse as different types
            val_lower = val.lower().strip()

            # Boolean
            if val_lower in ["true", "false", "yes", "no", "1", "0", "y", "n"]:
                bool_count += 1
            # Integer
            elif val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                int_count += 1
            # Float
            elif _is_float(val):
                float_count += 1
            # Date
            elif _is_date_like(val):
                date_count += 1
            else:
                string_count += 1
        else:
            string_count += 1

    total = len(values)
    # Find dominant type
    type_scores = {
        "boolean": bool_count / total,
        "integer": int_count / total,
        "number": float_count / total,
        "date": date_count / total,
        "string": string_count / total
    }

    best_type = max(type_scores.items(), key=lambda x: x[1])
    return best_type[0], best_type[1]

def _is_float(s):
    """Check if string can be parsed as float"""
    try:
        float(s)
        return True
    except ValueError:
        return False

def _is_date_like(s):
    """Check if string looks like a date"""
    import re
    # Simple date patterns
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
    ]

    for pattern in date_patterns:
        if re.match(pattern, s.strip()):
            return True
    return False

def _infer_records_schema(records, threshold):
    """Infer schema from list of records/objects"""
    if not records:
        return {"schema": {"type": "empty"}, "report": {"status": "error", "message": "No records provided"}}

    # Find all unique keys
    all_keys = set()
    for record in records:
        if isinstance(record, dict):
            all_keys.update(record.keys())

    if not all_keys:
        return {"schema": {"type": "unknown"}, "report": {"status": "error", "message": "No valid record structure found"}}

    # Convert to table format for analysis
    header = sorted(list(all_keys))
    rows = []

    for record in records:
        if isinstance(record, dict):
            row = [record.get(key) for key in header]
            rows.append(row)

    return _infer_table_schema(header, rows, threshold)

def _infer_text_schema(text, threshold):
    """Try to infer structure from raw text"""
    lines = text.strip().split('\n')

    # Try CSV detection
    if ',' in text or ';' in text or '\t' in text:
        import csv
        import io

        # Try different delimiters
        for delimiter in [',', ';', '\t', '|']:
            try:
                reader = csv.reader(io.StringIO(text), delimiter=delimiter)
                rows = list(reader)
                if len(rows) > 1 and len(rows[0]) > 1:
                    header = rows[0]
                    data_rows = rows[1:]
                    return _infer_table_schema(header, data_rows, threshold)
            except:
                continue

    # Try JSON detection
    if text.strip().startswith('{') or text.strip().startswith('['):
        try:
            import json
            data = json.loads(text)
            if isinstance(data, list):
                return _infer_records_schema(data, threshold)
            elif isinstance(data, dict):
                return _infer_records_schema([data], threshold)
        except:
            pass

    return {
        "schema": {
            "type": "text",
            "line_count": len(lines),
            "character_count": len(text),
            "confidence": 0.5
        },
        "report": {
            "status": "partial",
            "message": "Detected unstructured text data",
            "recommendations": ["Consider using nlp.extract_entities or text.parse tools for further processing"]
        }
    }

def _generate_recommendations(schema_fields):
    """Generate recommendations based on inferred schema"""
    recommendations = []

    for field in schema_fields:
        if field["confidence"] < 0.7:
            recommendations.append(f"Consider manual review of field '{field['name']}' - low confidence type inference")

        if field["missing_rate"] > 0.3:
            recommendations.append(f"Field '{field['name']}' has high missing values - consider using data.clean or providing defaults")

        if field["type"] == "string" and field["confidence"] > 0.8:
            recommendations.append(f"Field '{field['name']}' appears to be categorical - consider using data.categorize")

    if not recommendations:
        recommendations.append("Schema looks clean! Ready for downstream processing.")

    return recommendations
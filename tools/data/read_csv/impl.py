# tools/data/read_csv/impl.py
import csv
from pathlib import Path

def execute(inputs, context):
    """Read CSV file and parse into table format"""
    path = inputs["path"]

    # Use context's sandbox-aware file reading
    if hasattr(context, '_fs_read_csv'):
        header, rows = context._fs_read_csv(path)
        return {"table": {"header": header, "rows": rows}}

    # Fallback direct implementation
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with p.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Empty CSV file")

    header = rows[0]
    body = rows[1:]

    # Basic type coercion
    typed_body = []
    for row in body:
        typed_row = []
        for cell in row:
            cell = cell.strip()
            # Try to convert to number
            try:
                if '.' in cell:
                    typed_row.append(float(cell))
                else:
                    typed_row.append(int(cell))
            except ValueError:
                typed_row.append(cell)
        typed_body.append(typed_row)

    return {"table": {"header": header, "rows": typed_body}}
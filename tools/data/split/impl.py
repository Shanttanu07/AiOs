# tools/data/split/impl.py
import hashlib

def execute(inputs, context):
    """Split dataset into train/validation sets"""
    table = inputs["table"]
    ratio = inputs.get("ratio", 0.8)
    seed = inputs.get("seed", 1337)

    header = table["header"]
    rows = table["rows"]

    # Deterministic split using hash
    train_rows = []
    val_rows = []

    for i, row in enumerate(rows):
        h = hashlib.md5(f"{i}:{seed}".encode()).digest()[0]
        if (h / 255.0) < ratio:
            train_rows.append(row)
        else:
            val_rows.append(row)

    # Ensure at least one validation row for small datasets
    if len(val_rows) == 0 and len(train_rows) > 1:
        val_rows.append(train_rows.pop())

    return {
        "train": {"header": header, "rows": train_rows},
        "val": {"header": header, "rows": val_rows}
    }
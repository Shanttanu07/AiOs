# tools/io/emit_report/impl.py
from pathlib import Path

def execute(inputs, context):
    """Generate markdown report from schema and metrics"""
    schema = inputs["schema"]
    metrics = inputs["metrics"]
    output_path = inputs["output_path"]

    # Use context's report rendering if available
    if hasattr(context, '_render_report'):
        report_text = context._render_report(schema, metrics)
    else:
        # Basic fallback report
        report_text = f"""# ML Report

## Schema
Rows: {schema.get('rows', 'N/A')}

## Metrics
- **MSE**: {metrics.get('MSE', 'N/A')}
- **MAE**: {metrics.get('MAE', 'N/A')}
- **R2**: {metrics.get('R2', 'N/A')}
"""

    # Use context's file writing if available
    if hasattr(context, '_fs_write_text'):
        context._fs_write_text(output_path, report_text)
    else:
        # Direct write
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(report_text, encoding="utf-8")

    return {}
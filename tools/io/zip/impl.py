# tools/io/zip/impl.py

def execute(inputs, context):
    """Create ZIP archive from directory"""
    source_dir = inputs["source_dir"]
    output_path = inputs["output_path"]

    # Delegate to context if available
    if hasattr(context, '_zip_dir'):
        context._zip_dir(source_dir, output_path)
    else:
        # Basic implementation
        import zipfile
        from pathlib import Path

        src_path = Path(source_dir)
        out_path = Path(output_path)

        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in src_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(src_path)
                    zf.write(file_path, arcname)

    return {}
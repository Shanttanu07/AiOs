# tools/verify/verify_zip/impl.py

def execute(inputs, context):
    """Verify ZIP archive integrity"""
    zip_path = inputs["zip_path"]

    # Delegate to context if available
    if hasattr(context, '_verify_zip'):
        context._verify_zip(zip_path)
    else:
        # Basic verification
        import zipfile
        from pathlib import Path

        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                bad_file = zf.testzip()
                if bad_file:
                    raise RuntimeError(f"ZIP file corrupted: {bad_file}")
        except zipfile.BadZipFile:
            raise RuntimeError(f"Invalid ZIP file: {zip_path}")

    return {}
# tools/files/organize/impl.py - AI-native file organization and understanding

def execute(inputs, context):
    """Intelligently organize files using AI and semantic understanding"""
    directory = inputs["directory"]
    strategy = inputs.get("strategy", "semantic")
    create_index = inputs.get("create_index", True)

    import os
    from pathlib import Path

    dir_path = Path(directory)
    if not dir_path.exists():
        return {
            "organization_plan": {},
            "index": {},
            "summary": {"error": f"Directory not found: {directory}"}
        }

    # Scan directory and analyze files
    file_analysis = _analyze_directory(dir_path)

    # Generate organization plan based on strategy
    organization_plan = _create_organization_plan(file_analysis, strategy)

    # Create searchable index if requested
    index = _create_file_index(file_analysis) if create_index else {}

    # Generate summary
    summary = _create_summary(file_analysis, organization_plan)

    return {
        "organization_plan": organization_plan,
        "index": index,
        "summary": summary
    }

def _analyze_directory(dir_path):
    """Analyze all files in directory"""
    analysis = {
        "files": [],
        "total_size": 0,
        "file_types": {},
        "content_categories": {}
    }

    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            file_path = Path(root) / filename
            file_info = _analyze_file(file_path)
            analysis["files"].append(file_info)
            analysis["total_size"] += file_info["size"]

            # Track file types
            ext = file_info["extension"]
            analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1

            # Track content categories
            category = file_info["content_category"]
            analysis["content_categories"][category] = analysis["content_categories"].get(category, 0) + 1

    return analysis

def _analyze_file(file_path):
    """Analyze individual file"""
    try:
        stat = file_path.stat()
        extension = file_path.suffix.lower()

        # Basic file info
        file_info = {
            "path": str(file_path),
            "name": file_path.name,
            "extension": extension,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "content_category": _categorize_by_extension(extension),
            "content_summary": "",
            "keywords": []
        }

        # Content analysis for text files
        if extension in ['.txt', '.md', '.csv', '.json', '.py', '.js', '.html']:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:1000]  # First 1KB
                file_info["content_summary"] = _summarize_text_content(content, extension)
                file_info["keywords"] = _extract_keywords(content)
            except:
                pass

        # Simulate OCR for image files
        elif extension in ['.pdf', '.png', '.jpg', '.jpeg']:
            file_info["content_summary"] = f"Visual content: {file_path.name}"
            file_info["keywords"] = ["visual", "document", "image"]

        return file_info

    except Exception as e:
        return {
            "path": str(file_path),
            "name": file_path.name,
            "extension": "",
            "size": 0,
            "modified": 0,
            "content_category": "unknown",
            "content_summary": f"Error analyzing file: {e}",
            "keywords": []
        }

def _categorize_by_extension(ext):
    """Categorize file by extension"""
    categories = {
        "documents": ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf'],
        "spreadsheets": ['.xlsx', '.xls', '.csv', '.tsv'],
        "presentations": ['.ppt', '.pptx'],
        "images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
        "videos": ['.mp4', '.avi', '.mov', '.wmv', '.flv'],
        "audio": ['.mp3', '.wav', '.flac', '.aac'],
        "code": ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c'],
        "data": ['.json', '.xml', '.yaml', '.sql'],
        "archives": ['.zip', '.rar', '.7z', '.tar', '.gz']
    }

    for category, extensions in categories.items():
        if ext in extensions:
            return category

    return "other"

def _summarize_text_content(content, extension):
    """Generate summary of text content"""
    content_clean = content.strip()[:200]  # First 200 chars

    if extension == '.csv':
        lines = content_clean.split('\n')
        return f"CSV data with {len(lines)} rows, columns: {lines[0] if lines else 'unknown'}"

    elif extension == '.json':
        return "JSON data structure containing configuration or data records"

    elif extension in ['.py', '.js']:
        return f"Source code file ({extension[1:].upper()}) containing functions and logic"

    elif extension == '.md':
        return "Markdown documentation or notes"

    else:
        # Generic text summary
        words = len(content_clean.split())
        return f"Text document with approximately {words} words"

def _extract_keywords(content):
    """Extract keywords from text content"""
    # Simple keyword extraction
    import re

    words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
    # Remove common words
    common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}

    keywords = [word for word in set(words) if word not in common_words]
    return sorted(keywords)[:10]  # Top 10 keywords

def _create_organization_plan(analysis, strategy):
    """Create file organization plan based on strategy"""
    plan = {
        "strategy": strategy,
        "folders": {},
        "moves": []
    }

    if strategy == "by_type":
        # Organize by file type
        for file_info in analysis["files"]:
            category = file_info["content_category"]
            folder_name = f"{category}_files"

            if folder_name not in plan["folders"]:
                plan["folders"][folder_name] = {
                    "description": f"All {category} files",
                    "files": []
                }

            plan["folders"][folder_name]["files"].append(file_info["name"])
            plan["moves"].append({
                "from": file_info["path"],
                "to": f"{folder_name}/{file_info['name']}",
                "reason": f"File type: {category}"
            })

    elif strategy == "semantic":
        # Organize by content similarity (simplified)
        content_groups = {}

        for file_info in analysis["files"]:
            # Group by keywords similarity
            primary_keyword = file_info["keywords"][0] if file_info["keywords"] else "misc"
            group_name = f"{primary_keyword}_related"

            if group_name not in content_groups:
                content_groups[group_name] = []

            content_groups[group_name].append(file_info)

        for group_name, files in content_groups.items():
            if len(files) > 1:  # Only create folders for multiple files
                plan["folders"][group_name] = {
                    "description": f"Files related to {group_name.replace('_related', '')}",
                    "files": [f["name"] for f in files]
                }

                for file_info in files:
                    plan["moves"].append({
                        "from": file_info["path"],
                        "to": f"{group_name}/{file_info['name']}",
                        "reason": f"Content similarity: {group_name}"
                    })

    elif strategy == "by_date":
        # Organize by modification date
        import datetime

        for file_info in analysis["files"]:
            file_date = datetime.datetime.fromtimestamp(file_info["modified"])
            folder_name = file_date.strftime("%Y-%m")

            if folder_name not in plan["folders"]:
                plan["folders"][folder_name] = {
                    "description": f"Files from {folder_name}",
                    "files": []
                }

            plan["folders"][folder_name]["files"].append(file_info["name"])
            plan["moves"].append({
                "from": file_info["path"],
                "to": f"{folder_name}/{file_info['name']}",
                "reason": f"Modified in {folder_name}"
            })

    return plan

def _create_file_index(analysis):
    """Create searchable index of files"""
    index = {
        "files": {},
        "keywords": {},
        "categories": {},
        "created_at": "2024-01-15T10:00:00Z"
    }

    for file_info in analysis["files"]:
        file_id = file_info["name"]

        # File entry
        index["files"][file_id] = {
            "path": file_info["path"],
            "size": file_info["size"],
            "category": file_info["content_category"],
            "summary": file_info["content_summary"],
            "keywords": file_info["keywords"]
        }

        # Keyword index
        for keyword in file_info["keywords"]:
            if keyword not in index["keywords"]:
                index["keywords"][keyword] = []
            index["keywords"][keyword].append(file_id)

        # Category index
        category = file_info["content_category"]
        if category not in index["categories"]:
            index["categories"][category] = []
        index["categories"][category].append(file_id)

    return index

def _create_summary(analysis, plan):
    """Create summary of organization process"""
    return {
        "total_files": len(analysis["files"]),
        "total_size_mb": round(analysis["total_size"] / (1024 * 1024), 2),
        "file_types": analysis["file_types"],
        "content_categories": analysis["content_categories"],
        "folders_to_create": len(plan["folders"]),
        "files_to_move": len(plan["moves"]),
        "strategy_used": plan["strategy"],
        "recommendations": [
            f"Found {len(analysis['file_types'])} different file types",
            f"Identified {len(analysis['content_categories'])} content categories",
            f"Proposed organizing into {len(plan['folders'])} folders",
            "Run with execute=true to apply organization plan"
        ]
    }
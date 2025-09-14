# tools/viz/recommend/impl.py - Smart visualization recommendation

def execute(inputs, context):
    """Recommend optimal chart types for data"""
    data = inputs["data"]
    viz_context = inputs.get("context", "general")

    if not isinstance(data, dict) or "header" not in data:
        return {
            "recommendations": [],
            "preview_config": {},
            "error": "Invalid data format - expected table with header and rows"
        }

    header = data["header"]
    rows = data.get("rows", [])

    # Analyze data characteristics
    analysis = _analyze_data_for_viz(header, rows)

    # Generate recommendations based on data characteristics
    recommendations = _generate_viz_recommendations(analysis, viz_context)

    # Create preview config for top recommendation
    preview_config = _create_preview_config(recommendations[0] if recommendations else None, analysis)

    return {
        "recommendations": recommendations,
        "preview_config": preview_config,
        "data_analysis": analysis
    }

def _analyze_data_for_viz(header, rows):
    """Analyze data characteristics to inform visualization choice"""
    if not rows:
        return {"error": "No data rows to analyze"}

    analysis = {
        "column_count": len(header),
        "row_count": len(rows),
        "columns": {}
    }

    for i, col_name in enumerate(header):
        # Sample values from this column
        values = []
        for row in rows[:100]:  # Sample first 100 rows
            if i < len(row) and row[i] is not None:
                values.append(row[i])

        col_analysis = {
            "name": col_name,
            "sample_size": len(values),
            "data_type": _infer_column_type(values),
            "unique_count": len(set(values)) if values else 0,
            "has_nulls": len(values) < len(rows[:100])
        }

        # Additional stats for numeric columns
        if col_analysis["data_type"] == "numeric":
            numeric_values = [float(v) for v in values if isinstance(v, (int, float)) or str(v).replace('.','').replace('-','').isdigit()]
            if numeric_values:
                col_analysis["min"] = min(numeric_values)
                col_analysis["max"] = max(numeric_values)
                col_analysis["range"] = col_analysis["max"] - col_analysis["min"]

        analysis["columns"][col_name] = col_analysis

    return analysis

def _infer_column_type(values):
    """Infer the type of a column from sample values"""
    if not values:
        return "empty"

    numeric_count = 0
    date_count = 0
    categorical_count = 0

    for val in values:
        if isinstance(val, (int, float)):
            numeric_count += 1
        elif isinstance(val, str):
            # Try to parse as number
            try:
                float(val)
                numeric_count += 1
            except ValueError:
                # Check if it looks like a date
                if _looks_like_date(val):
                    date_count += 1
                else:
                    categorical_count += 1
        else:
            categorical_count += 1

    total = len(values)
    if numeric_count / total > 0.8:
        return "numeric"
    elif date_count / total > 0.6:
        return "date"
    else:
        return "categorical"

def _looks_like_date(s):
    """Simple date detection"""
    import re
    date_patterns = [r'\d{4}-\d{2}-\d{2}', r'\d{2}/\d{2}/\d{4}', r'\d{2}-\d{2}-\d{4}']
    return any(re.search(pattern, s) for pattern in date_patterns)

def _generate_viz_recommendations(analysis, context):
    """Generate visualization recommendations based on data analysis"""
    if "error" in analysis:
        return [{"type": "error", "message": analysis["error"]}]

    recommendations = []
    columns = analysis["columns"]
    numeric_cols = [name for name, col in columns.items() if col["data_type"] == "numeric"]
    categorical_cols = [name for name, col in columns.items() if col["data_type"] == "categorical"]
    date_cols = [name for name, col in columns.items() if col["data_type"] == "date"]

    # Time series (if date column present)
    if date_cols and numeric_cols:
        recommendations.append({
            "type": "line_chart",
            "confidence": 0.9,
            "x_axis": date_cols[0],
            "y_axis": numeric_cols[0],
            "justification": "Time series data detected - line chart shows trends over time effectively",
            "best_for": "tracking changes and trends over time"
        })

    # Distribution analysis
    if len(numeric_cols) >= 1:
        recommendations.append({
            "type": "histogram",
            "confidence": 0.8,
            "variable": numeric_cols[0],
            "justification": "Numeric data present - histogram reveals data distribution patterns",
            "best_for": "understanding data distribution and identifying outliers"
        })

    # Comparison between categories
    if categorical_cols and numeric_cols:
        recommendations.append({
            "type": "bar_chart",
            "confidence": 0.85,
            "x_axis": categorical_cols[0],
            "y_axis": numeric_cols[0],
            "justification": "Categorical and numeric variables - bar chart enables effective comparison between groups",
            "best_for": "comparing values across different categories"
        })

    # Correlation analysis
    if len(numeric_cols) >= 2:
        recommendations.append({
            "type": "scatter_plot",
            "confidence": 0.75,
            "x_axis": numeric_cols[0],
            "y_axis": numeric_cols[1],
            "justification": "Multiple numeric variables - scatter plot reveals relationships and correlations",
            "best_for": "exploring relationships between two continuous variables"
        })

    # Proportional data
    if len(categorical_cols) >= 1:
        unique_count = columns[categorical_cols[0]]["unique_count"]
        if unique_count <= 8:  # Good number of categories for pie chart
            recommendations.append({
                "type": "pie_chart",
                "confidence": 0.7,
                "category": categorical_cols[0],
                "justification": f"Categorical data with {unique_count} categories - pie chart shows proportional relationships",
                "best_for": "showing parts of a whole or proportional relationships"
            })

    # Sort by confidence
    recommendations.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Ensure we have at least one recommendation
    if not recommendations:
        recommendations.append({
            "type": "table",
            "confidence": 0.5,
            "justification": "Complex or mixed data types - tabular view provides comprehensive overview",
            "best_for": "detailed data inspection and analysis"
        })

    return recommendations

def _create_preview_config(top_recommendation, analysis):
    """Create configuration for generating the recommended visualization"""
    if not top_recommendation:
        return {}

    config = {
        "chart_type": top_recommendation["type"],
        "title": f"{top_recommendation['type'].replace('_', ' ').title()}",
        "data_source": "input_data"
    }

    # Add specific configurations based on chart type
    if "x_axis" in top_recommendation:
        config["x_axis"] = {
            "field": top_recommendation["x_axis"],
            "label": top_recommendation["x_axis"].replace("_", " ").title()
        }

    if "y_axis" in top_recommendation:
        config["y_axis"] = {
            "field": top_recommendation["y_axis"],
            "label": top_recommendation["y_axis"].replace("_", " ").title()
        }

    if "variable" in top_recommendation:
        config["variable"] = top_recommendation["variable"]

    if "category" in top_recommendation:
        config["category"] = top_recommendation["category"]

    # Add styling suggestions
    config["styling"] = {
        "width": 800,
        "height": 400,
        "theme": "modern",
        "color_scheme": "blue"
    }

    return config
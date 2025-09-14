# tools/analyze/business_insights/impl.py - Generate actionable business insights from reconciled data

def execute(inputs, context):
    """Generate comprehensive business insights and actionable recommendations"""

    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        import json
    except ImportError as e:
        return {"error": f"Required library not available: {e}. Install with: pip install pandas numpy"}

    customer_data = inputs["customer_data"]
    conflict_report = inputs.get("conflict_report", {})
    focus_areas = inputs.get("focus_areas", ["revenue", "retention", "satisfaction", "growth"])

    # Convert to pandas DataFrame
    df = pd.DataFrame(customer_data["rows"], columns=customer_data["header"])

    # Generate comprehensive insights
    executive_summary = _generate_executive_summary(df, conflict_report)
    action_items = _generate_action_items(df, focus_areas)
    risk_analysis = _analyze_risks(df)
    opportunities = _identify_opportunities(df)

    return {
        "executive_summary": executive_summary,
        "action_items": action_items,
        "risk_analysis": risk_analysis,
        "opportunities": opportunities
    }


def _generate_executive_summary(df, conflict_report):
    """Generate high-level executive summary with key metrics"""
    total_customers = len(df)
    total_revenue = _safe_sum(df.get('revenue', []))
    active_customers = len(df[df.get('status', '') == 'active']) if 'status' in df.columns else 0

    # Customer health metrics
    support_issues = _safe_sum(df.get('support_issues', []))
    angry_customers = len(df[df.get('sentiment', '') == 'angry']) if 'sentiment' in df.columns else 0

    # Data quality metrics
    data_quality_score = _calculate_data_quality_score(df, conflict_report)

    summary = {
        "total_customers": int(total_customers),
        "total_revenue": float(total_revenue),
        "active_customers": int(active_customers),
        "customer_health": {
            "satisfaction_risk": int(angry_customers),
            "support_burden": int(support_issues),
            "retention_rate": round((active_customers / total_customers * 100) if total_customers > 0 else 0, 1)
        },
        "data_quality": {
            "overall_score": round(data_quality_score, 1),
            "conflicts_resolved": conflict_report.get("conflicts_resolved", 0),
            "duplicates_cleaned": conflict_report.get("duplicates_found", 0)
        },
        "revenue_metrics": {
            "average_per_customer": round(total_revenue / total_customers, 2) if total_customers > 0 else 0,
            "high_value_customers": len(df[_safe_to_numeric(df.get('revenue', [])) > 50000]) if 'revenue' in df.columns else 0
        }
    }

    return summary


def _generate_action_items(df, focus_areas):
    """Generate prioritized actionable recommendations"""
    actions = []

    if 'revenue' in focus_areas:
        actions.extend(_revenue_actions(df))

    if 'retention' in focus_areas:
        actions.extend(_retention_actions(df))

    if 'satisfaction' in focus_areas:
        actions.extend(_satisfaction_actions(df))

    if 'growth' in focus_areas:
        actions.extend(_growth_actions(df))

    # Sort by priority and impact
    actions.sort(key=lambda x: (x.get('priority', 3), -x.get('impact_score', 0)))

    return actions[:10]  # Return top 10 actions


def _revenue_actions(df):
    """Generate revenue-focused action items"""
    actions = []

    # Failed payment recovery
    if 'payment_status' in df.columns:
        failed_payments = df[df['payment_status'] == 'failed']
        if not failed_payments.empty:
            potential_recovery = _safe_sum(failed_payments.get('revenue', []))
            actions.append({
                "category": "revenue_recovery",
                "title": "Recover Failed Payments",
                "description": f"Contact {len(failed_payments)} customers with failed payments",
                "impact": f"Potential recovery: ${potential_recovery:,.0f}",
                "priority": 1,
                "impact_score": potential_recovery,
                "timeline": "immediate",
                "effort": "medium",
                "affected_customers": len(failed_payments)
            })

    # High-value inactive customers
    if 'status' in df.columns and 'revenue' in df.columns:
        inactive_high_value = df[
            (df['status'] == 'inactive') &
            (_safe_to_numeric(df['revenue']) > 25000)
        ]
        if not inactive_high_value.empty:
            at_risk_revenue = _safe_sum(inactive_high_value['revenue'])
            actions.append({
                "category": "retention",
                "title": "Re-engage High-Value Inactive Customers",
                "description": f"Launch retention campaign for {len(inactive_high_value)} high-value inactive customers",
                "impact": f"Revenue at risk: ${at_risk_revenue:,.0f}",
                "priority": 1,
                "impact_score": at_risk_revenue,
                "timeline": "1-2 weeks",
                "effort": "high",
                "affected_customers": len(inactive_high_value)
            })

    return actions


def _retention_actions(df):
    """Generate customer retention action items"""
    actions = []

    # Customers without recent contact
    if 'last_contact' in df.columns:
        # Simplistic check for old dates (contains "2023" vs "2024")
        old_contact = df[df['last_contact'].astype(str).str.contains('2023', na=False)]
        if not old_contact.empty:
            actions.append({
                "category": "retention",
                "title": "Re-establish Contact with Dormant Customers",
                "description": f"Reach out to {len(old_contact)} customers with no recent contact",
                "impact": "Prevent churn, gather feedback",
                "priority": 2,
                "impact_score": len(old_contact) * 1000,  # Estimated value per customer
                "timeline": "2-4 weeks",
                "effort": "medium",
                "affected_customers": len(old_contact)
            })

    return actions


def _satisfaction_actions(df):
    """Generate customer satisfaction action items"""
    actions = []

    # Address angry customers immediately
    if 'sentiment' in df.columns:
        angry_customers = df[df['sentiment'] == 'angry']
        if not angry_customers.empty:
            actions.append({
                "category": "satisfaction",
                "title": "Emergency Customer Recovery",
                "description": f"Immediate intervention for {len(angry_customers)} angry customers",
                "impact": "Prevent churn, reputation damage",
                "priority": 1,
                "impact_score": len(angry_customers) * 5000,  # High impact score
                "timeline": "24-48 hours",
                "effort": "high",
                "affected_customers": len(angry_customers)
            })

        # Proactive outreach to concerned customers
        concerned_customers = df[df['sentiment'] == 'concerned']
        if not concerned_customers.empty:
            actions.append({
                "category": "satisfaction",
                "title": "Proactive Support for Concerned Customers",
                "description": f"Preventive outreach to {len(concerned_customers)} concerned customers",
                "impact": "Prevent escalation to angry state",
                "priority": 2,
                "impact_score": len(concerned_customers) * 2000,
                "timeline": "1 week",
                "effort": "medium",
                "affected_customers": len(concerned_customers)
            })

    return actions


def _growth_actions(df):
    """Generate growth and upsell action items"""
    actions = []

    # Identify upsell opportunities
    if 'revenue_impact' in df.columns:
        upsell_opportunities = df[
            df['revenue_impact'].astype(str).str.contains('upsell', case=False, na=False)
        ]
        if not upsell_opportunities.empty:
            # Extract potential upsell values
            potential_value = 0
            for impact in upsell_opportunities['revenue_impact']:
                numbers = [float(s) for s in str(impact).split() if s.replace('k', '').replace('$', '').replace(',', '').isdigit()]
                if numbers:
                    potential_value += numbers[0] * (1000 if 'k' in str(impact).lower() else 1)

            actions.append({
                "category": "growth",
                "title": "Execute Upsell Campaign",
                "description": f"Target {len(upsell_opportunities)} customers expressing upgrade interest",
                "impact": f"Potential revenue: ${potential_value:,.0f}",
                "priority": 2,
                "impact_score": potential_value,
                "timeline": "2-4 weeks",
                "effort": "medium",
                "affected_customers": len(upsell_opportunities)
            })

    return actions


def _analyze_risks(df):
    """Analyze business risks and provide mitigation strategies"""
    risks = {
        "revenue_risks": [],
        "customer_risks": [],
        "operational_risks": []
    }

    # Revenue concentration risk
    if 'revenue' in df.columns:
        revenue_values = _safe_to_numeric(df['revenue'])
        total_revenue = revenue_values.sum()
        if total_revenue > 0:
            # Check for revenue concentration (top 20% of customers)
            sorted_revenue = revenue_values.sort_values(ascending=False)
            top_20_pct_count = max(1, len(sorted_revenue) // 5)
            top_20_pct_revenue = sorted_revenue.head(top_20_pct_count).sum()
            concentration_ratio = (top_20_pct_revenue / total_revenue) * 100

            if concentration_ratio > 60:
                risks["revenue_risks"].append({
                    "risk": "High Revenue Concentration",
                    "description": f"{concentration_ratio:.1f}% of revenue from top 20% of customers",
                    "severity": "high" if concentration_ratio > 80 else "medium",
                    "mitigation": "Diversify customer base, focus on mid-tier customer growth"
                })

    # Customer satisfaction risk
    if 'sentiment' in df.columns:
        total_customers = len(df)
        negative_sentiment = len(df[df['sentiment'].isin(['angry', 'frustrated', 'concerned'])])
        if negative_sentiment > 0:
            negative_ratio = (negative_sentiment / total_customers) * 100
            risks["customer_risks"].append({
                "risk": "Customer Satisfaction Decline",
                "description": f"{negative_ratio:.1f}% of customers show negative sentiment",
                "severity": "high" if negative_ratio > 20 else "medium",
                "mitigation": "Implement customer success program, improve support processes"
            })

    # Payment failure risk
    if 'payment_status' in df.columns:
        failed_payments = len(df[df['payment_status'] == 'failed'])
        if failed_payments > 0:
            failure_rate = (failed_payments / len(df)) * 100
            risks["operational_risks"].append({
                "risk": "Payment Processing Issues",
                "description": f"{failure_rate:.1f}% payment failure rate",
                "severity": "high" if failure_rate > 10 else "medium",
                "mitigation": "Review payment methods, implement retry logic, update customer payment info"
            })

    return risks


def _identify_opportunities(df):
    """Identify growth and business opportunities"""
    opportunities = []

    # Market expansion based on successful customers
    if 'company' in df.columns and 'revenue' in df.columns:
        high_value_companies = df[_safe_to_numeric(df['revenue']) > 50000]
        if not high_value_companies.empty:
            # Analyze company patterns
            company_types = high_value_companies['company'].astype(str).apply(
                lambda x: 'Corp' if 'corp' in x.lower() else
                         'Inc' if 'inc' in x.lower() else
                         'LLC' if 'llc' in x.lower() else 'Other'
            ).value_counts()

            if len(company_types) > 0:
                top_segment = company_types.index[0]
                opportunities.append({
                    "type": "market_expansion",
                    "title": f"Target {top_segment} Segment",
                    "description": f"High-value customers concentrated in {top_segment} companies",
                    "potential": "high",
                    "effort": "medium",
                    "timeline": "3-6 months"
                })

    # Product expansion based on support tickets
    if 'revenue_impact' in df.columns:
        interested_customers = df[
            df['revenue_impact'].astype(str).str.contains('interested|upgrade|expand', case=False, na=False)
        ]
        if not interested_customers.empty:
            opportunities.append({
                "type": "product_expansion",
                "title": "Develop Premium Features",
                "description": f"{len(interested_customers)} customers expressed interest in upgrades",
                "potential": "high",
                "effort": "high",
                "timeline": "6-12 months"
            })

    # Process improvement opportunities
    if 'support_issues' in df.columns:
        support_heavy = df[_safe_to_numeric(df.get('support_issues', [])) > 2]
        if not support_heavy.empty:
            opportunities.append({
                "type": "operational_efficiency",
                "title": "Reduce Support Burden",
                "description": f"{len(support_heavy)} customers with high support needs",
                "potential": "medium",
                "effort": "medium",
                "timeline": "1-3 months",
                "approach": "Self-service tools, documentation improvement, proactive communication"
            })

    return opportunities


def _calculate_data_quality_score(df, conflict_report):
    """Calculate overall data quality score (0-100)"""
    score = 100.0
    total_records = len(df)

    if total_records == 0:
        return 0.0

    # Penalize for missing data
    for col in ['name', 'email', 'phone', 'company']:
        if col in df.columns:
            missing_count = df[col].isna().sum() + (df[col] == "").sum()
            missing_ratio = missing_count / total_records
            score -= missing_ratio * 20  # Max 20 points penalty per critical field

    # Reward conflict resolution
    conflicts_resolved = conflict_report.get("conflicts_resolved", 0)
    if conflicts_resolved > 0:
        score += min(conflicts_resolved * 2, 10)  # Max 10 bonus points

    return max(0.0, min(100.0, score))


def _safe_to_numeric(series):
    """Safely convert series to numeric, handling errors"""
    try:
        return pd.to_numeric(series, errors='coerce').fillna(0)
    except:
        return pd.Series([0] * len(series))


def _safe_sum(values):
    """Safely sum values, handling non-numeric data"""
    try:
        numeric_values = pd.to_numeric(values, errors='coerce')
        return numeric_values.sum()
    except:
        return 0.0
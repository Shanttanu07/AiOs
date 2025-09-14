# tools/flightfixer/refund_analyzer/impl.py - Apply DOT 2024 refund rules

def execute(inputs, context):
    """Apply Department of Transportation 2024 refund rules to determine passenger eligibility"""

    try:
        import pandas as pd
        from datetime import datetime
        import re
    except ImportError as e:
        return {"error": f"Required library not available: {e}"}

    matched_flights_data = inputs["matched_flights"]
    dot_rules_config = inputs.get("dot_rules_config", {
        "domestic_significant_delay_minutes": 180,  # 3 hours
        "international_significant_delay_minutes": 360,  # 6 hours
        "automatic_refund_required": True,
        "baggage_delay_hours": 12,
        "wifi_refund_threshold_percent": 50
    })

    if not matched_flights_data["rows"]:
        return {
            "refund_decisions": {"header": [], "rows": []},
            "refund_summary": {"total_cases": 0, "eligible_refunds": 0}
        }

    # Convert to DataFrame
    df = pd.DataFrame(matched_flights_data["rows"], columns=matched_flights_data["header"])
    print(f"[refund_analyzer] Analyzing {len(df)} matched flight complaints")

    # DOT 2024 Final Rule: Refunds and Other Consumer Protections
    # Federal Register: April 26, 2024 (89 FR 32886)
    dot_rule_citations = {
        "cancelled_flight": "14 CFR 259.5(b)(1) - Automatic refund required for cancelled flights",
        "significant_delay_domestic": f"14 CFR 259.5(b)(2) - Domestic flights delayed {dot_rules_config['domestic_significant_delay_minutes']}+ minutes",
        "significant_delay_international": f"14 CFR 259.5(b)(2) - International flights delayed {dot_rules_config['international_significant_delay_minutes']}+ minutes",
        "schedule_change": "14 CFR 259.5(b)(3) - Significant schedule changes",
        "baggage_delay": f"14 CFR 259.8 - Baggage delayed {dot_rules_config['baggage_delay_hours']}+ hours",
        "ancillary_services": "14 CFR 259.6 - Ancillary services not provided (WiFi, seat assignments, etc.)",
        "downgrade_service": "14 CFR 259.7 - Involuntary downgrade in service class"
    }

    refund_decisions = []
    summary_stats = {
        "total_cases": len(df),
        "eligible_refunds": 0,
        "cancelled_flights": 0,
        "significant_delays": 0,
        "baggage_issues": 0,
        "ancillary_issues": 0,
        "by_airline": {},
        "total_estimated_refund_amount": 0.0
    }

    for idx, row in df.iterrows():
        case = row.to_dict()

        # Initialize decision record
        decision = {
            **case,  # Include all original data
            'refund_eligible': False,
            'refund_reason': None,
            'dot_rule_citation': None,
            'evidence_summary': None,
            'estimated_refund_amount': 0.0,
            'refund_type': None,  # 'cash', 'voucher', 'partial'
            'customer_action_required': None,
            'airline_deadline_days': None,
            'confidence_level': 'high'  # high, medium, low
        }

        # Extract flight performance data
        is_cancelled = case.get('bts_cancelled', False)
        arr_delay_minutes = float(case.get('bts_arr_delay_minutes', 0))
        dep_delay_minutes = float(case.get('bts_dep_delay_minutes', 0))
        significant_delay = case.get('bts_significant_delay', False)

        # Estimate ticket price (simplified - in reality would need fare data)
        estimated_ticket_price = 350.0  # Average domestic ticket price
        origin = case.get('bts_origin', '')
        destination = case.get('bts_destination', '')

        # Adjust estimate based on route (simplified logic)
        if origin and destination:
            # International routes (rough detection)
            international_airports = ['LHR', 'CDG', 'NRT', 'ICN', 'FRA', 'AMS', 'YYZ', 'YVR']
            if origin in international_airports or destination in international_airports:
                estimated_ticket_price = 800.0
                delay_threshold = dot_rules_config['international_significant_delay_minutes']
            else:
                # Domestic routes
                delay_threshold = dot_rules_config['domestic_significant_delay_minutes']

                # High-traffic routes typically more expensive
                high_traffic_airports = ['JFK', 'LAX', 'ORD', 'ATL', 'DFW', 'SFO', 'LAS', 'SEA']
                if origin in high_traffic_airports or destination in high_traffic_airports:
                    estimated_ticket_price = 450.0

        decision['estimated_refund_amount'] = estimated_ticket_price

        # Apply DOT refund rules
        refund_reasons = []
        rule_citations = []
        evidence_points = []

        # Rule 1: Cancelled flights
        if is_cancelled:
            decision['refund_eligible'] = True
            refund_reasons.append('Flight cancellation')
            rule_citations.append(dot_rule_citations['cancelled_flight'])
            evidence_points.append(f"BTS data confirms flight was cancelled")
            decision['refund_type'] = 'cash'
            decision['airline_deadline_days'] = 7
            summary_stats['cancelled_flights'] += 1

        # Rule 2: Significant delays
        elif arr_delay_minutes >= delay_threshold:
            decision['refund_eligible'] = True
            hours_delayed = arr_delay_minutes / 60
            refund_reasons.append(f'Significant delay ({hours_delayed:.1f} hours)')

            if delay_threshold == dot_rules_config['domestic_significant_delay_minutes']:
                rule_citations.append(dot_rule_citations['significant_delay_domestic'])
            else:
                rule_citations.append(dot_rule_citations['significant_delay_international'])

            evidence_points.append(f"BTS data shows {arr_delay_minutes} minute arrival delay")
            decision['refund_type'] = 'cash'
            decision['airline_deadline_days'] = 7
            summary_stats['significant_delays'] += 1

        # Rule 3: Baggage issues (from tweet content analysis)
        tweet_text = case.get('original_text', '').lower()
        baggage_keywords = ['lost bag', 'baggage', 'luggage', 'suitcase', 'checked bag']
        if any(keyword in tweet_text for keyword in baggage_keywords):
            # This would typically require additional baggage tracking data
            # For demo purposes, we'll flag as potential baggage issue
            if not decision['refund_eligible']:
                decision['confidence_level'] = 'medium'
                decision['customer_action_required'] = 'Provide baggage claim tickets and tracking information'

            refund_reasons.append('Potential baggage delay/loss')
            rule_citations.append(dot_rule_citations['baggage_delay'])
            evidence_points.append("Tweet mentions baggage issues")
            summary_stats['baggage_issues'] += 1

            # Baggage refund is typically for fees, not full ticket
            if 'bag' in tweet_text and 'fee' in tweet_text:
                decision['estimated_refund_amount'] = min(decision['estimated_refund_amount'], 75.0)  # Typical bag fee

        # Rule 4: Ancillary services (WiFi, seat assignments, etc.)
        ancillary_keywords = ['wifi', 'internet', 'seat assignment', 'meal', 'entertainment']
        if any(keyword in tweet_text for keyword in ancillary_keywords):
            if 'wifi' in tweet_text or 'internet' in tweet_text:
                refund_reasons.append('WiFi service issues')
                rule_citations.append(dot_rule_citations['ancillary_services'])
                evidence_points.append("Tweet mentions WiFi/internet problems")
                decision['estimated_refund_amount'] = min(decision['estimated_refund_amount'], 25.0)  # Typical WiFi fee
                summary_stats['ancillary_issues'] += 1

        # Determine final eligibility
        if refund_reasons:
            if not decision['refund_eligible']:
                # Ancillary or baggage issues might be eligible for partial refunds
                decision['refund_eligible'] = True
                decision['refund_type'] = 'partial'
                decision['airline_deadline_days'] = 30

            decision['refund_reason'] = '; '.join(refund_reasons)
            decision['dot_rule_citation'] = '; '.join(rule_citations)
            decision['evidence_summary'] = '; '.join(evidence_points)

            summary_stats['eligible_refunds'] += 1
            summary_stats['total_estimated_refund_amount'] += decision['estimated_refund_amount']

        else:
            # No clear refund eligibility
            decision['refund_eligible'] = False
            decision['refund_reason'] = 'No DOT refund criteria met'
            decision['evidence_summary'] = 'Flight performance within normal parameters'
            decision['customer_action_required'] = 'Contact airline customer service for voluntary compensation'

        # Airline-specific tracking
        carrier = case.get('bts_carrier', 'Unknown')
        if carrier not in summary_stats['by_airline']:
            summary_stats['by_airline'][carrier] = {
                'total_cases': 0,
                'eligible_refunds': 0,
                'estimated_refund_amount': 0.0
            }

        summary_stats['by_airline'][carrier]['total_cases'] += 1
        if decision['refund_eligible']:
            summary_stats['by_airline'][carrier]['eligible_refunds'] += 1
            summary_stats['by_airline'][carrier]['estimated_refund_amount'] += decision['estimated_refund_amount']

        refund_decisions.append(decision)

    # Calculate summary percentages
    if summary_stats['total_cases'] > 0:
        summary_stats['refund_eligibility_rate'] = summary_stats['eligible_refunds'] / summary_stats['total_cases']
        summary_stats['average_refund_amount'] = (
            summary_stats['total_estimated_refund_amount'] / summary_stats['eligible_refunds']
            if summary_stats['eligible_refunds'] > 0 else 0
        )

    # Convert to table format
    if refund_decisions:
        decisions_df = pd.DataFrame(refund_decisions)
        refund_decisions_table = {
            "header": list(decisions_df.columns),
            "rows": decisions_df.values.tolist(),
            "metadata": {
                "dot_rules_applied": dot_rules_config,
                "rule_citations": dot_rule_citations,
                "analysis_date": datetime.now().isoformat(),
                "regulatory_source": "14 CFR Part 259 - DOT Final Rule (April 26, 2024)"
            }
        }
    else:
        refund_decisions_table = {"header": [], "rows": []}

    print(f"[refund_analyzer] {summary_stats['eligible_refunds']}/{summary_stats['total_cases']} cases eligible for refunds")
    print(f"[refund_analyzer] Estimated total refund amount: ${summary_stats['total_estimated_refund_amount']:,.2f}")

    return {
        "refund_decisions": refund_decisions_table,
        "refund_summary": summary_stats
    }
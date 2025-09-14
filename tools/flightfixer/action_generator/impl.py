# tools/flightfixer/action_generator/impl.py - Generate actionable outputs from refund analysis

def execute(inputs, context):
    """Generate refund claims, customer replies, and Slack notifications"""

    try:
        import pandas as pd
        from datetime import datetime, timedelta
        import json
        import os
    except ImportError as e:
        return {"error": f"Required library not available: {e}"}

    refund_decisions_data = inputs["refund_decisions"]
    unmatched_tweets_data = inputs.get("unmatched_tweets", {"rows": [], "header": []})
    output_config = inputs.get("output_config", {
        "claims_format": "jsonl",
        "replies_format": "markdown",
        "slack_format": "blocks",
        "include_legal_disclaimer": True
    })

    # Convert to DataFrames
    refund_df = pd.DataFrame(refund_decisions_data["rows"], columns=refund_decisions_data["header"]) if refund_decisions_data["rows"] else pd.DataFrame()
    unmatched_df = pd.DataFrame(unmatched_tweets_data["rows"], columns=unmatched_tweets_data["header"]) if unmatched_tweets_data["rows"] else pd.DataFrame()

    # Generate outputs
    outputs = {
        "refund_claims": None,
        "customer_replies": None,
        "slack_notification": None,
        "action_summary": {
            "generated_at": datetime.now().isoformat(),
            "total_claims": 0,
            "total_replies": 0,
            "eligible_refund_amount": 0.0,
            "requires_manual_review": 0
        }
    }

    # 1. Generate Refund Claims (JSONL format)
    claims_data = []
    eligible_refunds = refund_df[refund_df['refund_eligible'] == True] if not refund_df.empty else pd.DataFrame()

    for idx, case in eligible_refunds.iterrows():
        claim = {
            "claim_id": f"RFC-{datetime.now().strftime('%Y%m%d')}-{idx:04d}",
            "timestamp": datetime.now().isoformat(),
            "passenger": {
                "twitter_handle": case.get('user', 'Unknown'),
                "contact_method": "twitter_dm"
            },
            "flight": {
                "carrier": case.get('bts_carrier', ''),
                "flight_number": case.get('bts_flight_num', ''),
                "date": case.get('bts_date', ''),
                "origin": case.get('bts_origin', ''),
                "destination": case.get('bts_destination', '')
            },
            "incident": {
                "type": case.get('incident_type', ''),
                "description": case.get('original_text', ''),
                "bts_cancelled": case.get('bts_cancelled', False),
                "bts_delay_minutes": case.get('bts_arr_delay_minutes', 0)
            },
            "refund": {
                "eligible": True,
                "reason": case.get('refund_reason', ''),
                "dot_citation": case.get('dot_rule_citation', ''),
                "estimated_amount": case.get('estimated_refund_amount', 0.0),
                "refund_type": case.get('refund_type', 'cash'),
                "deadline_days": case.get('airline_deadline_days', 7)
            },
            "evidence": {
                "bts_data_match": True,
                "match_confidence": case.get('match_confidence', 0.0),
                "summary": case.get('evidence_summary', '')
            },
            "status": "pending_review",
            "priority": "high" if case.get('refund_type') == 'cash' else "medium"
        }
        claims_data.append(claim)

    outputs["refund_claims"] = {
        "format": "jsonl",
        "count": len(claims_data),
        "claims": claims_data
    }

    # 2. Generate Customer Reply Drafts
    replies_data = []

    # Replies for eligible refunds
    for idx, case in eligible_refunds.iterrows():
        twitter_handle = case.get('user', 'Valued Customer')
        carrier = case.get('bts_carrier', 'the airline')
        flight_info = f"{case.get('bts_carrier', '')}{case.get('bts_flight_num', '')} on {case.get('bts_date', '')}"
        refund_amount = case.get('estimated_refund_amount', 0.0)
        deadline = case.get('airline_deadline_days', 7)

        reply_content = f"""Hello @{twitter_handle},

We've reviewed your complaint about flight {flight_info} and determined that you are eligible for a refund under the Department of Transportation's 2024 refund rules.

**Your Refund Details:**
• Flight: {flight_info}
• Reason: {case.get('refund_reason', 'Flight disruption')}
• Estimated Amount: ${refund_amount:.2f}
• Refund Type: {case.get('refund_type', 'Cash').title()}

**Legal Basis:**
Under {case.get('dot_rule_citation', '14 CFR 259.5')}, airlines must provide automatic cash refunds for cancelled flights and significant delays. Your flight qualifies based on official Bureau of Transportation Statistics data.

**Next Steps:**
1. The airline must process your refund within {deadline} days
2. No additional documentation should be required for this automatic refund
3. If you don't receive your refund, you can file a complaint with DOT at aviation.consumerprotection.gov

**Evidence:**
{case.get('evidence_summary', 'Flight performance confirmed via official BTS data')}

We're here to help ensure you receive the compensation you're entitled to under federal regulations.

Best regards,
FlightFixer Customer Advocacy"""

        if output_config.get("include_legal_disclaimer", True):
            reply_content += """

---
*Disclaimer: This analysis is based on publicly available flight data and DOT regulations. For official refund requests, contact the airline directly. This is not legal advice.*"""

        replies_data.append({
            "recipient": twitter_handle,
            "flight": flight_info,
            "refund_eligible": True,
            "content": reply_content,
            "priority": "high",
            "estimated_refund": refund_amount
        })

    # Replies for unmatched/need more info cases
    for idx, case in unmatched_df.iterrows():
        twitter_handle = case.get('user', 'Valued Customer')
        match_status = case.get('match_status', 'no_matches')

        if match_status == 'insufficient_data':
            reply_content = f"""Hello @{twitter_handle},

We'd like to help you determine if you're eligible for a refund under the DOT's 2024 automatic refund rules. However, we need more specific information about your flight to match it with official performance data.

**Please provide:**
• Flight number (e.g., UA123, AA456)
• Flight date (MM/DD/YYYY)
• Departure and arrival airports (3-letter codes if possible)

**Why this matters:**
The DOT's new rules require automatic cash refunds for:
• Cancelled flights
• Domestic flights delayed 3+ hours
• International flights delayed 6+ hours

Once you provide the flight details, we can check official Bureau of Transportation Statistics data to determine your eligibility and help you get the refund you may be entitled to.

**Your Rights:**
Under 14 CFR 259.5, airlines must provide automatic refunds within 7 days for eligible disruptions - no questions asked.

Reply with your flight details and we'll analyze your case immediately.

Best regards,
FlightFixer Customer Advocacy"""

        elif match_status == 'low_confidence':
            suggested_flight = case.get('suggested_flight', 'similar flight')
            reply_content = f"""Hello @{twitter_handle},

We found a potential match for your complaint ({suggested_flight}), but we want to confirm the details before providing refund guidance.

**Please verify:**
• Is {suggested_flight} the correct flight?
• Are the departure/arrival cities correct?

**If this is your flight:**
Based on official BTS data, this flight experienced significant disruptions that may qualify for automatic DOT refunds. We'll provide detailed eligibility analysis once confirmed.

**Your Rights:**
The DOT's 2024 rules require automatic cash refunds for cancelled flights and significant delays. Airlines have 7 days to process eligible refunds.

Please confirm the flight details so we can provide accurate refund guidance.

Best regards,
FlightFixer Customer Advocacy"""

        else:
            reply_content = f"""Hello @{twitter_handle},

We've reviewed your flight complaint but couldn't find a matching flight in the official Bureau of Transportation Statistics database for the timeframe mentioned.

**This could mean:**
• The flight date/number needs clarification
• The issue occurred outside our current data range
• The flight may not have qualified for DOT automatic refunds

**Still have options:**
Even if not eligible for automatic DOT refunds, you may still be entitled to:
• Voluntary airline compensation
• Vouchers or future flight credits
• Refunds under the airline's customer service policy

**Next steps:**
1. Contact {case.get('airline', 'the airline')} customer service directly
2. Reference DOT regulations and ask about voluntary compensation
3. File a DOT complaint at aviation.consumerprotection.gov if unsatisfied

We recommend being persistent - airlines often provide compensation even when not legally required.

Best regards,
FlightFixer Customer Advocacy"""

        replies_data.append({
            "recipient": twitter_handle,
            "flight": case.get('flight_number', 'Unknown'),
            "refund_eligible": False,
            "content": reply_content,
            "priority": "medium",
            "requires_followup": True
        })

    outputs["customer_replies"] = {
        "format": "markdown",
        "count": len(replies_data),
        "replies": replies_data
    }

    # 3. Generate Slack Notification (Block Kit format)
    eligible_count = len(eligible_refunds)
    unmatched_count = len(unmatched_df)
    total_refund_amount = eligible_refunds['estimated_refund_amount'].sum() if not eligible_refunds.empty else 0.0

    # Airline breakdown
    airline_stats = {}
    if not eligible_refunds.empty:
        airline_breakdown = eligible_refunds.groupby('bts_carrier').agg({
            'estimated_refund_amount': ['count', 'sum']
        }).round(2)

        for carrier in airline_breakdown.index:
            count = int(airline_breakdown.loc[carrier, ('estimated_refund_amount', 'count')])
            amount = float(airline_breakdown.loc[carrier, ('estimated_refund_amount', 'sum')])
            airline_stats[carrier] = {"cases": count, "amount": amount}

    slack_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛫 FlightFixer Daily Report"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Cases Processed:* {eligible_count + unmatched_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Refund Eligible:* {eligible_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Need Manual Review:* {unmatched_count}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Estimated Refunds:* ${total_refund_amount:,.2f}"
                }
            ]
        }
    ]

    if airline_stats:
        airline_text = "\\n".join([f"• {carrier}: {stats['cases']} cases, ${stats['amount']:,.2f}"
                                 for carrier, stats in sorted(airline_stats.items())])
        slack_blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Breakdown by Airline:*\\n{airline_text}"
            }
        })

    if unmatched_count > 0:
        slack_blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *{unmatched_count} cases require manual review* - insufficient flight data or low confidence matches."
            }
        })

    slack_blocks.extend([
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M UTC')} | Based on DOT 2024 refund rules"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Review Claims"
                    },
                    "style": "primary",
                    "url": "https://flightfixer.internal/claims"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Manual Review Queue"
                    },
                    "url": "https://flightfixer.internal/manual-review"
                }
            ]
        }
    ])

    outputs["slack_notification"] = {
        "format": "blocks",
        "webhook_ready": True,
        "blocks": slack_blocks
    }

    # 4. Action Summary
    outputs["action_summary"] = {
        "generated_at": datetime.now().isoformat(),
        "total_claims": len(claims_data),
        "total_replies": len(replies_data),
        "eligible_refund_amount": float(total_refund_amount),
        "requires_manual_review": unmatched_count,
        "high_priority_cases": eligible_count,
        "estimated_airline_liability": float(total_refund_amount),
        "dot_compliance_rate": float(eligible_count / (eligible_count + unmatched_count)) if (eligible_count + unmatched_count) > 0 else 0,
        "next_steps": [
            f"Review {eligible_count} eligible refund claims",
            f"Send {len([r for r in replies_data if r['refund_eligible']])} refund notification replies",
            f"Follow up on {unmatched_count} cases needing more information",
            "Monitor airline response times for DOT compliance"
        ]
    }

    print(f"[action_generator] Generated {len(claims_data)} refund claims worth ${total_refund_amount:,.2f}")
    print(f"[action_generator] Created {len(replies_data)} customer reply drafts")
    print(f"[action_generator] Prepared Slack notification with {len(slack_blocks)} blocks")

    return outputs
# tools/flightfixer/flight_matcher/impl.py - Match tweets with BTS flight data

def execute(inputs, context):
    """Match parsed complaint tweets with official BTS flight performance data"""

    try:
        import pandas as pd
        from datetime import datetime, timedelta
        import re
        from fuzzywuzzy import fuzz
    except ImportError as e:
        return {"error": f"Required library not available: {e}. Install with: pip install fuzzywuzzy python-levenshtein"}

    parsed_tweets_data = inputs["parsed_tweets"]
    flight_performance_data = inputs["flight_performance"]
    match_confidence_threshold = inputs.get("match_confidence_threshold", 0.7)
    date_tolerance_days = inputs.get("date_tolerance_days", 1)

    # Convert tables to DataFrames
    tweets_df = pd.DataFrame(parsed_tweets_data["rows"], columns=parsed_tweets_data["header"])
    flights_df = pd.DataFrame(flight_performance_data["rows"], columns=flight_performance_data["header"])

    print(f"[flight_matcher] Matching {len(tweets_df)} tweets against {len(flights_df)} flight records")

    matched_results = []
    unmatched_results = []
    match_stats = {
        "total_tweets": len(tweets_df),
        "successful_matches": 0,
        "high_confidence_matches": 0,
        "low_confidence_matches": 0,
        "no_matches": 0,
        "confidence_distribution": {"0.9+": 0, "0.8-0.9": 0, "0.7-0.8": 0, "0.6-0.7": 0, "<0.6": 0}
    }

    # Preprocess BTS data for faster matching
    if 'FL_DATE' in flights_df.columns:
        flights_df['FL_DATE'] = pd.to_datetime(flights_df['FL_DATE'])
    if 'DATE_STR' in flights_df.columns:
        flights_df['FL_DATE_STR'] = flights_df['DATE_STR']
    else:
        flights_df['FL_DATE_STR'] = flights_df['FL_DATE'].dt.strftime('%Y-%m-%d')

    # Create flight lookup dictionary for faster matching
    flight_lookup = {}
    for idx, flight_row in flights_df.iterrows():
        flight_key = flight_row.get('FLIGHT_KEY', f"{flight_row.get('CARRIER', '')}{flight_row.get('FL_NUM', '')}")
        date_str = flight_row['FL_DATE_STR']
        lookup_key = f"{flight_key}_{date_str}"
        flight_lookup[lookup_key] = {
            'index': idx,
            'data': flight_row.to_dict(),
            'carrier': flight_row.get('CARRIER', ''),
            'flight_num': str(flight_row.get('FL_NUM', '')),
            'date': date_str,
            'origin': flight_row.get('ORIGIN', ''),
            'destination': flight_row.get('DEST', '')
        }

    for tweet_idx, tweet_row in tweets_df.iterrows():
        tweet_data = tweet_row.to_dict()

        best_match = None
        best_confidence = 0.0
        match_reasons = []

        # Extract tweet details
        tweet_flight_number = tweet_data.get('flight_number', '')
        tweet_date = tweet_data.get('flight_date', '')
        tweet_origin = tweet_data.get('origin', '')
        tweet_destination = tweet_data.get('destination', '')

        if not tweet_flight_number and not tweet_origin:
            # No sufficient data for matching
            unmatched_results.append({
                **tweet_data,
                'match_status': 'insufficient_data',
                'match_reason': 'No flight number or airport information found'
            })
            match_stats["no_matches"] += 1
            continue

        # Generate potential flight keys for matching
        potential_matches = []

        # Direct flight number matching
        if tweet_flight_number:
            # Extract carrier and flight number parts
            flight_match = re.match(r'([A-Z]{1,3})(\d+)', tweet_flight_number.upper())
            if flight_match:
                carrier_code, flight_num = flight_match.groups()

                # Try exact date match first
                if tweet_date:
                    lookup_key = f"{carrier_code}{flight_num}_{tweet_date}"
                    if lookup_key in flight_lookup:
                        potential_matches.append((flight_lookup[lookup_key], 1.0, "exact_flight_date"))

                # Try date tolerance matching
                if tweet_date and not potential_matches:
                    try:
                        tweet_datetime = datetime.strptime(tweet_date, '%Y-%m-%d')
                        for days_offset in range(-date_tolerance_days, date_tolerance_days + 1):
                            if days_offset == 0:
                                continue  # Already tried exact match

                            check_date = tweet_datetime + timedelta(days=days_offset)
                            check_date_str = check_date.strftime('%Y-%m-%d')
                            lookup_key = f"{carrier_code}{flight_num}_{check_date_str}"

                            if lookup_key in flight_lookup:
                                confidence_penalty = 0.1 * abs(days_offset)  # Reduce confidence for date differences
                                potential_matches.append((
                                    flight_lookup[lookup_key],
                                    0.9 - confidence_penalty,
                                    f"flight_date_±{abs(days_offset)}d"
                                ))
                    except ValueError:
                        pass

                # If no date, try flight number only (lower confidence)
                if not potential_matches:
                    for lookup_key, flight_data in flight_lookup.items():
                        if flight_data['carrier'] == carrier_code and flight_data['flight_num'] == flight_num:
                            potential_matches.append((flight_data, 0.6, "flight_number_only"))

        # Airport-based matching (fallback)
        if not potential_matches and (tweet_origin or tweet_destination):
            for lookup_key, flight_data in flight_lookup.items():
                airport_match_score = 0.0
                airport_reasons = []

                if tweet_origin and flight_data['origin'] == tweet_origin:
                    airport_match_score += 0.3
                    airport_reasons.append("origin_match")

                if tweet_destination and flight_data['destination'] == tweet_destination:
                    airport_match_score += 0.3
                    airport_reasons.append("destination_match")

                # Date matching for airport-based matches
                if tweet_date and flight_data['date'] == tweet_date:
                    airport_match_score += 0.2
                    airport_reasons.append("date_match")
                elif tweet_date:
                    # Try date tolerance for airport matches
                    try:
                        tweet_datetime = datetime.strptime(tweet_date, '%Y-%m-%d')
                        flight_datetime = datetime.strptime(flight_data['date'], '%Y-%m-%d')
                        days_diff = abs((flight_datetime - tweet_datetime).days)
                        if days_diff <= date_tolerance_days:
                            airport_match_score += max(0.1, 0.2 - 0.05 * days_diff)
                            airport_reasons.append(f"date_±{days_diff}d")
                    except ValueError:
                        pass

                if airport_match_score >= 0.4:  # Minimum threshold for airport-based matching
                    potential_matches.append((
                        flight_data,
                        airport_match_score,
                        f"airport_based_{'+'.join(airport_reasons)}"
                    ))

        # Select best match
        if potential_matches:
            # Sort by confidence score
            potential_matches.sort(key=lambda x: x[1], reverse=True)
            best_flight_data, best_confidence, match_reason = potential_matches[0]

            # Additional confidence adjustments based on consistency
            consistency_bonus = 0.0

            # Check if incident type matches flight performance
            tweet_incident = tweet_data.get('incident_type', '').lower()
            flight_cancelled = best_flight_data['data'].get('IS_CANCELLED', False)
            flight_delayed = best_flight_data['data'].get('SIGNIFICANT_DELAY', False)

            if 'cancel' in tweet_incident and flight_cancelled:
                consistency_bonus += 0.1
            elif 'delay' in tweet_incident and flight_delayed:
                consistency_bonus += 0.1
            elif flight_cancelled or flight_delayed:
                # Flight had issues but tweet doesn't mention them specifically
                consistency_bonus += 0.05

            final_confidence = min(1.0, best_confidence + consistency_bonus)

            if final_confidence >= match_confidence_threshold:
                # High confidence match
                matched_result = {
                    **tweet_data,
                    'match_confidence': final_confidence,
                    'match_reason': match_reason,
                    'match_status': 'matched',
                    'bts_carrier': best_flight_data['data'].get('CARRIER', ''),
                    'bts_flight_num': best_flight_data['data'].get('FL_NUM', ''),
                    'bts_date': best_flight_data['data'].get('DATE_STR', ''),
                    'bts_origin': best_flight_data['data'].get('ORIGIN', ''),
                    'bts_destination': best_flight_data['data'].get('DEST', ''),
                    'bts_cancelled': best_flight_data['data'].get('IS_CANCELLED', False),
                    'bts_significant_delay': best_flight_data['data'].get('SIGNIFICANT_DELAY', False),
                    'bts_refund_eligible': best_flight_data['data'].get('REFUND_ELIGIBLE', False),
                    'bts_arr_delay_minutes': best_flight_data['data'].get('ARR_DELAY_MINUTES', 0),
                    'bts_dep_delay_minutes': best_flight_data['data'].get('DEP_DELAY_MINUTES', 0)
                }
                matched_results.append(matched_result)
                match_stats["successful_matches"] += 1

                if final_confidence >= 0.8:
                    match_stats["high_confidence_matches"] += 1
                else:
                    match_stats["low_confidence_matches"] += 1

            else:
                # Low confidence - needs human review
                unmatched_results.append({
                    **tweet_data,
                    'match_status': 'low_confidence',
                    'match_reason': f'Best match confidence {final_confidence:.2f} below threshold {match_confidence_threshold}',
                    'suggested_flight': f"{best_flight_data['carrier']}{best_flight_data['flight_num']} on {best_flight_data['date']}"
                })
                match_stats["no_matches"] += 1
        else:
            # No potential matches found
            unmatched_results.append({
                **tweet_data,
                'match_status': 'no_matches',
                'match_reason': 'No matching flights found in BTS data'
            })
            match_stats["no_matches"] += 1

        # Update confidence distribution stats
        if best_confidence >= 0.9:
            match_stats["confidence_distribution"]["0.9+"] += 1
        elif best_confidence >= 0.8:
            match_stats["confidence_distribution"]["0.8-0.9"] += 1
        elif best_confidence >= 0.7:
            match_stats["confidence_distribution"]["0.7-0.8"] += 1
        elif best_confidence >= 0.6:
            match_stats["confidence_distribution"]["0.6-0.7"] += 1
        else:
            match_stats["confidence_distribution"]["<0.6"] += 1

    # Convert results to table format
    matched_table = {"header": [], "rows": []}
    unmatched_table = {"header": [], "rows": []}

    if matched_results:
        matched_df = pd.DataFrame(matched_results)
        matched_table = {
            "header": list(matched_df.columns),
            "rows": matched_df.values.tolist(),
            "metadata": {
                "match_config": {
                    "confidence_threshold": match_confidence_threshold,
                    "date_tolerance_days": date_tolerance_days
                }
            }
        }

    if unmatched_results:
        unmatched_df = pd.DataFrame(unmatched_results)
        unmatched_table = {
            "header": list(unmatched_df.columns),
            "rows": unmatched_df.values.tolist(),
            "metadata": {"requires_manual_review": True}
        }

    # Add processing summary to stats
    match_stats["match_rate"] = match_stats["successful_matches"] / match_stats["total_tweets"] if match_stats["total_tweets"] > 0 else 0
    match_stats["processed_at"] = datetime.now().isoformat()

    print(f"[flight_matcher] Matched {match_stats['successful_matches']}/{match_stats['total_tweets']} tweets ({match_stats['match_rate']:.1%})")

    return {
        "matched_flights": matched_table,
        "unmatched_tweets": unmatched_table,
        "match_stats": match_stats
    }
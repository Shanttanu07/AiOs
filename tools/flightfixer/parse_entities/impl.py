# tools/flightfixer/parse_entities/impl.py - Extract flight details from messy complaint tweets

def execute(inputs, context):
    """Extract flight numbers, dates, airports from complaint tweets using regex + LLM fallback"""

    try:
        import pandas as pd
        import re
        from datetime import datetime, timedelta
        import json
    except ImportError as e:
        return {"error": f"Required library not available: {e}"}

    tweets_data = inputs["tweets"]
    confidence_threshold = inputs.get("confidence_threshold", 0.6)
    use_llm_fallback = inputs.get("use_llm_fallback", True)

    # Convert table to DataFrame
    df = pd.DataFrame(tweets_data["rows"], columns=tweets_data["header"])

    # Regex patterns for entity extraction
    patterns = {
        'flight_number': [
            r'\b([A-Z]{2,3})\s*(\d{1,4})\b',  # UA 123, American 1234
            r'\bflight\s+([A-Z]{2,3})\s*(\d{1,4})\b',  # flight UA 123
            r'\b([A-Z]{2,3})(\d{1,4})\b'  # UA123
        ],
        'airports': [
            r'\b([A-Z]{3})\b',  # Three-letter IATA codes
            r'\bfrom\s+([A-Z]{3})\s+to\s+([A-Z]{3})\b',  # from ORD to LAX
            r'\b(ORD|LAX|JFK|LGA|ATL|DFW|DEN|PHX|LAS|SEA|SFO|LAX|MIA|BOS|MSP|DTW|PHL|CLT|PHX|IAH|EWR|MCO|FLL|BWI|DCA|IAD)\b'
        ],
        'dates': [
            r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b',  # MM/DD/YYYY
            r'\b(\d{1,2})/(\d{1,2})\b',  # MM/DD (assume current year)
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})\b',  # Feb 14
            r'\b(yesterday|today|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'
        ],
        'delays': [
            r'(\d+)\s*(hour|hr|h)\s*delay',
            r'delayed\s*(\d+)\s*(hour|hr|h)',
            r'stuck\s*(\d+)\s*(hour|hr|h)',
            r'(\d+)\s*hr\s*(late|delay)'
        ],
        'incidents': [
            r'\b(cancel|cancelled|canceled)\b',
            r'\b(delay|delayed)\b',
            r'\b(missed\s+connection|missed\s+flight)\b',
            r'\b(lost\s+bag|baggage|luggage)\b',
            r'\b(overbook|bumped)\b',
            r'\b(mechanical\s+issue|maintenance)\b'
        ]
    }

    # Common airline code mappings
    airline_codes = {
        '@united': 'UA', '@americanair': 'AA', '@delta': 'DL',
        '@southwestair': 'WN', '@jetblue': 'B6', '@usairways': 'US',
        'united': 'UA', 'american': 'AA', 'delta': 'DL',
        'southwest': 'WN', 'jetblue': 'B6'
    }

    # Major airport codes with city names
    airport_cities = {
        'ORD': 'Chicago', 'LAX': 'Los Angeles', 'JFK': 'New York', 'LGA': 'New York',
        'ATL': 'Atlanta', 'DFW': 'Dallas', 'DEN': 'Denver', 'PHX': 'Phoenix',
        'LAS': 'Las Vegas', 'SEA': 'Seattle', 'SFO': 'San Francisco', 'MIA': 'Miami',
        'BOS': 'Boston', 'MSP': 'Minneapolis', 'DTW': 'Detroit', 'PHL': 'Philadelphia',
        'CLT': 'Charlotte', 'IAH': 'Houston', 'EWR': 'Newark', 'MCO': 'Orlando'
    }

    results = []
    extraction_stats = {
        'total_processed': 0,
        'flight_numbers_extracted': 0,
        'dates_extracted': 0,
        'airports_extracted': 0,
        'incidents_identified': 0,
        'high_confidence': 0,
        'llm_fallback_used': 0
    }

    for idx, row in df.iterrows():
        text = str(row.get('text', ''))
        airline = row.get('airline', '') or ''  # Handle None values

        parsed = {
            'original_text': text,
            'airline': airline,
            'flight_number': None,
            'flight_date': None,
            'origin': None,
            'destination': None,
            'incident_type': None,
            'delay_hours': None,
            'confidence_score': 0.0,
            'extraction_method': 'regex'
        }

        # Extract flight number
        flight_matches = []
        for pattern in patterns['flight_number']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            flight_matches.extend(matches)

        if flight_matches:
            # Take the first match, prefer airline-specific codes
            for match in flight_matches:
                if isinstance(match, tuple):
                    carrier_code, flight_num = match
                else:
                    # Try to infer carrier from airline handle
                    carrier_code = airline_codes.get(airline.lower(), 'XX')
                    flight_num = match

                parsed['flight_number'] = f"{carrier_code}{flight_num}"
                extraction_stats['flight_numbers_extracted'] += 1
                parsed['confidence_score'] += 0.3
                break

        # Extract airports
        airport_matches = []
        for pattern in patterns['airports']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            airport_matches.extend([m for m in matches if isinstance(m, str) and m.upper() in airport_cities])

        if airport_matches:
            unique_airports = list(set([a.upper() for a in airport_matches]))
            if len(unique_airports) >= 2:
                parsed['origin'] = unique_airports[0]
                parsed['destination'] = unique_airports[1]
                extraction_stats['airports_extracted'] += 1
                parsed['confidence_score'] += 0.2
            elif len(unique_airports) == 1:
                parsed['origin'] = unique_airports[0]
                extraction_stats['airports_extracted'] += 1
                parsed['confidence_score'] += 0.1

        # Extract date information
        date_matches = []
        for pattern in patterns['dates']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            date_matches.extend(matches)

        if date_matches:
            # Try to parse the first reasonable date match
            for match in date_matches:
                try:
                    if isinstance(match, tuple) and len(match) >= 2:
                        if len(match) == 3:  # MM/DD/YYYY
                            month, day, year = match
                            if len(year) == 2:
                                year = f"20{year}"
                            parsed['flight_date'] = f"{year}-{month:0>2}-{day:0>2}"
                        else:  # MM/DD (assume current year)
                            month, day = match
                            current_year = datetime.now().year
                            parsed['flight_date'] = f"{current_year}-{month:0>2}-{day:0>2}"
                    elif isinstance(match, str):
                        # Handle relative dates
                        if str(match).lower() in ['yesterday', 'today']:
                            base_date = datetime.now()
                            if str(match).lower() == 'yesterday':
                                base_date -= timedelta(days=1)
                            parsed['flight_date'] = base_date.strftime('%Y-%m-%d')

                    if parsed['flight_date']:
                        extraction_stats['dates_extracted'] += 1
                        parsed['confidence_score'] += 0.2
                        break
                except:
                    continue

        # Extract incident type and delay information
        incident_types = []
        delay_hours = None

        for pattern in patterns['incidents']:
            if re.search(pattern, text, re.IGNORECASE):
                incident_types.append(str(re.search(pattern, text, re.IGNORECASE).group(0)).lower())

        for pattern in patterns['delays']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    delay_hours = int(match.group(1))
                    incident_types.append('delay')
                    break
                except:
                    pass

        if incident_types:
            parsed['incident_type'] = ', '.join(set(incident_types))
            parsed['delay_hours'] = delay_hours
            extraction_stats['incidents_identified'] += 1
            parsed['confidence_score'] += 0.2

        # Normalize confidence score
        parsed['confidence_score'] = min(1.0, parsed['confidence_score'])

        # LLM fallback for low-confidence extractions
        if (parsed['confidence_score'] < confidence_threshold and
            use_llm_fallback and
            context and hasattr(context, 'call_llm')):

            try:
                llm_prompt = f"""
                Extract flight details from this airline complaint tweet:
                Tweet: "{text}"
                Airline: {airline}

                Extract if available:
                - Flight number (format: CARRIER123)
                - Flight date (YYYY-MM-DD format)
                - Origin airport (3-letter IATA code)
                - Destination airport (3-letter IATA code)
                - Incident type (delay, cancellation, baggage, etc.)
                - Delay duration in hours (if mentioned)

                Respond with JSON only:
                {{"flight_number": "...", "flight_date": "...", "origin": "...", "destination": "...", "incident_type": "...", "delay_hours": null}}
                """

                llm_result = context.call_llm(llm_prompt, max_tokens=200, temperature=0.1)

                # Parse LLM response
                if llm_result and '{' in llm_result:
                    llm_data = json.loads(llm_result[llm_result.find('{'):llm_result.rfind('}')+1])

                    # Update parsed data with LLM results
                    for key, value in llm_data.items():
                        if value and value.strip() and value.strip() not in ['null', 'None', '...']:
                            parsed[key] = value.strip()

                    parsed['confidence_score'] = min(1.0, parsed['confidence_score'] + 0.3)
                    parsed['extraction_method'] = 'regex+llm'
                    extraction_stats['llm_fallback_used'] += 1

            except Exception as e:
                print(f"[parse_entities] LLM fallback failed: {e}")

        # Update stats
        extraction_stats['total_processed'] += 1
        if parsed['confidence_score'] >= confidence_threshold:
            extraction_stats['high_confidence'] += 1

        # Add all original row data plus parsed entities
        result_row = dict(row)
        result_row.update(parsed)
        results.append(result_row)

    # Convert results to table format
    if results:
        result_df = pd.DataFrame(results)
        parsed_table = {
            "header": list(result_df.columns),
            "rows": result_df.values.tolist(),
            "metadata": {
                "extraction_config": {
                    "confidence_threshold": confidence_threshold,
                    "use_llm_fallback": use_llm_fallback
                },
                "processed_at": datetime.now().isoformat()
            }
        }
    else:
        parsed_table = {"header": [], "rows": []}

    return {
        "parsed_tweets": parsed_table,
        "extraction_stats": extraction_stats
    }
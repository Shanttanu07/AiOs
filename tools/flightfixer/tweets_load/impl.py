# tools/flightfixer/tweets_load/impl.py - Load and filter Twitter airline sentiment data

def execute(inputs, context):
    """Load Twitter airline sentiment data with filtering and analysis"""

    try:
        import pandas as pd
        import json
        from datetime import datetime
        import re
    except ImportError as e:
        return {"error": f"Required library not available: {e}. Install with: pip install pandas"}

    dataset_path = inputs["dataset_path"]
    target_airlines = inputs.get("target_airlines", ["@united", "@AmericanAir", "@Delta", "@SouthwestAir", "@JetBlue", "@USAirways"])
    date_range = inputs.get("date_range")
    sentiment_filter = inputs.get("sentiment_filter", ["negative"])

    try:
        # Load dataset (support CSV and JSON)
        if dataset_path.endswith('.csv'):
            df = pd.read_csv(dataset_path)
        elif dataset_path.endswith('.json'):
            df = pd.read_json(dataset_path)
        else:
            # Try to auto-detect format
            try:
                df = pd.read_csv(dataset_path)
            except:
                df = pd.read_json(dataset_path)

        print(f"[tweets_load] Loaded {len(df)} raw tweets")

        # Standardize column names (handle different dataset formats)
        column_mapping = {
            'text': ['text', 'tweet', 'message', 'content'],
            'airline': ['airline', 'airline_sentiment_target', 'target'],
            'sentiment': ['airline_sentiment', 'sentiment', 'label'],
            'created_at': ['tweet_created', 'created_at', 'date', 'timestamp'],
            'user': ['name', 'user', 'username', 'screen_name']
        }

        # Map columns to standard names
        for standard_name, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in df.columns:
                    if standard_name not in df.columns:
                        df[standard_name] = df[possible_name]
                    break

        # Filter by sentiment if specified
        if sentiment_filter and 'sentiment' in df.columns:
            df = df[df['sentiment'].isin(sentiment_filter)]
            print(f"[tweets_load] After sentiment filter: {len(df)} tweets")

        # Filter by target airlines
        if target_airlines and 'airline' in df.columns:
            # Handle both @airline and airline formats
            airline_patterns = []
            for airline in target_airlines:
                if airline.startswith('@'):
                    airline_patterns.extend([airline, airline[1:]])
                else:
                    airline_patterns.extend([airline, f"@{airline}"])

            df = df[df['airline'].isin(airline_patterns)]
            print(f"[tweets_load] After airline filter: {len(df)} tweets")

        # Parse and filter by date range if specified
        if date_range and 'created_at' in df.columns:
            try:
                df['parsed_date'] = pd.to_datetime(df['created_at'])
                start_date = pd.to_datetime(date_range['start']) if 'start' in date_range else df['parsed_date'].min()
                end_date = pd.to_datetime(date_range['end']) if 'end' in date_range else df['parsed_date'].max()

                df = df[(df['parsed_date'] >= start_date) & (df['parsed_date'] <= end_date)]
                print(f"[tweets_load] After date filter: {len(df)} tweets")
            except Exception as e:
                print(f"[tweets_load] Warning: Date filtering failed: {e}")

        # Generate statistics
        stats = {
            "total_tweets": len(df),
            "date_range": {
                "start": df['created_at'].min() if 'created_at' in df.columns else None,
                "end": df['created_at'].max() if 'created_at' in df.columns else None
            },
            "airlines": df['airline'].value_counts().to_dict() if 'airline' in df.columns else {},
            "sentiment_distribution": df['sentiment'].value_counts().to_dict() if 'sentiment' in df.columns else {},
            "avg_text_length": df['text'].str.len().mean() if 'text' in df.columns else 0
        }

        # Prepare complaint-focused data
        complaint_df = df.copy()

        # Add complaint indicators
        if 'text' in complaint_df.columns:
            complaint_keywords = [
                'delay', 'cancel', 'stuck', 'late', 'missed', 'refund', 'compensation',
                'terrible', 'worst', 'never', 'awful', 'horrible', 'ruined',
                'hours', 'wait', 'gate', 'flight', 'baggage', 'lost'
            ]

            complaint_pattern = '|'.join(complaint_keywords)
            complaint_df['has_complaint_keywords'] = complaint_df['text'].str.contains(
                complaint_pattern, case=False, na=False
            )
            complaint_df['complaint_score'] = complaint_df['text'].str.count(
                complaint_pattern, flags=re.IGNORECASE
            )

        # Convert to table format for tool output
        tweets_table = {
            "header": list(complaint_df.columns),
            "rows": complaint_df.values.tolist(),
            "metadata": {
                "source": dataset_path,
                "processed_at": datetime.now().isoformat(),
                "filters_applied": {
                    "airlines": target_airlines,
                    "sentiment": sentiment_filter,
                    "date_range": date_range
                }
            }
        }

        return {
            "tweets": tweets_table,
            "stats": stats
        }

    except Exception as e:
        return {
            "error": f"Failed to load tweets: {str(e)}",
            "tweets": {"header": [], "rows": []},
            "stats": {"total_tweets": 0, "error": str(e)}
        }
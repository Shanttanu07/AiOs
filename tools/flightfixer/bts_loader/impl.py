# tools/flightfixer/bts_loader/impl.py - Load BTS on-time performance data

def execute(inputs, context):
    """Load and process BTS on-time performance data for flight matching"""

    try:
        import pandas as pd
        from datetime import datetime
        import numpy as np
    except ImportError as e:
        return {"error": f"Required library not available: {e}"}

    bts_data_path = inputs["bts_data_path"]
    month_filter = inputs.get("month_filter")
    carriers = inputs.get("carriers")

    try:
        # Load BTS data
        df = pd.read_csv(bts_data_path, low_memory=False)
        print(f"[bts_loader] Loaded {len(df)} flight records")

        # Standardize column names (BTS uses specific column names)
        # Common BTS columns: CARRIER, FL_DATE, FL_NUM, ORIGIN, DEST, ARR_DELAY, DEP_DELAY, CANCELLED
        required_columns = ['CARRIER', 'FL_DATE', 'FL_NUM', 'ORIGIN', 'DEST']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return {
                "error": f"Missing required BTS columns: {missing_columns}. Available columns: {list(df.columns)}",
                "flight_performance": {"header": [], "rows": []},
                "performance_stats": {}
            }

        # Parse flight date
        df['FL_DATE'] = pd.to_datetime(df['FL_DATE'])

        # Filter by month if specified
        if month_filter:
            try:
                year, month = map(int, month_filter.split('-'))
                df = df[(df['FL_DATE'].dt.year == year) & (df['FL_DATE'].dt.month == month)]
                print(f"[bts_loader] After month filter ({month_filter}): {len(df)} flights")
            except Exception as e:
                print(f"[bts_loader] Warning: Month filter failed: {e}")

        # Filter by carriers if specified
        if carriers:
            df = df[df['CARRIER'].isin(carriers)]
            print(f"[bts_loader] After carrier filter: {len(df)} flights")

        # Process delay and cancellation information
        delay_columns = ['ARR_DELAY', 'DEP_DELAY', 'ARR_DELAY_NEW', 'DEP_DELAY_NEW']
        for col in delay_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        cancellation_columns = ['CANCELLED', 'CANCELLATION_CODE']
        for col in cancellation_columns:
            if col in df.columns and df[col].dtype == object:
                # Convert boolean-like strings to numeric
                df[col] = df[col].replace({'1.00': 1, '0.00': 0, 'Y': 1, 'N': 0})
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Add derived fields for easier matching and analysis
        df['FLIGHT_KEY'] = df['CARRIER'] + df['FL_NUM'].astype(str)
        df['DATE_STR'] = df['FL_DATE'].dt.strftime('%Y-%m-%d')

        # Determine significant delays (3+ hours for domestic, per DOT 2024 rule)
        arrival_delay_col = 'ARR_DELAY' if 'ARR_DELAY' in df.columns else 'ARR_DELAY_NEW'
        if arrival_delay_col in df.columns:
            df['SIGNIFICANT_DELAY'] = df[arrival_delay_col] >= 180  # 3 hours = 180 minutes

        # Determine cancellation status
        cancelled_col = 'CANCELLED' if 'CANCELLED' in df.columns else None
        if cancelled_col:
            df['IS_CANCELLED'] = df[cancelled_col] == 1
        else:
            df['IS_CANCELLED'] = False

        # Calculate refund eligibility based on DOT 2024 rules
        df['REFUND_ELIGIBLE'] = (
            df.get('IS_CANCELLED', False) |
            df.get('SIGNIFICANT_DELAY', False)
        )

        # Generate performance statistics
        total_flights = len(df)
        cancelled_flights = df['IS_CANCELLED'].sum() if 'IS_CANCELLED' in df.columns else 0
        significantly_delayed = df['SIGNIFICANT_DELAY'].sum() if 'SIGNIFICANT_DELAY' in df.columns else 0
        refund_eligible = df['REFUND_ELIGIBLE'].sum() if 'REFUND_ELIGIBLE' in df.columns else 0

        performance_stats = {
            "total_flights": int(total_flights),
            "date_range": {
                "start": df['FL_DATE'].min().isoformat() if len(df) > 0 else None,
                "end": df['FL_DATE'].max().isoformat() if len(df) > 0 else None
            },
            "cancellation_rate": float(cancelled_flights / total_flights) if total_flights > 0 else 0,
            "significant_delay_rate": float(significantly_delayed / total_flights) if total_flights > 0 else 0,
            "refund_eligible_rate": float(refund_eligible / total_flights) if total_flights > 0 else 0,
            "carriers": {}
        }

        # Carrier-specific statistics
        if total_flights > 0:
            carrier_stats = df.groupby('CARRIER').agg({
                'FL_NUM': 'count',
                'IS_CANCELLED': 'sum',
                'SIGNIFICANT_DELAY': 'sum',
                'REFUND_ELIGIBLE': 'sum'
            }).rename(columns={'FL_NUM': 'total_flights'})

            for carrier in carrier_stats.index:
                stats = carrier_stats.loc[carrier]
                performance_stats["carriers"][carrier] = {
                    "total_flights": int(stats['total_flights']),
                    "cancellation_rate": float(stats['IS_CANCELLED'] / stats['total_flights']) if stats['total_flights'] > 0 else 0,
                    "significant_delay_rate": float(stats['SIGNIFICANT_DELAY'] / stats['total_flights']) if stats['total_flights'] > 0 else 0,
                    "refund_eligible_rate": float(stats['REFUND_ELIGIBLE'] / stats['total_flights']) if stats['total_flights'] > 0 else 0
                }

        # Prepare output table
        # Select key columns for matching
        output_columns = [
            'CARRIER', 'FL_NUM', 'FLIGHT_KEY', 'FL_DATE', 'DATE_STR',
            'ORIGIN', 'DEST', 'IS_CANCELLED', 'SIGNIFICANT_DELAY', 'REFUND_ELIGIBLE'
        ]

        # Add delay columns if available
        if arrival_delay_col in df.columns:
            output_columns.append(arrival_delay_col)
            df['ARR_DELAY_MINUTES'] = df[arrival_delay_col]

        dep_delay_col = 'DEP_DELAY' if 'DEP_DELAY' in df.columns else 'DEP_DELAY_NEW'
        if dep_delay_col in df.columns:
            df['DEP_DELAY_MINUTES'] = df[dep_delay_col]
            output_columns.append('DEP_DELAY_MINUTES')

        # Add cancellation code if available
        if 'CANCELLATION_CODE' in df.columns:
            output_columns.append('CANCELLATION_CODE')

        # Filter to existing columns
        existing_columns = [col for col in output_columns if col in df.columns]
        output_df = df[existing_columns].copy()

        flight_performance_table = {
            "header": list(output_df.columns),
            "rows": output_df.values.tolist(),
            "metadata": {
                "source": bts_data_path,
                "filters_applied": {
                    "month": month_filter,
                    "carriers": carriers
                },
                "dot_rules": {
                    "significant_delay_threshold_minutes": 180,
                    "refund_eligible_criteria": "cancelled OR domestic_delay >= 3 hours"
                },
                "processed_at": datetime.now().isoformat()
            }
        }

        return {
            "flight_performance": flight_performance_table,
            "performance_stats": performance_stats
        }

    except Exception as e:
        return {
            "error": f"Failed to load BTS data: {str(e)}",
            "flight_performance": {"header": [], "rows": []},
            "performance_stats": {"error": str(e)}
        }
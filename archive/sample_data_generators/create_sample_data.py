# create_sample_data.py - Generate sample datasets for FlightFixer demo
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def create_sample_twitter_data():
    """Create sample Twitter airline sentiment data for demo"""

    airlines = ["@united", "@AmericanAir", "@Delta", "@SouthwestAir", "@JetBlue"]

    # Sample complaint tweets with various levels of detail
    sample_tweets = [
        # Complete information
        {"text": "@united flight UA123 on 2/14 cancelled at ORD. Need refund!", "airline": "@united", "sentiment": "negative"},
        {"text": "@AmericanAir AA456 delayed 4 hours at LAX on Feb 15th. Missed connection!", "airline": "@AmericanAir", "sentiment": "negative"},
        {"text": "@Delta flight DL789 from ATL to JFK cancelled yesterday. Where's my refund?", "airline": "@Delta", "sentiment": "negative"},

        # Partial information
        {"text": "@SouthwestAir flight cancelled AGAIN! This is ridiculous!", "airline": "@SouthwestAir", "sentiment": "negative"},
        {"text": "@united stuck at gate for 3 hours. Departure delayed indefinitely.", "airline": "@united", "sentiment": "negative"},
        {"text": "@JetBlue worst airline ever. Flight delayed and no compensation!", "airline": "@JetBlue", "sentiment": "negative"},

        # Vague complaints
        {"text": "@AmericanAir ruined my vacation plans. Terrible service!", "airline": "@AmericanAir", "sentiment": "negative"},
        {"text": "@Delta why is your airline so unreliable? Always problems!", "airline": "@Delta", "sentiment": "negative"},
        {"text": "@united customer service is a joke. Never flying with you again.", "airline": "@united", "sentiment": "negative"},

        # More detailed complaints
        {"text": "@AmericanAir AA1234 on 2/16 from DFW to LAX delayed 5 hours. Missed meeting!", "airline": "@AmericanAir", "sentiment": "negative"},
        {"text": "@Delta DL567 cancelled at ATL this morning. Connecting flight to Europe missed!", "airline": "@Delta", "sentiment": "negative"},
        {"text": "@SouthwestAir WN890 delayed 2 hours at MDW. No food vouchers provided!", "airline": "@SouthwestAir", "sentiment": "negative"},

        # Baggage complaints
        {"text": "@united lost my bag on UA345 from ORD to SFO on 2/20. Need compensation!", "airline": "@united", "sentiment": "negative"},
        {"text": "@AmericanAir baggage delayed 12 hours on AA678. Where are my clothes?", "airline": "@AmericanAir", "sentiment": "negative"},

        # WiFi/service complaints
        {"text": "@Delta paid $25 for WiFi on DL901 and it didn't work. Refund please!", "airline": "@Delta", "sentiment": "negative"},
        {"text": "@JetBlue no food service on 6-hour flight B6234. Very disappointed.", "airline": "@JetBlue", "sentiment": "negative"},
    ]

    # Create DataFrame
    df = pd.DataFrame(sample_tweets)

    # Add additional columns to match Twitter airline sentiment dataset format
    df['tweet_id'] = range(1000000, 1000000 + len(df))
    df['airline_sentiment'] = df['sentiment']
    df['airline_sentiment_confidence'] = np.random.uniform(0.6, 0.95, len(df))
    df['negativereason'] = 'Flight Problems'
    df['name'] = [f"user_{i}" for i in range(len(df))]
    df['tweet_created'] = pd.date_range(start='2015-02-14', end='2015-02-20', periods=len(df))
    df['tweet_location'] = 'USA'
    df['user_timezone'] = 'Eastern Time (US & Canada)'

    return df

def create_sample_bts_data():
    """Create sample BTS on-time performance data for demo"""

    # Carrier codes
    carriers = [
        ('UA', 'United Airlines'),
        ('AA', 'American Airlines'),
        ('DL', 'Delta Airlines'),
        ('WN', 'Southwest Airlines'),
        ('B6', 'JetBlue Airways')
    ]

    # Major airports
    airports = ['ORD', 'ATL', 'LAX', 'DFW', 'DEN', 'JFK', 'SFO', 'LAS', 'SEA', 'MIA', 'PHX', 'IAH', 'MDW']

    flights_data = []

    # Generate sample flights for February 2015
    for day in range(14, 21):  # Feb 14-20, 2015
        flight_date = f"2015-02-{day:02d}"

        for carrier_code, carrier_name in carriers:
            # Generate multiple flights per day per carrier
            for flight_num in [123, 234, 345, 456, 567, 678, 789, 890, 901, 1234]:
                origin = random.choice(airports)
                dest = random.choice([a for a in airports if a != origin])

                # Simulate flight performance
                cancelled = random.random() < 0.05  # 5% cancellation rate

                if cancelled:
                    arr_delay = None
                    dep_delay = None
                    cancellation_code = random.choice(['A', 'B', 'C'])  # Weather, Airline, NAS
                else:
                    # Normal distribution of delays
                    arr_delay = max(0, np.random.normal(15, 45))  # Average 15min delay, std 45min
                    dep_delay = max(0, np.random.normal(12, 35))
                    cancellation_code = None

                # Some flights have significant delays (3+ hours for domestic)
                if random.random() < 0.03 and not cancelled:  # 3% significant delay rate
                    arr_delay = random.uniform(180, 480)  # 3-8 hours
                    dep_delay = random.uniform(120, 360)  # 2-6 hours

                flight_record = {
                    'FL_DATE': flight_date,
                    'CARRIER': carrier_code,
                    'FL_NUM': flight_num,
                    'ORIGIN': origin,
                    'DEST': dest,
                    'DEP_DELAY': dep_delay,
                    'ARR_DELAY': arr_delay,
                    'CANCELLED': 1 if cancelled else 0,
                    'CANCELLATION_CODE': cancellation_code,
                    'DIVERTED': 0,
                    'DISTANCE': random.randint(200, 2500)
                }

                flights_data.append(flight_record)

    df = pd.DataFrame(flights_data)

    # Add calculated fields that match real BTS data
    df['CARRIER_NAME'] = df['CARRIER'].map(dict(carriers))
    df['FL_DATE'] = pd.to_datetime(df['FL_DATE'])

    return df

def main():
    """Generate sample datasets for FlightFixer demo"""

    print("Creating sample Twitter airline sentiment data...")
    twitter_df = create_sample_twitter_data()
    twitter_df.to_csv('sandbox/in/twitter_airline_sentiment.csv', index=False)
    print(f"Created {len(twitter_df)} sample tweets")

    print("Creating sample BTS on-time performance data...")
    bts_df = create_sample_bts_data()
    bts_df.to_csv('sandbox/in/bts_ontime_feb2015.csv', index=False)
    print(f"Created {len(bts_df)} sample flight records")

    # Create output directories
    import os
    os.makedirs('sandbox/out/customer_replies', exist_ok=True)
    os.makedirs('sandbox/out/actions', exist_ok=True)

    print("Sample data created successfully!")
    print("\nDataset Summary:")
    print(f"Twitter Dataset: {len(twitter_df)} tweets with various complaint types")
    print(f"BTS Dataset: {len(bts_df)} flight records with realistic delay/cancellation patterns")
    print("\nReady for FlightFixer demo!")

if __name__ == "__main__":
    main()
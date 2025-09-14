# create_simple_sample_data.py - Generate sample datasets without pandas
import csv
import os
import random
from datetime import datetime, timedelta

def create_sample_twitter_data():
    """Create sample Twitter airline sentiment CSV data"""

    sample_tweets = [
        # Complete information
        ["@united flight UA123 on 2/14 cancelled at ORD. Need refund!", "@united", "negative", "user_001", "2015-02-14"],
        ["@AmericanAir AA456 delayed 4 hours at LAX on Feb 15th. Missed connection!", "@AmericanAir", "negative", "user_002", "2015-02-15"],
        ["@Delta flight DL789 from ATL to JFK cancelled yesterday. Where's my refund?", "@Delta", "negative", "user_003", "2015-02-16"],

        # Partial information
        ["@SouthwestAir flight cancelled AGAIN! This is ridiculous!", "@SouthwestAir", "negative", "user_004", "2015-02-17"],
        ["@united stuck at gate for 3 hours. Departure delayed indefinitely.", "@united", "negative", "user_005", "2015-02-18"],
        ["@JetBlue worst airline ever. Flight delayed and no compensation!", "@JetBlue", "negative", "user_006", "2015-02-19"],

        # Vague complaints
        ["@AmericanAir ruined my vacation plans. Terrible service!", "@AmericanAir", "negative", "user_007", "2015-02-14"],
        ["@Delta why is your airline so unreliable? Always problems!", "@Delta", "negative", "user_008", "2015-02-15"],
        ["@united customer service is a joke. Never flying with you again.", "@united", "negative", "user_009", "2015-02-16"],

        # More detailed complaints
        ["@AmericanAir AA1234 on 2/16 from DFW to LAX delayed 5 hours. Missed meeting!", "@AmericanAir", "negative", "user_010", "2015-02-16"],
        ["@Delta DL567 cancelled at ATL this morning. Connecting flight to Europe missed!", "@Delta", "negative", "user_011", "2015-02-17"],
        ["@SouthwestAir WN890 delayed 2 hours at MDW. No food vouchers provided!", "@SouthwestAir", "negative", "user_012", "2015-02-18"],

        # Baggage complaints
        ["@united lost my bag on UA345 from ORD to SFO on 2/20. Need compensation!", "@united", "negative", "user_013", "2015-02-20"],
        ["@AmericanAir baggage delayed 12 hours on AA678. Where are my clothes?", "@AmericanAir", "negative", "user_014", "2015-02-19"],

        # WiFi/service complaints
        ["@Delta paid $25 for WiFi on DL901 and it didn't work. Refund please!", "@Delta", "negative", "user_015", "2015-02-18"],
        ["@JetBlue no food service on 6-hour flight B6234. Very disappointed.", "@JetBlue", "negative", "user_016", "2015-02-17"],
    ]

    return sample_tweets

def create_sample_bts_data():
    """Create sample BTS on-time performance data"""

    carriers = ['UA', 'AA', 'DL', 'WN', 'B6']
    airports = ['ORD', 'ATL', 'LAX', 'DFW', 'DEN', 'JFK', 'SFO', 'MDW']

    flights_data = []

    # Generate sample flights
    flights_info = [
        # Matches for tweets
        ['2015-02-14', 'UA', '123', 'ORD', 'DEN', 0, 0, 1, 'A'],  # UA123 cancelled
        ['2015-02-15', 'AA', '456', 'LAX', 'JFK', 120, 240, 0, ''],  # AA456 delayed 4 hours (240 min)
        ['2015-02-16', 'DL', '789', 'ATL', 'JFK', 30, 0, 1, 'B'],  # DL789 cancelled
        ['2015-02-16', 'AA', '1234', 'DFW', 'LAX', 180, 300, 0, ''],  # AA1234 delayed 5 hours (300 min)
        ['2015-02-17', 'DL', '567', 'ATL', 'LHR', 60, 0, 1, 'A'],  # DL567 cancelled
        ['2015-02-18', 'WN', '890', 'MDW', 'LAX', 45, 120, 0, ''],  # WN890 delayed 2 hours
        ['2015-02-20', 'UA', '345', 'ORD', 'SFO', 15, 30, 0, ''],  # UA345 normal flight (baggage issue)
        ['2015-02-19', 'AA', '678', 'DFW', 'ORD', 20, 25, 0, ''],  # AA678 normal flight (baggage issue)
        ['2015-02-18', 'DL', '901', 'ATL', 'LAX', 10, 15, 0, ''],  # DL901 normal flight (wifi issue)
        ['2015-02-17', 'B6', '234', 'JFK', 'LAX', 25, 45, 0, ''],  # B6234 normal flight (service issue)

        # Additional flights for context
        ['2015-02-14', 'UA', '100', 'ORD', 'LAX', 15, 20, 0, ''],
        ['2015-02-15', 'AA', '200', 'DFW', 'JFK', 30, 45, 0, ''],
        ['2015-02-16', 'DL', '300', 'ATL', 'SFO', 0, 5, 0, ''],
        ['2015-02-17', 'WN', '400', 'MDW', 'DEN', 60, 90, 0, ''],
        ['2015-02-18', 'B6', '500', 'JFK', 'SFO', 120, 180, 0, ''],  # 3 hour delay
        ['2015-02-19', 'UA', '600', 'SFO', 'ORD', 200, 240, 0, ''],  # 4 hour delay
        ['2015-02-20', 'AA', '700', 'LAX', 'ATL', 0, 0, 1, 'B'],  # Cancelled
    ]

    for flight_info in flights_info:
        flights_data.append(flight_info)

    return flights_data

def main():
    """Generate sample datasets"""

    # Create directories
    os.makedirs('sandbox/in', exist_ok=True)
    os.makedirs('sandbox/out/customer_replies', exist_ok=True)
    os.makedirs('sandbox/out/actions', exist_ok=True)

    print("Creating sample Twitter airline sentiment data...")

    # Write Twitter data
    with open('sandbox/in/twitter_airline_sentiment.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['text', 'airline', 'airline_sentiment', 'name', 'tweet_created'])

        tweets = create_sample_twitter_data()
        for tweet in tweets:
            writer.writerow(tweet)

    print(f"Created {len(create_sample_twitter_data())} sample tweets")

    print("Creating sample BTS on-time performance data...")

    # Write BTS data
    with open('sandbox/in/bts_ontime_feb2015.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['FL_DATE', 'CARRIER', 'FL_NUM', 'ORIGIN', 'DEST', 'DEP_DELAY', 'ARR_DELAY', 'CANCELLED', 'CANCELLATION_CODE'])

        flights = create_sample_bts_data()
        for flight in flights:
            writer.writerow(flight)

    print(f"Created {len(create_sample_bts_data())} sample flight records")

    print("\nSample data created successfully!")
    print("\nDataset Summary:")
    print(f"Twitter Dataset: 16 tweets with various complaint types and detail levels")
    print(f"BTS Dataset: 17 flight records with realistic delay/cancellation patterns")
    print("\nKey test cases:")
    print("- UA123: Tweet mentions cancellation, BTS confirms cancelled")
    print("- AA456: Tweet mentions 4hr delay, BTS shows 240min arrival delay")
    print("- Baggage issues: Normal flights with baggage complaints")
    print("- Vague complaints: Missing flight details for 'need more info' responses")
    print("\nReady for FlightFixer demo!")

if __name__ == "__main__":
    main()
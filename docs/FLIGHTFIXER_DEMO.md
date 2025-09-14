# FlightFixer: Judge-Ready Demo

**Transform messy airline complaints into actionable refund claims using real data sources**

## 🎯 **Demo Overview**

FlightFixer takes **unstructured passenger complaints** from Twitter, cross-references them with **official flight performance data** from the Bureau of Transportation Statistics, applies **DOT 2024 refund rules**, and generates **real actionable outputs**: refund claim JSON, customer reply drafts, and Slack notifications for operations teams.

## 📊 **Real Data Sources**

### Twitter Airline Sentiment Dataset
- **Source**: [Hugging Face - Twitter US Airline Sentiment](https://huggingface.co/datasets/osanseviero/twitter-airline-sentiment)
- **Content**: 14,640 tweets about US airlines (Feb 2015)
- **Challenge**: Unstructured text, missing flight details, contradictory information
- **Example**: "@united flight UA101 2/14 stuck 4 hrs at ORD!!!"

### BTS On-Time Performance Data
- **Source**: [Bureau of Transportation Statistics](https://www.transtats.bts.gov/ontime/)
- **Content**: Official flight delays, cancellations, performance metrics
- **Challenge**: Complex carrier codes, timezone handling, data quality issues
- **Coverage**: 1987-present, downloadable by month

### DOT 2024 Refund Rules
- **Source**: [Federal Register - April 26, 2024](https://www.federalregister.gov/documents/2024/04/26/2024-07177/refunds-and-other-consumer-protections)
- **Rules**: Automatic cash refunds for cancellations, 3+ hour domestic delays, 6+ hour international delays
- **Implementation**: 14 CFR 259.5 compliance with legal citations

## 🔧 **FlightFixer Tool Chain**

### 1. **tweets_load** - Messy Data Ingestion
```json
{
  "op": "tweets_load",
  "in": {
    "dataset_path": "sandbox/in/twitter_airline_sentiment.csv",
    "sentiment_filter": ["negative"],
    "target_airlines": ["@united", "@AmericanAir", "@Delta"]
  }
}
```
**Handles**: Different CSV formats, airline handle variations, date parsing

### 2. **parse_entities** - Extract Flight Details
```json
{
  "op": "parse_entities",
  "in": {
    "tweets": "$complaint_tweets",
    "use_llm_fallback": true,
    "confidence_threshold": 0.6
  }
}
```
**Extracts**: Flight numbers (UA123), dates (2/14, yesterday), airports (ORD→LAX), incident types

### 3. **bts_loader** - Official Flight Data
```json
{
  "op": "bts_loader",
  "in": {
    "bts_data_path": "sandbox/in/bts_ontime_feb2015.csv",
    "month_filter": "2015-02"
  }
}
```
**Processes**: Carrier codes, delay minutes, cancellation flags, DOT compliance markers

### 4. **flight_matcher** - Fuzzy Data Resolution
```json
{
  "op": "flight_matcher",
  "in": {
    "parsed_tweets": "$parsed_complaints",
    "flight_performance": "$flight_performance",
    "date_tolerance_days": 1
  }
}
```
**Matches**: Tweets ↔ BTS records with confidence scoring, handles missing data

### 5. **refund_analyzer** - DOT Rules Engine
```json
{
  "op": "refund_analyzer",
  "in": {
    "matched_flights": "$matched_flights",
    "dot_rules_config": {
      "domestic_significant_delay_minutes": 180
    }
  }
}
```
**Applies**: 14 CFR 259.5 rules, calculates refund amounts, provides legal citations

### 6. **action_generator** - Actionable Outputs
```json
{
  "op": "action_generator",
  "in": {
    "refund_decisions": "$refund_decisions",
    "output_config": {"include_legal_disclaimer": true}
  }
}
```

## 🎬 **Judge Demo Script (3-4 minutes)**

### **Step 1: Show the Problem** (30 seconds)
- Display messy tweet: "@AmericanAir flight cancelled AGAIN!!! Need refund #worst"
- Show BTS data complexity: Carrier codes, UTC timestamps, missing entries
- **Challenge**: How do you connect unstructured complaints to official data?

### **Step 2: Run FlightFixer** (60 seconds)
```bash
python -m aiox run --bytecode apps/forge/flightfixer_demo.apl.bytecode.json --yes
```
- Watch tool chain execute: tweets → parsing → BTS loading → matching → DOT analysis → actions
- **Show**: Real-time processing of messy data through structured pipeline

### **Step 3: Show Actionable Outputs** (90 seconds)

#### A) **Refund Claims JSON** (`sandbox/out/refund_claims.jsonl`)
```json
{
  "claim_id": "RFC-20250114-0001",
  "passenger": {"twitter_handle": "@john_traveler"},
  "flight": {"carrier": "AA", "flight_number": "1234", "date": "2015-02-14"},
  "refund": {
    "eligible": true,
    "reason": "Flight cancellation",
    "dot_citation": "14 CFR 259.5(b)(1)",
    "estimated_amount": 450.0,
    "deadline_days": 7
  }
}
```

#### B) **Customer Reply Draft** (`sandbox/out/customer_replies/john_traveler.md`)
```markdown
Hello @john_traveler,

You are eligible for a $450.00 refund under DOT 2024 rules.

**Legal Basis:** 14 CFR 259.5(b)(1) - Automatic refund required for cancelled flights

**Evidence:** BTS data confirms flight AA1234 on 2015-02-14 was cancelled

The airline must process your refund within 7 days...
```

#### C) **Slack Operations Notification** (`sandbox/out/slack_notification.json`)
```json
{
  "blocks": [
    {"type": "header", "text": {"text": "🛫 FlightFixer Daily Report"}},
    {"type": "section", "fields": [
      {"text": "*Total Cases:* 45"},
      {"text": "*Refund Eligible:* 23"},
      {"text": "*Estimated Refunds:* $12,350.00"}
    ]}
  ]
}
```

### **Step 4: Robustness Demo** (30 seconds)
- Show **"need more info"** reply for vague tweet: "flight was terrible"
- Show **low confidence** quarantine: Unclear flight numbers get human review
- **Highlight**: No destructive actions on uncertain data

### **Step 5: Deterministic Replay** (30 seconds)
```bash
python -m aiox pack flightfixer_demo --output flightfixer.aiox
python -m aiox replay flightfixer.aiox  # Same results, no new LLM calls
```

## ✅ **Why This Nails the Sponsor Brief**

### **Messy Data Mastery**
- **Unstructured**: Tweets with missing flight info, typos, abbreviations
- **Incomplete**: "@airline ruined my trip" → Extract what's possible, ask for rest
- **Conflicting**: Tweet says delay, BTS shows cancellation → Use official data, note discrepancy

### **Multi-Source Resolution**
- **Join**: Twitter handles ↔ Carrier codes ↔ Flight numbers ↔ Performance data
- **Handle**: Timezone differences, date formats, airline code variations
- **Validate**: Cross-reference social complaints with official government records

### **Robust Decision Making**
- **Uncertainty Handling**: Low confidence matches → Manual review queue
- **Rule-Based**: DOT 2024 thresholds drive refund eligibility decisions
- **Evidence-Based**: Every decision includes BTS data citation and confidence score

### **Practical Utility**
- **Claims JSON**: Ready for automated processing systems
- **Reply Drafts**: Customer service can copy/paste with legal backing
- **Slack Payload**: Operations team gets instant situation awareness

## 📦 **Ready-to-Run Package**

Everything needed for the demo:
```
flightfixer_demo.aiox
├── tools/flightfixer/          # 6 specialized tools
├── sandbox/in/
│   ├── twitter_airline_sentiment.csv     # Real tweet dataset
│   └── bts_ontime_feb2015.csv            # Official BTS data
├── apps/forge/flightfixer_demo.apl.json  # Complete workflow plan
└── expected_outputs/                      # Reference results
```

**Judge Experience**:
1. Run single command → See messy data become actionable outputs
2. Open generated files → Real customer replies with DOT citations
3. Replay deterministically → Same results, no network calls

The FlightFixer demo shows how our expanded APL architecture handles real-world messy data scenarios with practical business impact - turning social media complaints into compliant refund processing workflows.
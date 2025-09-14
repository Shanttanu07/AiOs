# Real-Time AI-OS Demo

## Launch Real-Time Interface

```bash
# Terminal 1: Real-time prompt interface
python realtime_terminal.py

# Terminal 2: TUI with carbon/cost tracking (optional)
python -m aiox.ui.tui
```

## Real-Time Demo Flow

1. **Launch terminal interface**
   ```bash
   python realtime_terminal.py
   ```

2. **Type natural language prompts**
   ```
   AI-OS> Process airline complaints and identify refunds
   AI-OS> Analyze flight delay patterns
   AI-OS> Generate insights from customer data
   ```

3. **Launch TUI to see metrics**
   ```
   AI-OS> tui
   ```

4. **Watch real-time execution**
   - Carbon footprint tracking
   - Cost accumulation
   - Tool execution progress
   - Generated outputs

## Sample Prompts

**FlightFixer Demo:**
```
Process airline complaint tweets and match with flight data for refund eligibility
```

**Data Analysis:**
```
Analyze customer feedback patterns and generate business insights
```

**Custom Task:**
```
Load CSV data, profile schema, and create summary report
```

## TUI Features

- **Live Carbon Tracking**: Real-time CO2 emissions
- **Cost Meters**: Visual progress bars for spending
- **Active Run Highlighting**: Reverse video for live execution
- **Tool Discovery**: Dynamic schema with 20+ tools
- **APL Generation**: LLM-based planning with fallback

## Quick Commands

- `tui` - Launch TUI interface
- `quit` - Exit terminal
- Any natural language prompt for real-time processing

Perfect for live demonstrations of task-agnostic automation!
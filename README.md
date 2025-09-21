# Wells Fargo Agent Protocol (WFAP) - Complete Implementation

A comprehensive implementation of the Wells Fargo Agent Protocol using Google's Agent Development Kit (ADK) and A2A communication protocol. This system enables AI agents to handle corporate credit requests with structured communications, ESG evaluation, and automated offer comparison.

## 🏗️ Architecture Overview

The WFAP system consists of four main components:

```
Company Agent → [Structured Intent] → Broker Agent → [Pure Routing] → Bank Agents → [Generate Offers] → Process Request
```

### Components:

1. **Company Agent** (`company_agent/`) - Creates credit intents and evaluates bank offers
2. **Broker Agent** (`broker_agent/`) - Pure message router between company and banks
3. **Wells Fargo Agent** (`wells_fargo_agent/`) - Conservative bank with ESG focus
4. **Bank of America Agent** (`boa_agent/`) - Innovation-focused bank with tech emphasis

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- `uv` package manager
- Google Gemini API key

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd wfap-solution
   ```

2. **Set up environment variables:**
   Create `.env` files in each agent directory with your Gemini API key:
   
   ```bash
   # In each agent directory (broker_agent/, company_agent/, wells_fargo_agent/, boa_agent/)
   echo "GEMINI_API_KEY=your_api_key_here" > .env
   ```

3. **Install dependencies for each agent:**
   ```bash
   # Install broker agent dependencies
   cd broker_agent && uv sync && cd ..
   
   # Install company agent dependencies  
   cd company_agent && uv sync && cd ..
   
   # Install Wells Fargo agent dependencies
   cd wells_fargo_agent && uv sync && cd ..
   
   # Install Bank of America agent dependencies
   cd boa_agent && uv sync && cd ..
   ```

## 🏃‍♂️ Running the System

### Start All Agents

Open 4 terminal windows and run each agent:

**Terminal 1 - Broker Agent:**
```bash
cd broker_agent
uv run python __main__.py --port 8000
```

**Terminal 2 - Wells Fargo Agent:**
```bash
cd wells_fargo_agent  
uv run python __main__.py --port 8001
```

**Terminal 3 - Bank of America Agent:**
```bash
cd boa_agent
uv run python __main__.py --port 8002
```

**Terminal 4 - Company Agent (Using ADK Web):**
```bash
# From the wfap-solution directory
adk web --port 8003
```

### Alternative: Start All Servers Except Company Agent

If you want to start all servers except the company agent (for testing purposes):

```bash
# Start broker agent
cd broker_agent && uv run python __main__.py --port 8000 &

# Start Wells Fargo agent  
cd wells_fargo_agent && uv run python __main__.py --port 8001 &

# Start Bank of America agent
cd boa_agent && uv run python __main__.py --port 8002 &
```

Then use ADK Web for the company agent:
```bash
# From the wfap-solution directory
adk web --port 8003
```

### Verify Agents Are Running

Check that all agents are accessible:

```bash
# Broker Agent
curl http://localhost:8000/.well-known/agent-card.json

# Wells Fargo Agent  
curl http://localhost:8001/.well-known/agent-card.json

# Bank of America Agent
curl http://localhost:8002/.well-known/agent-card.json

# Company Agent
curl http://localhost:8003/.well-known/agent-card.json
```

## 💼 Using the System

### Method 1: Direct Company Agent Interaction

Send a natural language credit request to the company agent:

```bash
curl -X POST http://localhost:8003 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "credit-request-1",
    "method": "message/send",
    "params": {
      "id": "task-credit-request",
      "message": {
        "messageId": "msg-credit-request",
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "I need a credit line for my tech company. We are TechCorp Inc, a technology company with $5M annual revenue, 750 credit score, 8 years in business, 50 employees. We need $2M credit limit for equipment purchase, prefer 12-month draw period and 24-month repayment period, ESG requirements include renewable energy and carbon reduction, preferred interest rate under 8%."
          }
        ]
      }
    }
  }'
```

### Method 2: Direct Bank Agent Testing

Test individual bank agents with structured JSON:

```bash
# Test Wells Fargo Agent
curl -X POST http://localhost:8001 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-wf",
    "method": "message/send",
    "params": {
      "id": "task-wf",
      "message": {
        "messageId": "msg-wf",
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "{\"intent_id\": \"test-001\", \"company\": {\"name\": \"TechCorp Inc\", \"industry\": \"Technology\", \"annual_revenue\": 5000000, \"credit_score\": 750, \"years_in_business\": 8, \"employee_count\": 50}, \"requested_credit_limit\": 2000000, \"credit_purpose\": \"Equipment purchase\", \"draw_period_months\": 12, \"repayment_period_months\": 24, \"esg_requirements\": \"Renewable energy and carbon reduction\", \"preferred_interest_rate\": 7.5}"
          }
        ]
      }
    }
  }'
```

## 🔐 Security Features

### Enhanced Business Logic

- **Company Agent**: Creates structured credit intents and evaluates offers based on comprehensive criteria
- **Bank Agents**: Generate complete structured offers with all required fields
- **Broker Agent**: Pure message router for efficient communication
- **Audit Trail**: Complete logging of all agent operations

### Offer Evaluation Criteria

The company agent evaluates offers based on:
- **Primary**: Composite Score (ESG-adjusted effective rate + risk penalties)
- **Secondary**: ESG Impact Score (ESG score + carbon footprint reduction bonus)
- **Financial Analysis**: Effective rate (including fees), total cost of borrowing, monthly payments
- **Risk Assessment**: Collateral requirements, personal guarantee, prepayment penalties

## 📊 Protocol Definitions

### Credit Intent Structure

```json
{
  "intent_id": "unique-identifier",
  "company": {
    "name": "Company Name",
    "industry": "Technology",
    "annual_revenue": 5000000,
    "credit_score": 750,
    "years_in_business": 8,
    "employee_count": 50
  },
  "requested_credit_limit": 2000000,
  "credit_purpose": "Equipment purchase",
  "draw_period_months": 12,
  "repayment_period_months": 24,
  "esg_requirements": "Renewable energy focus",
  "preferred_interest_rate": 7.5
}
```

### Bank Offer Structure

```json
{
  "offer_id": "unique-offer-id",
  "bank_name": "Wells Fargo",
  "bank_id": "wells-fargo",
  "approved_credit_limit": 2000000,
  "interest_rate": 6.75,
  "draw_period_months": 12,
  "repayment_period_months": 24,
  "draw_fee_percentage": 0.5,
  "unused_credit_fee": 0.25,
  "esg_impact": {
    "score": 8.5,
    "summary": "Strong ESG profile with renewable energy focus",
    "carbon_reduction_potential": 15.2
  },
  "line_of_credit_schedule": {...},
  "created_at": "2024-01-01T00:00:00Z",
  "offer_complete": true
}
```

## 🏦 Bank Policies

### Wells Fargo Agent
- **Minimum Credit Score**: 650
- **Preferred Industries**: Technology, Healthcare, Manufacturing
- **ESG Bonus**: +0.25% rate reduction for ESG score > 8.0
- **Approach**: Conservative with strong emphasis on creditworthiness

### Bank of America Agent  
- **Minimum Credit Score**: 600
- **Preferred Industries**: Technology, Fintech, Innovation
- **ESG Bonus**: +0.5% rate reduction for ESG score > 7.5
- **Innovation Bonus**: +0.25% rate reduction for tech companies
- **Approach**: Innovation-focused with competitive rates

## 🔄 Communication Flow

1. **Company Agent** receives natural language credit request
2. **Company Agent** creates structured credit intent
3. **Company Agent** sends structured intent to Broker Agent
4. **Broker Agent** routes message to all bank agents
5. **Bank Agents** generate complete structured offers with all fields
6. **Broker Agent** aggregates responses from all banks
7. **Company Agent** receives offers and evaluates them using comprehensive criteria
8. **Company Agent** selects best offer based on composite score and ESG impact

## 🛠️ Development

### Project Structure

```
wfap-solution/
├── protocols/           # Protocol definitions (Intent, Response)
├── broker_agent/        # Pure message router
├── company_agent/       # Credit request handler
├── wells_fargo_agent/   # Conservative bank agent
├── boa_agent/          # Innovation-focused bank agent
└── README.md           # This file
```

### Adding New Bank Agents

1. Create new agent directory following existing pattern
2. Update broker agent endpoints in `broker_executor.py`
3. Implement bank-specific policies and ESG criteria
4. Ensure complete structured offer generation with all required fields

### Customizing Bank Policies

Edit the respective agent files:
- `wells_fargo_agent/agent.py` - Wells Fargo policies
- `boa_agent/agent.py` - Bank of America policies

Key areas to customize:
- Credit score requirements
- Industry preferences  
- ESG bonus calculations
- Interest rate calculations

## 🐛 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Kill existing processes
pkill -f "wells_fargo_agent|boa_agent|company_agent|broker_agent"

# Wait a moment, then restart
sleep 2
```

**Gemini API Overloaded:**
- Wait 15-30 seconds and retry
- Check your API key and quota limits

**Offer Evaluation Errors:**
- Ensure bank agents are generating complete structured offers
- Check that all required fields are populated in the response protocol

**Agent Not Responding:**
- Check agent logs for errors
- Verify `.env` files contain valid API keys
- Ensure all dependencies are installed with `uv sync`

### Debug Mode

Enable verbose logging by setting environment variables:
```bash
export ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS=true
export GEMINI_MODEL=gemini-2.0-flash-001
```

## 📈 Performance

- **Response Time**: 5-15 seconds for complete workflow
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Scalability**: Easy to add new bank agents
- **Reliability**: Structured offer validation ensures data integrity

## 🔮 Future Enhancements

- **Negotiation Protocol**: Direct company-bank negotiation channels
- **Real-time Updates**: WebSocket support for live offer updates  
- **Advanced ESG**: More sophisticated ESG scoring algorithms
- **Multi-currency**: Support for different currencies
- **Regulatory Compliance**: Enhanced compliance checking

## 📄 License

This project is part of the Wells Fargo Agent Protocol implementation for hackathon purposes.

## 🤝 Contributing

1. Follow the existing code structure
2. Maintain comprehensive offer evaluation patterns
3. Add comprehensive error handling
4. Update documentation for new features
5. Test all agent interactions thoroughly
6. Ensure complete structured offer generation

---

**Ready to revolutionize corporate credit with AI agents!** 🚀
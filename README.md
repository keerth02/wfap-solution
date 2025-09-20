# Wells Fargo Agent Protocol (WFAP) - Complete Implementation

A comprehensive implementation of the Wells Fargo Agent Protocol using Google's Agent Development Kit (ADK) and A2A communication protocol. This system enables AI agents to handle corporate credit requests with JWT-signed communications, ESG evaluation, and automated offer comparison.

## 🏗️ Architecture Overview

The WFAP system consists of four main components:

```
Company Agent → [JWT Sign] → Broker Agent → [Pure Routing] → Bank Agents → [JWT Validate] → Process Request
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

**Terminal 4 - Company Agent:**
```bash
cd company_agent
uv run python __main__.py --port 8003
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
            "text": "I need a credit line for my tech company. We are TechCorp Inc, a technology company with $5M annual revenue, 750 credit score, 8 years in business, 50 employees. We need $2M for equipment purchase, prefer 36-month term, ESG requirements include renewable energy and carbon reduction, preferred interest rate under 8%."
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
            "text": "{\"intent_id\": \"test-001\", \"company\": {\"name\": \"TechCorp Inc\", \"industry\": \"Technology\", \"annual_revenue\": 5000000, \"credit_score\": 750, \"years_in_business\": 8, \"employee_count\": 50}, \"requested_amount\": 2000000, \"purpose\": \"Equipment purchase\", \"preferred_term_months\": 36, \"esg_requirements\": \"Renewable energy and carbon reduction\", \"preferred_interest_rate\": 7.5}"
          }
        ]
      }
    }
  }'
```

## 🔐 Security Features

### JWT Signing and Validation

- **Company Agent**: Signs all credit intents with JWT
- **Bank Agents**: Validate company JWTs before processing
- **Shared Keys**: Synchronized key system across all agents
- **Audit Trail**: Complete logging of all JWT operations

### Key Management

Keys are managed in `shared_keys.py`:
- `company-agent-1`: Company signing key
- `wells-fargo`: Wells Fargo signing key  
- `bank-of-america`: Bank of America signing key

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
  "requested_amount": 2000000,
  "purpose": "Equipment purchase",
  "preferred_term_months": 36,
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
  "approved_amount": 2000000,
  "interest_rate": 6.75,
  "term_months": 36,
  "monthly_payment": 61234.56,
  "total_interest": 204456.16,
  "esg_impact": {
    "score": 8.5,
    "summary": "Strong ESG profile with renewable energy focus",
    "carbon_reduction_potential": 15.2
  },
  "repayment_schedule": [...],
  "created_at": "2024-01-01T00:00:00Z",
  "jwt_signed": true
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
2. **Company Agent** creates structured credit intent and signs with JWT
3. **Company Agent** sends JWT-signed intent to Broker Agent
4. **Broker Agent** routes message to all bank agents
5. **Bank Agents** validate JWT and generate offers
6. **Bank Agents** sign offers with their own JWTs
7. **Broker Agent** aggregates responses
8. **Company Agent** receives offers and selects best one

## 🛠️ Development

### Project Structure

```
wfap-solution/
├── protocols/           # Protocol definitions (Intent, Response, JWT)
├── shared_keys.py       # Shared JWT keys for all agents
├── broker_agent/        # Pure message router
├── company_agent/       # Credit request handler
├── wells_fargo_agent/   # Conservative bank agent
├── boa_agent/          # Innovation-focused bank agent
└── README.md           # This file
```

### Adding New Bank Agents

1. Create new agent directory following existing pattern
2. Add to `shared_keys.py` with new key pair
3. Update broker agent endpoints in `broker_executor.py`
4. Implement bank-specific policies and ESG criteria

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

**JWT Validation Errors:**
- Ensure all agents are using shared keys from `shared_keys.py`
- Restart all agents after key changes

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
- **Reliability**: JWT validation ensures message integrity

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
2. Maintain JWT signing/validation patterns
3. Add comprehensive error handling
4. Update documentation for new features
5. Test all agent interactions thoroughly

---

**Ready to revolutionize corporate credit with AI agents!** 🚀
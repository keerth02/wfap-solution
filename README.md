# WFAP - Working Capital Financing Platform

A secure, multi-agent system for automated credit line processing between companies and banks.

## Quick Start

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Start All Servers
```bash
bash start_servers.sh
```

This will start:
- **Broker Agent**: `localhost:8000` (orchestrates the process)
- **Wells Fargo Agent**: `localhost:8001` (bank agent)
- **Bank of America Agent**: `localhost:8002` (bank agent)  
- **Chase Bank Agent**: `localhost:8003` (bank agent)
- **Company Agent**: `localhost:8004` (company interface)

To interact with the Company Agent with your line of credit request, navigate to localhost:8004 on your browser to start the UI.

### Communication Process:
1. **Credit Intent**: Company sends request to broker
2. **Bank Routing**: Broker forwards to all 3 banks simultaneously
3. **Questions**: Banks may ask clarifying questions
4. **Offers**: Banks respond with credit offers
5. **Evaluation**: Company evaluates all offers
6. **Negotiation**: Company can negotiate terms with specific bank
7. **Counter-Offers**: Banks provide improved terms if possible

## Security Features

- **HMAC Signatures**: All intents and offers are cryptographically signed
- **Broker Validation**: Central authority validates all signatures
- **Shared Secrets**: Each agent has unique secret keys for authentication
- **Message Integrity**: Prevents tampering with financial data

## Why This Matters

This represents the future of financial services - a **secure, automated, multi-agent system** where:

- **Companies** get instant access to multiple bank offers without manual processes
- **Banks** can compete transparently while maintaining security
- **Brokers** orchestrate complex negotiations automatically
- **All parties** benefit from cryptographic security and audit trails

The system eliminates traditional bottlenecks, reduces processing time from weeks to minutes, and provides unprecedented transparency in credit line negotiations while maintaining bank-grade security standards.

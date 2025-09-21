# WFAP Solution Installation Guide

## Installation Options

### Option 1: Using pip (requirements.txt)

```bash
# Create virtual environment
python -m venv wfap-env
source wfap-env/bin/activate  # On Windows: wfap-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### Option 2: Using uv (recommended)

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv pip install -r requirements.txt

# Or use uv sync (if uv.lock exists)
uv sync
```

## Running the Agents

### Start All Agents (except Company Agent)

```bash
# Terminal 1 - Broker Agent
cd broker_agent
python __main__.py --port 8000

# Terminal 2 - Wells Fargo Agent  
cd wells_fargo_agent
python __main__.py --port 8001

# Terminal 3 - Bank of America Agent
cd boa_agent
python __main__.py --port 8002

# Terminal 4 - Chase Bank Agent
cd chase_bank
python __main__.py --port 8003
```

### Start Company Agent

```bash
# From wfap-solution directory
adk web --port 8004
```

## Environment Setup

Create a `.env` file in each agent directory with:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
LITELLM_MODEL=gemini/gemini-2.0-flash
```

## Verification

Check that all agents are running:

```bash
curl http://localhost:8000/.well-known/agent-card.json  # Broker
curl http://localhost:8001/.well-known/agent-card.json  # Wells Fargo
curl http://localhost:8002/.well-known/agent-card.json  # Bank of America
curl http://localhost:8003/.well-known/agent-card.json  # Chase Bank
```

## Troubleshooting

- Ensure Python 3.12+ is installed
- Check that all ports (8000-8003) are available
- Verify GEMINI_API_KEY is set correctly
- Make sure all dependencies are installed

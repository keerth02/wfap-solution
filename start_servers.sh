#!/bin/bash

# Kill existing processes
pkill -f "python3.*__main__.py" 
pkill -f "adk web" 
for port in 8000 8001 8002 8003 8004; do lsof -ti:$port | xargs kill -9 2>/dev/null; done

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start servers in separate terminal windows
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/broker_agent' && python3 __main__.py --port 8000\""
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/wells_fargo_agent' && python3 __main__.py --port 8001\""
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/boa_agent' && python3 __main__.py --port 8002\""
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/chase_bank' && python3 __main__.py --port 8003\""

# Start company agent with adk web in a separate terminal
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR' && adk web --port 8004\""
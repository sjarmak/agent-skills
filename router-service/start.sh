#!/bin/bash
# Start the Agent Router Service

cd "$(dirname "$0")"

# Check if dependencies are installed
if ! python -c "import fastapi, transformers, torch" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Starting Agent Router Service on http://127.0.0.1:8765"
echo "API docs available at http://127.0.0.1:8765/docs"
echo ""

uvicorn router:app --host 127.0.0.1 --port 8765

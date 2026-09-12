#!/usr/bin/env bash
# Quick launcher for Cited Research Assistant Streamlit UI

# Resolve project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🔬 Starting Cited Research Assistant Web UI"
echo "🌐 URL: http://localhost:8501 (or http://127.0.0.1:8501)"
echo "=================================================="

# Run Streamlit using the project's virtual environment
exec "$SCRIPT_DIR/.venv/bin/streamlit" run "$SCRIPT_DIR/ui/streamlit_app.py" \
    --server.headless true \
    --server.port 8501 \
    --server.address 0.0.0.0

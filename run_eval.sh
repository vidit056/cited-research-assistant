#!/usr/bin/env bash
# Quick launcher for Evaluation Benchmark Harness

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LIMIT="${1:-3}"

echo "=================================================="
echo "📊 Running Evaluation Harness on $LIMIT Questions"
echo "=================================================="

PYTHONPATH=. "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/eval/run_eval.py" --limit "$LIMIT"

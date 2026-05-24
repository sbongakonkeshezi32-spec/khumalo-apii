#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Start FastAPI application using Uvicorn on the active PORT assigned by Render
echo "Starting Khumalo Music Platform Backend Gateway on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
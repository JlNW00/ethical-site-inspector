#!/bin/bash
# Environment setup script - idempotent
# Runs at the start of each worker session

set -e

echo "=== EthicalSiteInspector Environment Setup ==="

# Backend setup
if [ -d "backend/.venv" ]; then
    echo "Backend venv exists, checking dependencies..."
    cd backend
    .venv/Scripts/python.exe -m pip install -r requirements.txt --quiet 2>/dev/null || \
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt --quiet 2>/dev/null || true
    
    # Run migrations
    .venv/Scripts/python.exe -m alembic upgrade head 2>/dev/null || \
    .venv\\Scripts\\python.exe -m alembic upgrade head 2>/dev/null || true
    cd ..
else
    echo "Creating backend venv..."
    cd backend
    python -m venv .venv
    .venv/Scripts/python.exe -m pip install -r requirements.txt --quiet 2>/dev/null || \
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt --quiet 2>/dev/null || true
    .venv/Scripts/python.exe -m alembic upgrade head 2>/dev/null || \
    .venv\\Scripts\\python.exe -m alembic upgrade head 2>/dev/null || true
    cd ..
fi

# Frontend setup
if [ -d "frontend/node_modules" ]; then
    echo "Frontend node_modules exists, skipping install..."
else
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "=== Setup complete ==="

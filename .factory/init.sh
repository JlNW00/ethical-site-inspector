#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

# Backend: install dependencies including nova-act
if [ -d "backend/.venv" ]; then
  echo "Installing backend dependencies..."
  backend/.venv/Scripts/pip.exe install -q -r backend/requirements.txt 2>/dev/null || \
    backend/.venv/Scripts/python.exe -m pip install -q -r backend/requirements.txt
  
  # Ensure nova-act is installed
  backend/.venv/Scripts/pip.exe show nova-act >/dev/null 2>&1 || \
    backend/.venv/Scripts/pip.exe install -q nova-act
fi

# Run migrations
if [ -f "backend/alembic.ini" ]; then
  echo "Running database migrations..."
  cd backend && .venv/Scripts/python.exe -m alembic upgrade head 2>/dev/null && cd ..
fi

# Frontend: install dependencies
if [ -f "frontend/package.json" ]; then
  echo "Installing frontend dependencies..."
  cd frontend && npm install --silent 2>/dev/null && cd ..
fi

echo "Init complete."

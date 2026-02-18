#!/bin/bash

# WireGuard VPN Admin - Start Script

echo "Starting WireGuard VPN Admin..."

# Start backend (FastAPI)
echo "Starting backend..."
cd "$(dirname "$0")/backend"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend (Vue.js dev server)
echo "Starting frontend..."
cd "$(dirname "$0")/frontend"
npm run dev &
FRONTEND_PID=$!

echo "WireGuard VPN Admin is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait

#!/bin/bash

# Start the Resume Builder (Backend + Frontend)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "🚀 Starting RAG ATS Resume Builder..."
echo ""

# Start Backend
echo "📦 Starting Backend (port 8000)..."
cd "$PROJECT_ROOT"
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo ""

# Give backend time to start
sleep 2

# Start Frontend
echo "⚛️  Starting Frontend (port 3000)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Resume Builder is running!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Wait for both processes and handle Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo '👋 Services stopped'; exit" SIGINT

wait

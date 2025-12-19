#!/usr/bin/env bash
set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Virtualenv activation script not found in $VENV_DIR/bin/activate"
  exit 1
fi

pip install --upgrade pip
pip install -r requirements.txt

echo "✅ venv ready. To run backend:"
echo "  source $VENV_DIR/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000 --app-dir backend"

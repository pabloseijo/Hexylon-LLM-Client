#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR"
FRONTEND_DIR="$ROOT_DIR/ui"

command -v uv >/dev/null 2>&1 || { echo "Error: uv no está instalado."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm no está instalado."; exit 1; }

if [[ ! -f "$BACKEND_DIR/src/api/server.py" ]]; then
  echo "Error: no se encuentra src/api/server.py"
  exit 1
fi

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  echo "Error: no se encuentra ui/package.json"
  exit 1
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "Deteniendo backend y frontend..."

  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Iniciando backend..."
(
  cd "$BACKEND_DIR"
  PYTHONPATH=src uv run python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8001
) &
BACKEND_PID=$!

echo "Iniciando frontend..."
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host 127.0.0.1 --port 5173
) &
FRONTEND_PID=$!

echo "Backend PID : $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Frontend disponible en http://127.0.0.1:5173"
echo "Backend disponible en http://127.0.0.1:8001"

wait
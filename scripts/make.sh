#!/usr/bin/env bash
set -euo pipefail

CMD=${1:-help}

case "$CMD" in
  dev)
    echo "Starting dev environment..."
    docker compose up -d postgres qdrant
    cd backend && uvicorn app.main:app --reload --port 8000
    ;;
  test)
    cd backend && pytest -v
    ;;
  migrate)
    cd backend && alembic upgrade head
    ;;
  migration)
    cd backend && alembic revision --autogenerate -m "${2:-auto}"
    ;;
  seed)
    cd backend && python scripts/seed.py
    ;;
  prod)
    docker compose up --build -d
    ;;
  clean)
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf frontend/dist
    echo "Clean done."
    ;;
  *)
    echo "Usage: bash scripts/make.sh <command>"
    echo "Commands: dev | test | migrate | migration | seed | prod | clean"
    ;;
esac

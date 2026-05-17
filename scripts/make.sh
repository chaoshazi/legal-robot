#!/usr/bin/env bash
set -euo pipefail

CMD=${1:-help}

case "$CMD" in
  dev)
    echo "Starting Docker infrastructure (postgres, qdrant, redis, monitoring)..."
    docker compose up -d postgres qdrant-node-0 qdrant-node-1 qdrant-node-2 redis \
      prometheus grafana loki promtail langfuse
    docker compose stop backend frontend nginx 2>/dev/null || true
    echo ""
    echo "=========================================="
    echo " 开发环境已就绪"
    echo "=========================================="
    echo ""
    echo "请在新终端中执行："
    echo ""
    echo "  后端:  cd backend && uvicorn app.main:app --reload --port 8888"
    echo "  前端:  cd frontend && npm run dev"
    echo ""
    echo "访问:  https://101.37.231.123:5175/"
    echo "       http://localhost:8888/health"
    echo ""
    echo "监控:  http://localhost:9091/ (Prometheus)"
    echo "       http://localhost:3031/ (Grafana)"
    echo "       http://localhost:3002/ (LangFuse)"
    echo ""
    ;;
  dev:backend)
    cd backend && uvicorn app.main:app --reload --port 8888
    ;;
  dev:frontend)
    cd frontend && npm run dev
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
  stop)
    docker compose stop backend frontend nginx
    ;;
  clean)
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf frontend/dist
    echo "Clean done."
    ;;
  *)
    echo "Usage: bash scripts/make.sh <command>"
    echo ""
    echo "开发:"
    echo "  dev           启动 Docker 基础设施 + 提示启动前后端"
    echo "  dev:backend   启动后端 (uvicorn :8888)"
    echo "  dev:frontend  启动前端 (npm run dev)"
    echo "  stop          停掉 Docker 里的前后端 (释放端口)"
    echo ""
    echo "其他:"
    echo "  test          运行后端测试"
    echo "  migrate       执行数据库迁移"
    echo "  migration     [描述] 创建新迁移"
    echo "  seed          初始化种子数据"
    echo "  prod          生产部署 (docker compose up --build)"
    echo "  clean         清理缓存文件"
    ;;
esac

#!/usr/bin/env bash
# Linting (Ruff: pyflakes, isort, McCabe, etc.). Uso: lint.sh [etl|api|all]
source "$(dirname "$0")/lib.sh"

for svc in $(resolve_targets "${1:-all}"); do
    echo ">> ruff check services/$svc"
    uv run ruff check "services/$svc"
done

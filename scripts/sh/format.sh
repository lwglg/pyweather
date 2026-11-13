#!/usr/bin/env bash
# Formatação (Ruff format). Uso: format.sh [etl|api|all] [--check]
source "$(dirname "$0")/lib.sh"

target="${1:-all}"
mode="${2:-}"

for svc in $(resolve_targets "$target"); do
    if [[ "$mode" == "--check" ]]; then
        echo ">> ruff format --check services/$svc"
        uv run ruff format --check "services/$svc"
    else
        echo ">> ruff format services/$svc"
        uv run ruff format "services/$svc"
        uv run ruff check --select I --fix "services/$svc"
    fi
done

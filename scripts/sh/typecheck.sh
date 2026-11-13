#!/usr/bin/env bash
# Verificação estática de tipos (Mypy strict). Uso: typecheck.sh [etl|api|all]
source "$(dirname "$0")/lib.sh"

for svc in $(resolve_targets "${1:-all}"); do
    echo ">> mypy services/$svc"
    uv run mypy "services/$svc"
done

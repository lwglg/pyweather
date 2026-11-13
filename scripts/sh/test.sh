#!/usr/bin/env bash
# Testes unitários com cobertura mínima de 80% por serviço.
# Uso: test.sh [etl|api|all]
source "$(dirname "$0")/lib.sh"

MIN_COVERAGE="${MIN_COVERAGE:-80}"

for svc in $(resolve_targets "${1:-all}"); do
    echo ">> pytest services/$svc (cobertura mínima: ${MIN_COVERAGE}%)"
    COVERAGE_FILE=".coverage.${svc}" uv run pytest "services/${svc}/tests" \
        -m "not integration" \
        --cov="pyweather_${svc}" \
        --cov-report=term-missing \
        --cov-report="xml:coverage-${svc}.xml" \
        --cov-fail-under="${MIN_COVERAGE}"
done

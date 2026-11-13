#!/usr/bin/env bash
# Funções utilitárias compartilhadas pelos scripts de apoio.
# Uso: source "$(dirname "$0")/lib.sh"

set -euo pipefail

# Sempre executa a partir da raiz do repositório.
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

# Valida o alvo (serviço) informado: etl | api | all
resolve_targets() {
    local target="${1:-all}"
    case "$target" in
        etl) echo "etl" ;;
        api) echo "api" ;;
        all) echo "etl api" ;;
        *)
            echo "Alvo inválido: '$target' (use: etl | api | all)" >&2
            exit 2
            ;;
    esac
}

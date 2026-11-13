#!/usr/bin/env bash
# Smoke tests de ponta a ponta: toda a stack em contêineres + collection do Postman (Newman).
#
# Uso: smoke.sh [all|up|run|down|logs|local]
#   all    (padrão) sobe a stack, executa a collection e derruba tudo (down -v), mesmo em caso de falha
#   up     constrói e sobe database, mock-openweather, etl e api (aguarda a API ficar saudável)
#   run    executa a collection com o Newman dentro da rede do Compose (stack já no ar)
#   down   derruba a stack e remove o volume
#   logs   mostra os logs da stack
#   local  executa a MESMA collection com o environment `local` contra http://localhost:8000
#          (requer Node/npx; use com `make up` ou `make api-dev`)
#
# O código de saída é o do Newman (0 = todas as asserções passaram).
source "$(dirname "$0")/lib.sh"

PROJECT="gntech-pyweather-smoke"
COMPOSE=(docker compose
    -f infra/docker/docker-compose.yml
    -f infra/docker/docker-compose.smoke.yml
    -p "${PROJECT}")
RESULTS_DIR="build/smoke"
NEWMAN_VERSION="${NEWMAN_VERSION:-6.2.1}"

# O Newman roda como o usuário `node` (UID 1000) dentro do contêiner, que costuma ser diferente do
# dono do diretório no host (ex.: o runner do GitHub Actions usa o UID 1001). Sem permissão de
# escrita, o relatório JUnit falha com `EACCES: permission denied, open '/results/newman-junit.xml'`.
prepare_results_dir() {
    mkdir -p "${RESULTS_DIR}"
    chmod a+rwx "${RESULTS_DIR}"
}

smoke_up() {
    prepare_results_dir
    echo ">> subindo a stack de smoke (${PROJECT})"
    "${COMPOSE[@]}" up -d --build --wait --wait-timeout 300 api mock-openweather
}

smoke_run() {
    prepare_results_dir
    echo ">> executando a collection (Newman) na rede do Compose"
    "${COMPOSE[@]}" --profile smoke run --rm --build newman
}

smoke_logs() {
    "${COMPOSE[@]}" --profile smoke logs --no-color --tail=200
}

smoke_down() {
    echo ">> derrubando a stack de smoke e removendo o volume"
    "${COMPOSE[@]}" --profile smoke down --volumes --remove-orphans
}

smoke_local() {
    mkdir -p "${RESULTS_DIR}"
    echo ">> executando a collection (environment local) em http://localhost:8000"
    npx --yes "newman@${NEWMAN_VERSION}" run tests/postman/pyweather.postman_collection.json \
        --environment tests/postman/pyweather.local.postman_environment.json \
        --reporters cli,junit \
        --reporter-junit-export "${RESULTS_DIR}/newman-junit-local.xml" \
        --timeout-request 10000
}

smoke_all() {
    local status=0
    # Teardown garantido (Ctrl+C, falha de build, falha de asserção).
    trap 'smoke_down || true' EXIT
    smoke_up && smoke_run || status=$?
    if [ "${status}" -ne 0 ]; then
        echo "!! smoke tests falharam (código ${status}); logs dos serviços:" >&2
        smoke_logs || true
    fi
    exit "${status}"
}

case "${1:-all}" in
    all) smoke_all ;;
    up) smoke_up ;;
    run) smoke_run ;;
    down) smoke_down ;;
    logs) smoke_logs ;;
    local) smoke_local ;;
    *)
        echo "Ação inválida: '${1}' (use: all | up | run | down | logs | local)" >&2
        exit 2
        ;;
esac

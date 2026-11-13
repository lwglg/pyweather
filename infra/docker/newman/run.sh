#!/bin/sh
# Espera a stack ficar pronta (ETL concluiu a primeira extração) e executa a collection com o Newman.
# O código de saída é o do Newman: 0 = todas as asserções passaram.
set -eu

: "${POSTMAN_COLLECTION:=pyweather.postman_collection.json}"
: "${POSTMAN_ENVIRONMENT:=pyweather.docker.postman_environment.json}"
: "${WAIT_URL:=http://api:8000/v1/locations/1/alerts}"
: "${WAIT_TIMEOUT:=180}"
: "${RESULTS_DIR:=/results}"

# O ETL grava na ordem: local → atual → horária → diária → alertas. Quando a lista de alertas tem
# ao menos um item, todas as etapas anteriores já foram concluídas.
echo ">> aguardando dados do ETL em ${WAIT_URL} (limite: ${WAIT_TIMEOUT}s)"
elapsed=0
until wget -qO- "${WAIT_URL}" 2>/dev/null | grep -Eq '"total": ?[1-9]'; do
    if [ "${elapsed}" -ge "${WAIT_TIMEOUT}" ]; then
        echo "!! tempo esgotado: o ETL não disponibilizou dados em ${WAIT_TIMEOUT}s" >&2
        exit 2
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo ">> dados disponíveis após ~${elapsed}s; executando a collection"

mkdir -p "${RESULTS_DIR}" 2>/dev/null || true
exec newman run "/postman/${POSTMAN_COLLECTION}" \
    --environment "/postman/${POSTMAN_ENVIRONMENT}" \
    --reporters cli,junit \
    --reporter-junit-export "${RESULTS_DIR}/newman-junit.xml" \
    --timeout-request 10000 \
    --color on

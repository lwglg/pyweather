# 7. Desenvolvimento e operação

[← Índice](../../README.md) · Anterior: [6. API](06-api.md) · Próximo: [8. Testes de sanidade](08-smoke-tests.md)

## Estrutura do repositório

```text
pyweather/
├── .github/workflows/        etl-qa.yml · api-qa.yml (QA ≥ 80 %) · smoke.yml (ponta a ponta)
├── infra/docker/
│   ├── etl/       Dockerfile · .env
│   ├── api/       Dockerfile · .env
│   ├── database/  Dockerfile · .env · init/
│   ├── mock-openweather/  Dockerfile · .env · server.py   (só para smoke)
│   ├── newman/    Dockerfile · .env · run.sh               (só para smoke)
│   ├── docker-compose.yml
│   └── docker-compose.smoke.yml   (override do smoke)
├── tests/postman/            collection + environments (local, docker)
├── services/
│   ├── etl/pyweather_etl/    domain · application · infrastructure · cli · composition · config
│   │   └── tests/
│   └── api/pyweather_api/    domain · application · infrastructure · presentation · main · config
│       └── tests/
├── docs/md/                  esta documentação (+ diagramas/*.mmd)
├── scripts/sh/               lint · format · typecheck · test · docs · smoke  (chamados via make)
├── pyproject.toml · uv.lock  projeto "services" (grupos de dependências: etl, api, dev)
├── ruff.toml                 lint/format (imports, McCabe ≤ 10, separação de código)
├── Makefile                  automação
└── README.md
```

**Um único `pyproject.toml`/`uv.lock`** na raiz cobre os dois serviços por meio de **grupos de
dependências** (`etl`, `api`, `dev`). Cada imagem Docker instala somente o seu grupo
(`uv sync --only-group …`), e o CI instala só o grupo do serviço testado — o que também garante que um
serviço não dependa, sem querer, das bibliotecas do outro.

## Qualidade

| Verificação | Ferramenta | Comando | Critério |
|-------------|-----------|---------|----------|
| Formatação | Ruff (`format`) | `make format-check` / `make format` | Sem diferenças |
| Lint | Ruff (`check`) | `make lint` | pyflakes, isort, pep8-naming, pyupgrade, bugbear, McCabe ≤ 10, `DTZ` (datas com fuso), pytest-style, sem `print` |
| Tipagem | mypy `strict` + plugin Pydantic | `make typecheck` | Sem erros |
| Testes unitários | pytest + pytest-cov | `make test` | **Cobertura ≥ 80 %** por serviço (`--cov-fail-under`) |
| Tudo | — | `make qa` | — |
| Smoke (ponta a ponta) | Postman/Newman + Docker Compose | `make smoke` | Todas as asserções passam ([seção 8](08-smoke-tests.md)) |
| Diagramas | `scripts/sh/docs.sh` | `make docs` / `make docs-check` | Blocos Mermaid iguais aos `.mmd` |

Todos aceitam `TARGET=etl|api|all`. Cobertura medida na escrita: **ETL 94,6 %** (94 testes) e
**API 100 %** (46 testes); a pasta de migrações (`env.py` e `versions/`) só é exercitada
indiretamente, via `upgrade_to_head` nos testes.

### Estratégia de testes

- **Domínio e aplicação**: testes puros com *fakes* das portas.
- **Cliente OpenWeather**: `httpx.MockTransport` — cobre paginação, retentativas, `Retry-After`,
  401/404/429/5xx, falhas de rede e payloads malformados, **sem rede nem chave**.
- **Persistência**: SQLite em memória, com o esquema criado **pelas migrações Alembic reais** (ETL) ou
  por `SQLModel.metadata.create_all` (API); verifica idempotência e filtros.
- **API**: `TestClient` com repositório real sobre SQLite — inclui o contrato OpenAPI em português.
- **Ponta a ponta**: `make smoke` sobe a stack completa (com um mock da OpenWeather) e executa a
  collection do Postman via Newman — veja a [seção 8](08-smoke-tests.md). Não entra no `make qa`
  (exige Docker).
- **Limite honesto**: SQLite não é PostgreSQL. A migração, as cargas idempotentes e as consultas da
  API foram **verificadas manualmente contra um PostgreSQL real** durante o desenvolvimento, mas
  **não há** teste de integração automatizado com PostgreSQL no CI (o *marker* `integration` está
  reservado para isso — veja "Próximos passos").

### Integração contínua

`.github/workflows/etl-qa.yml` e `api-qa.yml` rodam, para o respectivo serviço (disparados por
alterações em `services/<x>/`, `pyproject.toml`, `uv.lock`, `ruff.toml` ou `scripts/`): instalação do
grupo → `format-check` → `lint` → `typecheck` → `test` (falha abaixo de 80 %) → publicação do `coverage-<x>.xml`.

`.github/workflows/smoke.yml` executa `make smoke` (alterações em `services/`, `infra/docker/`,
`tests/postman/` etc., ou manualmente) e publica `build/smoke/newman-junit.xml`.

## Configuração do ETL (variáveis de ambiente)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OPENWEATHER_API_KEY` | — **(obrigatória)** | Chave da OpenWeather. Em Docker: `infra/docker/etl/.env.local` ou variável do shell |
| `OPENWEATHER_BASE_URL` | `https://api.openweathermap.org` | Base das APIs |
| `OPENWEATHER_UNITS` | `metric` | `standard`, `metric` ou `imperial` (veja o alerta sobre unidades em [Domínio](03-dominio.md)) |
| `OPENWEATHER_LANG` | `pt_br` | Idioma das descrições |
| `HTTP_TIMEOUT_SECONDS` / `HTTP_MAX_RETRIES` | `15` / `3` | Tempo limite e retentativas (0–10) |
| `CITY_NAME` / `CITY_STATE` / `CITY_COUNTRY` | `Florianópolis` / `Santa Catarina` / `BR` | Cidade-alvo (o estado só entra na busca para `US`) |
| `CITY_LATITUDE` / `CITY_LONGITUDE` | — | Se **ambas** informadas, dispensam a geocodificação (informar só uma é erro) |
| `ETL_INTERVAL_SECONDS` | `3600` (mín. 60) | Intervalo entre extrações no modo `serve` |
| `ETL_HOURLY_PAGES` / `ETL_DAILY_PAGES` | `3` / `1` (0–10) | Páginas por extração (a API entrega até 20 horas e 10 dias por página); `0` desativa |
| `ETL_INCLUDE_ALERTS` | `true` | Busca os detalhes dos alertas ativos |
| `POSTGRES_*` · `DATABASE_URL` | veja [API](06-api.md#configuração-variáveis-de-ambiente-da-api) | Banco (no Compose, `POSTGRES_HOST=database`) |
| `LOG_LEVEL` | `INFO` | Nível de log |

Comandos do ETL (`python -m pyweather_etl <cmd>`): `migrate`, `run` (uma extração), `serve` (laço
periódico; padrão da imagem), `healthcheck`.

## Operação

| Tarefa | Como |
|--------|------|
| Trocar de cidade | Altere `CITY_*` em `infra/docker/etl/.env` e `make restart SERVICE=etl`. A cidade anterior **permanece** no banco, com seu histórico. |
| Monitorar **várias** cidades | Não suportado nesta versão (um processo ETL = uma cidade). Suba outra instância do ETL com outro `.env` apontando ao mesmo banco. |
| Extração imediata | `make shell SERVICE=etl` → `python -m pyweather_etl run` |
| Logs | `make logs` / `make logs SERVICE=api` |
| Backup | Faça *dump* do banco (`pg_dump`) a partir do contêiner `gntech-pyweather-database` ou do volume `gntech-pyweather-pgdata` |
| Zerar tudo | `make clean-docker` (**apaga** o volume) |

## Limitações conhecidas e próximos passos

- **Teste de integração com PostgreSQL** automatizado no CI (`pytest -m integration`, serviço `postgres` no workflow).
- **Ordem de inicialização**: a API pode responder 500 nos primeiros segundos da primeira subida,
  antes de o ETL terminar a migração ([detalhes](02-arquitetura.md#implantação-docker-compose)).
  Uma melhoria possível: um serviço de migração dedicado (`depends_on: service_completed_successfully`).
- **Sem autenticação nem limitação de taxa** na API; **uma cidade por instância** do ETL.
- **Sem retenção/expurgo**: o histórico de observações cresce indefinidamente (~1 linha/hora por
  local no padrão); considere particionamento ou limpeza se necessário.
- As imagens Docker **não foram construídas** no ambiente em que este projeto foi desenvolvido (sem
  *daemon* Docker): o `docker-compose.yml` e o `docker-compose.smoke.yml` foram validados
  sintaticamente (`docker compose config`) e o passo de dependências dos Dockerfiles foi reproduzido
  com `uv`. Rode `make docker-build` e `make smoke` na primeira utilização.
- A integração com a **One Call API 4.0** foi implementada conforme a documentação oficial
  (caminhos, parâmetros e campos conferidos) e testada com respostas simuladas; **não foi exercitada
  contra a API real**, por não haver chave durante o desenvolvimento.

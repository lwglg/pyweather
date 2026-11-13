# 1. Apresentação, preliminares e início rápido

[← Voltar ao índice](../../README.md) · Próximo: [2. Arquitetura](02-arquitetura.md)

## O que é o pyweather

Plataforma de software que **coleta dados climáticos de uma cidade** na API pública da
[OpenWeather](https://openweathermap.org/api) (APIs do **plano gratuito**), **persiste-os em
PostgreSQL** e os **disponibiliza por uma API RESTful** com filtros adequados aos dados.

| Serviço    | Papel                                                                        | Tecnologia principal             | Imagem                              |
|------------|------------------------------------------------------------------------------|----------------------------------|-------------------------------------|
| `etl`      | Extrai da OpenWeather, transforma em entidades de domínio e carrega no banco | Python, httpx, SQLAlchemy, Alembic | `gntech/pyweather-etl:latest`       |
| `api`      | Serve os dados por HTTP (documentação OpenAPI/Swagger em português)         | Python, FastAPI, SQLModel        | `gntech/pyweather-api:latest`       |
| `database` | Armazena locais, observações, previsões e alertas                            | PostgreSQL                       | `gntech/pyweather-database:latest`  |

Os contêineres seguem o padrão `gntech-pyweather-<serviço>`.

## Ferramentas e versões

| Ferramenta     | Versão       | Observação                                                                  |
|----------------|--------------|-----------------------------------------------------------------------------|
| Python         | **3.14** (3.14.6) | Veja a nota abaixo sobre "LTS".                                        |
| uv             | 0.11.32      | Gerenciador de pacotes e do ambiente virtual; `uv.lock` versionado.         |
| FastAPI        | 0.162.5      | Com as bibliotecas recomendadas na sua documentação: Pydantic, SQLModel, Uvicorn, pydantic-settings. |
| Pydantic       | 2.14.3       | Validação, esquemas e configuração.                                         |
| SQLModel       | 0.0.49       | Tabelas de **leitura** da API.                                              |
| SQLAlchemy     | 2.1.8        | Persistência do ETL (e base do SQLModel).                                   |
| Alembic        | 1.20.1       | Migrações do esquema (de responsabilidade do ETL).                          |
| httpx          | 0.28.1       | Cliente HTTP da OpenWeather.                                                |
| psycopg        | 3.3.9        | Driver PostgreSQL (`postgresql+psycopg`).                                   |
| PostgreSQL     | 18 (`postgres:18-alpine`) |                                                                |
| Ruff · mypy · pytest | 0.17.5 · 2.4.1 · 9.2.0 | Formatação/lint · tipagem estrita · testes com cobertura.   |

> **Sobre "Python LTS".** O Python não possui versões LTS formais; cada versão recebe correções por
> ~2 anos e segurança por ~5. Adotou-se a **linha 3.14** (patch 3.14.6) por ser a estável mais madura
> com suporte completo do ecossistema. O 3.15.0 foi publicado há poucas semanas e, no momento da
> escrita, o catálogo de interpretadores do próprio `uv` ainda listava apenas a beta 4. Para migrar
> no futuro, altere `.python-version`, `requires-python` e `[tool.mypy] python_version` no
> `pyproject.toml`, `target-version` no `ruff.toml` e o argumento `PYTHON_VERSION` dos
> Dockerfiles; depois rode `make lock` e `make qa`.

## Pré-requisitos

- **Docker** com **Docker Compose v2** (≥ 2.24, por causa de `env_file` opcional) e **make**.
- Uma **chave da OpenWeather** (o plano gratuito basta). O ETL usa apenas APIs gratuitas — *Current
  Weather Data*, *5 Day / 3 Hour Forecast* e *Geocoding* —, **não** a *One Call API*, que exige
  assinatura. Uma resposta HTTP 401 indica chave inválida, **recém-criada** (a ativação pode levar
  algumas horas) ou sem acesso ao produto.
- Para desenvolvimento sem Docker: **uv** e um PostgreSQL acessível.

## Início rápido

```bash
# 1. Chave da OpenWeather (arquivo ignorado pelo git)
echo "OPENWEATHER_API_KEY=sua-chave" > infra/docker/etl/.env.local

# 2. (Opcional) escolha a cidade em infra/docker/etl/.env  → CITY_NAME, CITY_STATE, CITY_COUNTRY

# 3. Constrói as imagens e sobe PostgreSQL + ETL + API
make up

# 4. Acompanha a primeira extração
make logs SERVICE=etl

# 5. Consulta
open http://localhost:8000/docs                         # Swagger UI (português)
curl "http://localhost:8000/v1/locations"
curl "http://localhost:8000/v1/locations/1/current"
curl "http://localhost:8000/v1/locations/1/forecast/hourly?min_pop=0.5&limit=10"
```

A cidade padrão é **Florianópolis/SC**. O ETL migra o banco ao iniciar e extrai a cada
`ETL_INTERVAL_SECONDS` (3600 s por padrão). Para encerrar: `make down` (mantém os dados) ou
`make clean-docker` (**apaga** o volume).

> **Custo de chamadas.** Cada extração consome 2 chamadas (condições atuais + previsão de 5 dias),
> mais 1 de geocodificação na primeira vez (se não houver coordenadas). Com o intervalo padrão:
> ~48 chamadas/dia, muito abaixo do limite do plano gratuito (60 chamadas/minuto). Com
> `ETL_INCLUDE_FORECAST=false` caem para 1 por extração.

> **Limitações do plano gratuito.** A previsão tem **passos de 3 horas** (não de 1 hora) por 5 dias;
> o **resumo diário** é calculado pelo ETL a partir deles; **alertas meteorológicos não são
> fornecidos** (o endpoint existe, mas retorna lista vazia); não há índice UV, ponto de orvalho nem
> dados lunares. Detalhes em [Domínio](03-dominio.md#mapeamento-do-plano-gratuito).

### Desenvolvimento local (sem Docker)

```bash
make install                                   # uv sync --locked --all-groups
export POSTGRES_HOST=localhost POSTGRES_PASSWORD=... OPENWEATHER_API_KEY=...
make migrate && make etl-run                   # cria o esquema e extrai uma vez
make api-dev                                   # API com autoreload em :8000
make qa                                        # format-check + lint + mypy + testes (≥ 80%)
```

## Comandos úteis (`make help`)

| Grupo      | Alvos                                                                                  |
|------------|----------------------------------------------------------------------------------------|
| Dependências | `install`, `install-etl`, `install-api`, `lock`, `upgrade`                           |
| Qualidade  | `format`, `format-check`, `lint`, `typecheck`, `test`, `qa` — aceitam `TARGET=etl\|api\|all` |
| Execução   | `migrate`, `etl-run`, `etl-serve`, `api-dev`                                           |
| Smoke      | `smoke`, `smoke-up`, `smoke-run`, `smoke-down`, `smoke-logs`, `smoke-local`            |
| Docker     | `docker-build`, `up`, `down`, `restart`, `ps`, `logs`, `shell`, `clean-docker`         |
| Docs       | `docs`, `docs-check`                                                                   |

## Mapa da documentação

| Seção | Conteúdo |
|-------|----------|
| [2. Arquitetura e design pattern](02-arquitetura.md) | Visão de contexto, camadas DDD, decisões e implantação |
| [3. Modelagem de domínio e entidades](03-dominio.md) | Entidades, objetos de valor, portas e modelo relacional |
| [4. Casos de uso](04-casos-de-uso.md) | Atores, casos de uso e fluxos |
| [5. Sequências](05-sequencias.md) | ETL, tratamento de falhas e consulta pela API |
| [6. Referência da API](06-api.md) | Endpoints, filtros, erros e exemplos |
| [7. Desenvolvimento e operação](07-desenvolvimento.md) | Estrutura, qualidade, CI, configuração e limitações |
| [8. Testes de sanidade](08-smoke-tests.md) | Collection Postman, stack de smoke no Compose, `make smoke` |

# 5. Sequências

[← Índice](../../README.md) · Anterior: [4. Casos de uso](04-casos-de-uso.md) · Próximo: [6. API](06-api.md)

## 5.1 Extração, transformação e carga (UC-01)

<!-- mmd:sequencia-etl -->
```mermaid
sequenceDiagram
    autonumber
    participant R as PeriodicRunner
    participant U as SyncWeatherUseCase
    participant G as OpenWeatherClient (geocoding)
    participant P as OpenWeatherClient (weather/forecast)
    participant Repo as SqlAlchemyWeatherRepository
    participant DB as PostgreSQL

    R->>U: execute()
    alt local ainda não resolvido
        opt coordenadas não informadas
            U->>G: locate(LocationSpec)
            G-->>U: Location (lat, lon)
        end
        U->>Repo: upsert_location(location)
        Repo->>DB: SELECT/INSERT/UPDATE locations
        Repo-->>U: Location com id
    end
    U->>P: fetch_current(coordinates)
    P-->>U: CurrentSnapshot (observação e fuso)
    U->>Repo: update_timezone() + save_current()
    Repo->>DB: UPSERT (merge) current_weather
    opt ETL_INCLUDE_FORECAST
        U->>P: fetch_forecast(coordinates)
        P-->>U: Forecast (passos de 3 h + resumo diário derivado)
        U->>Repo: save_hourly() + save_daily()
        Repo->>DB: UPSERT hourly_forecasts e daily_forecasts
    end
    U-->>R: SyncReport
    Note over R: aguarda ETL_INTERVAL_SECONDS<br/>(interrompível por SIGTERM/SIGINT)
```
<!-- /mmd -->

Notas:

- O local é resolvido e gravado **uma vez** por processo; nas execuções seguintes reutiliza-se o `id`.
- Cada operação do repositório é uma **transação própria**; uma falha numa etapa (ex.: previsão
  diária) não desfaz o que já foi gravado em etapas anteriores — e como a carga é idempotente, a
  próxima execução completa o que faltou.
- A previsão de 5 dias vem em **uma única chamada**: o mapeador ordena os passos, descarta
  duplicados e deriva o resumo diário por dia civil local ([regras](03-dominio.md#mapeamento-do-plano-gratuito)).
- O `PeriodicRunner` captura exceções do ciclo (log com *stack trace*) e continua; `SIGTERM`/`SIGINT`
  interrompem a espera e encerram graciosamente após o ciclo corrente.

## 5.2 Tratamento de falhas na chamada à OpenWeather

<!-- mmd:sequencia-retry -->
```mermaid
sequenceDiagram
    autonumber
    participant C as OpenWeatherClient
    participant OW as OpenWeather

    C->>OW: GET /data/2.5/weather
    OW-->>C: 503 (ou 429 / falha de rede)
    Note over C: espera Retry-After (máx. 60 s)<br/>ou recuo exponencial 1 s, 2 s, 4 s…
    C->>OW: nova tentativa
    OW-->>C: 200 + JSON
    Note over C: 401 → AuthenticationError (sem retry)<br/>404 → ResourceNotFoundError<br/>tentativas esgotadas → RateLimitError / ProviderUnavailableError
```
<!-- /mmd -->

| Resposta | Comportamento |
|----------|---------------|
| 200 | Converte o JSON; formato inesperado → `PayloadError` |
| 401 | `AuthenticationError` imediato (chave inválida, ainda não ativada ou sem acesso ao produto) |
| 404 | `ResourceNotFoundError` |
| 429, 500, 502, 503, 504, falha de rede | Até `HTTP_MAX_RETRIES` novas tentativas: espera `Retry-After` (limitado a 60 s) ou `1 s × 2ⁿ`; esgotadas → `RateLimitError` / `ProviderUnavailableError` |
| outros 4xx | `WeatherProviderError` |

## 5.3 Consulta pela API (UC-08)

<!-- mmd:sequencia-api -->
```mermaid
sequenceDiagram
    autonumber
    actor K as Cliente
    participant RT as Router (FastAPI)
    participant S as WeatherQueryService
    participant Repo as SqlModelWeatherReadRepository
    participant DB as PostgreSQL

    K->>RT: GET /v1/locations/1/forecast/hourly?min_pop=0.5&limit=20
    RT->>RT: valida parâmetros (Pydantic) → HourlyFilter + Pagination
    RT->>S: list_hourly(1, filtro, página)
    S->>Repo: get_location(1)
    Repo->>DB: SELECT locations WHERE id = 1
    alt local inexistente
        Repo-->>S: None
        S-->>RT: LocationNotFoundError
        RT-->>K: 404 {"detail": "Local 1 não encontrado."}
    else existe
        S->>S: valida período e limites
        alt filtro inconsistente
            S-->>RT: InvalidFilterError
            RT-->>K: 422 {"detail": "..."}
        else válido
            S->>Repo: list_hourly(1, filtro, página)
            Repo->>DB: SELECT COUNT(*) + SELECT ... LIMIT/OFFSET
            Repo-->>S: Page[HourlyForecast]
            S-->>RT: Page
            RT-->>K: 200 PageOut{items, total, limit, offset}
        end
    end
```
<!-- /mmd -->

Notas:

- A validação de **formato** (tipos, faixas, parâmetros desconhecidos) ocorre na borda (Pydantic →
  422 padrão do FastAPI); a validação de **regras** (período invertido, local inexistente) ocorre no
  serviço de aplicação e é traduzida em um único ponto (`presentation/api/errors.py`).
- A listagem faz duas consultas: `COUNT(*)` com os mesmos filtros (para `total`) e a página
  (`ORDER BY … LIMIT … OFFSET …`).

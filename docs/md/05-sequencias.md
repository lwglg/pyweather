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
    participant P as OpenWeatherClient (one call)
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
    P-->>U: CurrentSnapshot (observação, fuso, alert_ids)
    U->>Repo: update_timezone() + save_current()
    Repo->>DB: UPSERT (merge) current_weather
    loop páginas horárias (1h)
        U->>P: fetch_hourly(coordinates, pages)
        P-->>U: HourlyForecast[] (segue "next")
    end
    U->>Repo: save_hourly()
    Repo->>DB: UPSERT hourly_forecasts
    U->>P: fetch_daily(coordinates, pages)
    P-->>U: DailyForecast[]
    U->>Repo: save_daily()
    Repo->>DB: UPSERT daily_forecasts
    opt há alert_ids e include_alerts
        U->>P: fetch_alerts(alert_ids)
        P-->>U: WeatherAlert[]
        U->>Repo: save_alerts()
        Repo->>DB: UPSERT weather_alerts
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
- As linhas do tempo são paginadas pela OpenWeather: o cliente segue o campo `next` até
  `ETL_HOURLY_PAGES` / `ETL_DAILY_PAGES` páginas (cada página é uma chamada à API) e descarta
  registros duplicados entre páginas.
- O `PeriodicRunner` captura exceções do ciclo (log com *stack trace*) e continua; `SIGTERM`/`SIGINT`
  interrompem a espera e encerram graciosamente após o ciclo corrente.

## 5.2 Tratamento de falhas na chamada à OpenWeather

<!-- mmd:sequencia-retry -->
```mermaid
sequenceDiagram
    autonumber
    participant C as OpenWeatherClient
    participant OW as OpenWeather

    C->>OW: GET /data/4.0/onecall/current
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
| 401 | `AuthenticationError` imediato (chave inválida ou sem acesso ao produto) |
| 404 | `ResourceNotFoundError` (para alertas, é ignorado com *warning*) |
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

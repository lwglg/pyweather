# 3. Modelagem de domínios e entidades

[← Índice](../../README.md) · Anterior: [2. Arquitetura](02-arquitetura.md) · Próximo: [4. Casos de uso](04-casos-de-uso.md)

## Linguagem ubíqua

| Termo | Significado |
|-------|-------------|
| **Local** (`Location`) | Cidade monitorada, identificada por coordenadas. |
| **Condições atuais** (`CurrentWeather`) | Observação do momento; o ETL acumula uma por instante, formando um **histórico**. |
| **Previsão (passos de 3 h) / resumo diário** | Passos de 3 horas fornecidos pela OpenWeather e o resumo diário derivado deles pelo ETL. |
| **Alerta** (`WeatherAlert`) | Aviso oficial emitido por uma agência para um período (modelo e tabela mantidos; **não são preenchidos** no plano gratuito). |
| **Extração** | Uma execução do ETL (`SyncReport`). |

## Domínio do ETL

<!-- mmd:dominio-classes-etl -->
```mermaid
classDiagram
    direction LR

    class Coordinates {
        <<value object>>
        +float latitude
        +float longitude
    }
    class LocationSpec {
        <<value object>>
        +str name
        +str country
        +str state
        +Coordinates coordinates
    }
    class Location {
        <<entity>>
        +int id
        +str name
        +str country
        +Coordinates coordinates
        +TimezoneInfo timezone
    }
    class CurrentWeather {
        <<entity>>
        +datetime observed_at
        +float temperature
        +Wind wind
        +Precipitation precipitation
        +WeatherCondition condition
    }
    class HourlyForecast {
        <<entity>>
        +datetime forecast_at
    }
    class DailyForecast {
        <<entity>>
        +datetime forecast_at
        +DailyTemperature temperature
        +DailyFeelsLike feels_like
    }
    class WeatherAlert {
        <<entity>>
        +str alert_id
        +str event
        +datetime starts_at
        +datetime ends_at
    }
    class CurrentSnapshot {
        <<aggregate result>>
        +CurrentWeather weather
        +TimezoneInfo timezone
    }
    class Forecast {
        <<aggregate result>>
        +tuple steps
        +tuple daily
    }

    class GeocodingProvider {
        <<port>>
        +locate(spec) Location
    }
    class WeatherProvider {
        <<port>>
        +fetch_current(coords) CurrentSnapshot
        +fetch_forecast(coords) Forecast
    }
    class WeatherRepository {
        <<port>>
        +upsert_location(location) Location
        +update_timezone(id, tz)
        +save_current(id, weather) int
        +save_hourly(id, items) int
        +save_daily(id, items) int
        +save_alerts(id, items) int
    }
    class SyncWeatherUseCase {
        <<use case>>
        +execute() SyncReport
    }
    class OpenWeatherClient {
        <<adapter>>
    }
    class SqlAlchemyWeatherRepository {
        <<adapter>>
    }

    LocationSpec --> Coordinates
    Location --> Coordinates
    CurrentSnapshot --> CurrentWeather
    Forecast --> HourlyForecast
    Forecast --> DailyForecast
    SyncWeatherUseCase --> GeocodingProvider
    SyncWeatherUseCase --> WeatherProvider
    SyncWeatherUseCase --> WeatherRepository
    OpenWeatherClient ..|> GeocodingProvider
    OpenWeatherClient ..|> WeatherProvider
    SqlAlchemyWeatherRepository ..|> WeatherRepository
```
<!-- /mmd -->

### Objetos de valor (imutáveis)

| Objeto | Campos | Invariantes |
|--------|--------|-------------|
| `Coordinates` | `latitude`, `longitude` | −90 ≤ lat ≤ 90; −180 ≤ lon ≤ 180 (`InvalidCoordinatesError`) |
| `LocationSpec` | `name`, `country`, `state?`, `coordinates?` | Se houver `coordinates`, a geocodificação é dispensada |
| `TimezoneInfo` | `name` (IANA), `offset_seconds` | — |
| `WeatherCondition` | `code`, `main`, `description`, `icon` | Primeira condição da lista `weather` |
| `Wind` | `speed`, `direction`, `gust` | m/s e graus |
| `Precipitation` | `rain`, `snow`, `probability` | mm/h; probabilidade de 0 a 1 |
| `DailyTemperature` / `DailyFeelsLike` | dia, mín., máx., noite, entardecer, manhã | — |
| `AlertDescription` | `language`, `text` | — |

### Entidades

| Entidade | Identidade | Observações |
|----------|------------|-------------|
| `Location` | `id` (atribuído na persistência); unicidade natural por coordenadas | Nome/estado/país são atualizados a cada extração |
| `CurrentWeather` | `(location, observed_at)` | Temperatura, sensação, pressão, umidade, UV, nuvens, visibilidade, vento, precipitação, condição, nascer/pôr do sol |
| `HourlyForecast` | `(location, forecast_at)` | Mesmos campos de `CurrentWeather` (exceto sol) + probabilidade de precipitação |
| `DailyForecast` | `(location, forecast_at)` | Resumo do dia civil local: mínima, máxima e média, chuva/neve acumuladas, probabilidade máxima, condição predominante. Campos por período do dia, sol e **lua** ficam nulos |
| `WeatherAlert` | `(location, alert_id)` | Vigência (`starts_at`…`ends_at`), emissor, evento, textos por idioma, etiquetas |

`CurrentSnapshot` é o resultado da consulta de condições atuais: a observação e o fuso horário.
`Forecast` agrupa os passos de 3 h (`HourlyForecast`) e o resumo diário (`DailyForecast`) obtidos
em **uma única** chamada.

### Mapeamento do plano gratuito

| Dado | Origem | Observações |
|------|--------|-------------|
| Condições atuais | `GET /data/2.5/weather` | `main.*`, `wind.*`, `clouds.all`, `rain.1h`, `sys.sunrise/sunset`. Sem UV nem ponto de orvalho (ficam nulos). |
| Fuso horário | `timezone` (segundos) | O plano gratuito não informa o nome IANA: o nome é derivado do deslocamento (ex.: `UTC-03:00`). |
| Passos de 3 h | `GET /data/2.5/forecast` | 40 passos (5 dias). `pop`, `rain.3h`, `snow.3h`. O volume de chuva de cada passo é o acumulado de **3 h** (mm), não de 1 h. A tabela `hourly_forecasts` guarda esses passos. |
| Resumo diário | derivado dos passos | Agrupado por dia **civil local** (`city.timezone`). Mínima/máxima = extremos de `temp_min`/`temp_max`; `temp_day` = média das temperaturas; chuva/neve = soma; `pop` = máximo; vento = o passo mais forte; condição = a mais frequente. O 1º e o último dia podem ser **parciais** (a janela de 5 dias não começa à meia-noite). |
| Alertas | — | Só existem na One Call API (paga). Nada é extraído; `GET /alerts` retorna lista vazia. |

### Portas

| Porta | Implementação (infraestrutura) |
|-------|--------------------------------|
| `GeocodingProvider.locate` | `OpenWeatherClient` → `GET /geo/1.0/direct` |
| `WeatherProvider.fetch_current / fetch_forecast` | `OpenWeatherClient` → `GET /data/2.5/weather` e `GET /data/2.5/forecast` |
| `WeatherRepository.*` | `SqlAlchemyWeatherRepository` (`merge`/upsert por chave) |

### Erros do domínio (`PyWeatherError`)

`InvalidCoordinatesError`, `ConfigurationError`, `WeatherProviderError` ⟵ {`AuthenticationError` (401),
`RateLimitError` (429), `ProviderUnavailableError` (5xx/rede), `ResourceNotFoundError` (404),
`LocationNotFoundError`, `PayloadError`}.

## Modelo relacional (PostgreSQL)

<!-- mmd:dominio-er -->
```mermaid
erDiagram
    LOCATIONS ||--o{ CURRENT_WEATHER : "observações"
    LOCATIONS ||--o{ HOURLY_FORECASTS : "previsões horárias"
    LOCATIONS ||--o{ DAILY_FORECASTS : "previsões diárias"
    LOCATIONS ||--o{ WEATHER_ALERTS : "alertas"

    LOCATIONS {
        int id PK
        string name
        string state
        string country
        numeric latitude "UNIQUE com longitude"
        numeric longitude
        string timezone "IANA"
        int timezone_offset "segundos"
        timestamptz created_at
        timestamptz updated_at
    }
    CURRENT_WEATHER {
        int location_id PK,FK
        timestamptz observed_at PK
        float temperature
        float feels_like
        int pressure
        int humidity
        float dew_point
        float uvi
        int clouds
        int visibility
        float wind_speed
        int wind_deg
        float wind_gust
        float rain_1h
        float snow_1h
        string condition_main
        string condition_description
        timestamptz sunrise
        timestamptz sunset
        timestamptz fetched_at
    }
    HOURLY_FORECASTS {
        int location_id PK,FK
        timestamptz forecast_at PK
        float temperature
        float feels_like
        int humidity
        float pop "probabilidade 0..1"
        float rain_1h
        string condition_main
        timestamptz fetched_at
    }
    DAILY_FORECASTS {
        int location_id PK,FK
        timestamptz forecast_at PK
        float temp_min
        float temp_max
        float temp_day
        float temp_night
        float pop
        float rain
        float moon_phase
        timestamptz sunrise
        timestamptz sunset
        timestamptz fetched_at
    }
    WEATHER_ALERTS {
        int location_id PK,FK
        string alert_id PK
        string sender_name
        string event
        timestamptz starts_at
        timestamptz ends_at
        json descriptions
        json tags
        timestamptz fetched_at
    }
```
<!-- /mmd -->

Pontos de modelagem:

- **Chaves primárias compostas naturais** `(location_id, instante)` tornam a carga idempotente e
  dispensam chaves substitutas nas séries temporais. Todas as tabelas filhas usam
  `ON DELETE CASCADE` para `locations`.
- `locations` tem restrição **única** em `(latitude, longitude)`; as coordenadas são `NUMERIC(9,6)`
  (~0,1 m) e arredondadas antes da gravação, para que a geocodificação repetida encontre o mesmo local.
- Todas as colunas de data/hora são `timestamptz` (UTC). `descriptions` e `tags` de alertas são `JSON`.
- Unidades seguem `OPENWEATHER_UNITS` (padrão `metric`: °C, m/s, hPa, mm). **O banco não guarda a
  unidade por registro**; mudar a configuração depois de acumular dados mistura unidades — nesse
  caso, use um banco novo ou converta o histórico.
- O esquema é versionado por migrações Alembic em
  `services/etl/pyweather_etl/infrastructure/persistence/migrations/versions/` (revisão `0001`).

## Domínio da API (leitura)

A API possui modelos de leitura próprios (`pyweather_api.domain.models`), propositalmente separados
das entidades do ETL: os serviços evoluem de forma independente e compartilham somente o contrato do
banco.

| Conceito | Descrição |
|----------|-----------|
| `Page[T]` | Itens + `total` + `limit` + `offset` |
| `Pagination` | `limit` (1–200, padrão 50) e `offset` |
| `TimeRange` | Intervalo `[start, end]` inclusivo e opcional |
| `LocationFilter` | `name`, `state` (trecho, sem distinção de maiúsculas), `country` (código exato) |
| `CurrentFilter` | período, temperatura mín./máx., umidade mín./máx., condição, ordem |
| `HourlyFilter` | período, temperatura mín./máx., prob. de precipitação mínima, condição, ordem |
| `DailyFilter` | período, mínima do dia ≥ X, máxima do dia ≤ Y, prob. mínima, condição, ordem |
| `AlertFilter` | evento, emissor, vigente em (`active_at`), ordem |

Regras de negócio da API (`WeatherQueryService`): o local deve existir (`LocationNotFoundError`);
o início do período não pode ser posterior ao fim e mínimos não podem exceder máximos
(`InvalidFilterError`); consultar a "condição atual" de um local ainda sem observações gera
`NoDataError`.

# 6. Referência da API RESTful

[← Índice](../../README.md) · Anterior: [5. Sequências](05-sequencias.md) · Próximo: [7. Desenvolvimento e operação](07-desenvolvimento.md)

Com o serviço no ar (`make up`), a documentação interativa — **Swagger UI**, em português — fica em
<http://localhost:8000/docs>; há também **ReDoc** em `/redoc` e o contrato em `/openapi.json`.
Nomes de campos e estruturas de dados estão em inglês; descrições, resumos e mensagens de erro, em português.

## Convenções

- Somente `GET` (a API é de consulta). Versão no caminho: `/v1`.
- **Datas** em ISO 8601, sempre em **UTC**. Em parâmetros de consulta, datas **sem fuso** são
  interpretadas como UTC (`2026-11-12T14:00:00` ≡ `2026-11-12T14:00:00Z`); `active_at` exige fuso.
- **Paginação**: `limit` (1–200, padrão 50) e `offset` (≥ 0). Toda listagem responde
  `{ "items": [...], "total": N, "limit": L, "offset": O }`.
- **Filtros de texto** (`name`, `state`, `event`, `sender`, `condition`): contêm o trecho informado, sem
  distinção de maiúsculas; `%` e `_` são literais. `country` é comparação exata do código (ex.: `BR`).
- Parâmetros **desconhecidos** são rejeitados (422), evitando filtros ignorados silenciosamente por erro de digitação.
- Unidades conforme `OPENWEATHER_UNITS` (padrão métrico: °C, m/s, hPa, mm).

## Endpoints

| Método e caminho | Descrição | Filtros (além de `limit`/`offset`) |
|------------------|-----------|-------------------------------------|
| `GET /health` | *Liveness* (não consulta o banco) | — |
| `GET /health/ready` | *Readiness* (`SELECT 1`; 503 se falhar) | — |
| `GET /v1/locations` | Lista os locais (ordem alfabética) | `name`, `state`, `country` |
| `GET /v1/locations/{location_id}` | Detalha um local | — |
| `GET /v1/locations/{location_id}/current` | Condição atual **mais recente** | — |
| `GET /v1/locations/{location_id}/current/history` | Histórico de observações | `start`, `end`, `min_temperature`, `max_temperature`, `min_humidity`, `max_humidity`, `condition`, `order` (padrão `desc`) |
| `GET /v1/locations/{location_id}/forecast/hourly` | Previsão horária | `start`, `end`, `min_temperature`, `max_temperature`, `min_pop`, `condition`, `order` (padrão `asc`) |
| `GET /v1/locations/{location_id}/forecast/daily` | Previsão diária | `start`, `end`, `min_temperature` (sobre a **mínima** do dia), `max_temperature` (sobre a **máxima** do dia), `min_pop`, `condition`, `order` (padrão `asc`) |
| `GET /v1/locations/{location_id}/alerts` | Alertas meteorológicos | `event`, `sender`, `active_at`, `order` (padrão `desc`) |

Faixas validadas: `min_humidity`/`max_humidity` ∈ [0, 100]; `min_pop` ∈ [0, 1]; `location_id` ≥ 1.

## Exemplos

```bash
# Locais do Brasil
curl "http://localhost:8000/v1/locations?country=BR&limit=1"

# Condição atual
curl "http://localhost:8000/v1/locations/1/current"

# Próximas horas com chance de chuva ≥ 50 %
curl "http://localhost:8000/v1/locations/1/forecast/hourly?min_pop=0.5&limit=24"

# Dias frios (máxima ≤ 20 °C) na semana
curl "http://localhost:8000/v1/locations/1/forecast/daily?max_temperature=20&start=2026-11-12T00:00:00Z"

# Alertas vigentes agora
curl "http://localhost:8000/v1/locations/1/alerts?active_at=2026-11-12T15:00:00Z"
```

`GET /v1/locations?country=BR&limit=1`

```json
{
  "items": [
    {
      "id": 2,
      "name": "Curitiba",
      "state": "Paraná",
      "country": "BR",
      "latitude": -25.4284,
      "longitude": -49.2733,
      "timezone": null,
      "timezone_offset": null
    }
  ],
  "total": 2,
  "limit": 1,
  "offset": 0
}
```

`GET /v1/locations/1/current`

```json
{
  "location_id": 1,
  "observed_at": "2026-11-12T16:00:00Z",
  "temperature": 28.0,
  "feels_like": 29.0,
  "pressure": 1015,
  "humidity": 90,
  "dew_point": null,
  "uvi": null,
  "clouds": null,
  "visibility": null,
  "wind_speed": 3.0,
  "wind_deg": null,
  "wind_gust": null,
  "rain_1h": null,
  "snow_1h": null,
  "condition": { "code": 500, "main": "Rain", "description": "chuva leve", "icon": "10d" },
  "sunrise": "2026-11-12T12:00:00Z",
  "sunset": null,
  "fetched_at": "2026-11-12T12:00:00Z"
}
```

> Os exemplos acima foram gerados pela própria aplicação com dados de teste; seus valores reais
> dependem do que o ETL extraiu. Campos que a OpenWeather não informa ficam `null`.

## Erros

| Status | Quando | Corpo |
|--------|--------|-------|
| 404 | Local inexistente; ou local sem observações em `/current` | `{"detail": "Local 99 não encontrado."}` |
| 422 | Parâmetro inválido/desconhecido (formato do FastAPI) ou filtro inconsistente | `{"detail": "O início do período não pode ser posterior ao fim."}` |
| 503 | `/health/ready` com o banco indisponível | `{"detail": "Banco de dados indisponível."}` |

Erros de validação de formato (tipo, faixa, parâmetro desconhecido) usam o corpo padrão do FastAPI
(`detail` como lista de objetos com `loc`, `msg`, `type`).

## Configuração (variáveis de ambiente da API)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_HOST` / `PORT` / `DB` / `USER` / `PASSWORD` | `localhost` / `5432` / `pyweather` / `pyweather` / `pyweather` | Conexão com o PostgreSQL |
| `DATABASE_URL` | — | URL SQLAlchemy completa; tem precedência sobre `POSTGRES_*` |
| `API_TITLE` | `pyweather API` | Título exibido no Swagger |
| `API_ROOT_PATH` | *(vazio)* | Prefixo quando atrás de *proxy* reverso (ex.: `/pyweather`) |
| `CORS_ORIGINS` | *(vazio)* | Origens permitidas, separadas por vírgula; vazio desativa o CORS |
| `LOG_LEVEL` | `INFO` | Nível de log |

> **Segurança.** A API **não implementa autenticação**: publique-a atrás de um *gateway* ou *proxy*
> que a forneça, caso seja exposta fora de uma rede confiável.

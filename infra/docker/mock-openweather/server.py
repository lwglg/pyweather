"""Mock determinístico da OpenWeather (plano gratuito) para os smoke tests.

Somente biblioteca padrão. Serve fixtures **relativas ao instante atual** e **valores
determinísticos**, nos formatos reais das APIs gratuitas:

* ``/geo/1.0/direct``: Florianópolis;
* ``/data/2.5/weather``: 24,5 °C, 70 % de umidade, chuva leve, fuso UTC-3;
* ``/data/2.5/forecast``: 40 passos de 3 h a partir do próximo múltiplo de 3 h (UTC);
  ``pop`` = (índice do passo % 10) / 10, ou seja, 20 dos 40 passos têm pop ≥ 0,5;
* exige ``appid`` igual a ``MOCK_API_KEY`` (padrão ``smoke-test-key``), como a API real.

Não há alertas nem previsão diária: esses recursos não existem no plano gratuito.
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


API_KEY = os.environ.get("MOCK_API_KEY", "smoke-test-key")
PORT = int(os.environ.get("MOCK_PORT", "8080"))

LAT, LON = -27.5954, -48.548
TZ_OFFSET = -10800
STEP_COUNT = 40
HOUR = 3600
STEP = 3 * HOUR
DAY = 86400


def _weather(code: int, main: str, description: str, icon: str) -> list[dict[str, Any]]:
    return [{"id": code, "main": main, "description": description, "icon": icon}]


def current_payload(now: int) -> dict[str, Any]:
    midnight = now - now % DAY
    return {
        "coord": {"lon": LON, "lat": LAT},
        "weather": _weather(500, "Rain", "chuva leve", "10d"),
        "main": {
            "temp": 24.5,
            "feels_like": 25.1,
            "temp_min": 23.0,
            "temp_max": 26.0,
            "pressure": 1018,
            "humidity": 70,
        },
        "visibility": 10000,
        "wind": {"speed": 4.2, "deg": 120, "gust": 7.1},
        "rain": {"1h": 0.4},
        "clouds": {"all": 40},
        "dt": now,
        "sys": {"country": "BR", "sunrise": midnight + 8 * HOUR, "sunset": midnight + 21 * HOUR},
        "timezone": TZ_OFFSET,
        "name": "Florianópolis",
        "cod": 200,
    }


def forecast_step(dt: int, index: int) -> dict[str, Any]:
    slot = index % 10
    temp = 20.0 + slot
    return {
        "dt": dt,
        "main": {
            "temp": temp,
            "feels_like": temp + 0.5,
            "temp_min": temp - 0.5,
            "temp_max": temp + 0.5,
            "pressure": 1015,
            "humidity": 60 + slot,
        },
        "weather": _weather(803, "Clouds", "nublado", "04d"),
        "clouds": {"all": 50},
        "wind": {"speed": 3.5, "deg": 100, "gust": 6.0},
        "visibility": 10000,
        "pop": slot / 10,
        "rain": {"3h": 0.5},
    }


def forecast_payload(now: int) -> dict[str, Any]:
    first = now - now % STEP + STEP
    steps = [forecast_step(first + i * STEP, i) for i in range(STEP_COUNT)]
    return {
        "cod": "200",
        "cnt": STEP_COUNT,
        "list": steps,
        "city": {"name": "Florianópolis", "country": "BR", "timezone": TZ_OFFSET},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "MockOpenWeather/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Nunca registra a query string: ela contém a chave (appid).
        path = urlparse(self.path).path
        print(
            f"{self.address_string()} {self.command} {path} -> {args[1] if len(args) > 1 else ''}",
            flush=True,
        )

    def _send(self, status: int, body: Any) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        path = url.path

        if path == "/health":
            self._send(200, {"status": "ok"})
            return
        if query.get("appid") != API_KEY:
            self._send(401, {"cod": 401, "message": "Invalid API key."})
            return

        now = int(time.time())
        if path == "/geo/1.0/direct":
            found = "florian" in query.get("q", "").lower()
            body = (
                [
                    {
                        "name": "Florianópolis",
                        "lat": LAT,
                        "lon": LON,
                        "country": "BR",
                        "state": "Santa Catarina",
                    }
                ]
                if found
                else []
            )
            self._send(200, body)
        elif path == "/data/2.5/weather":
            self._send(200, current_payload(now))
        elif path == "/data/2.5/forecast":
            self._send(200, forecast_payload(now))
        else:
            self._send(404, {"cod": 404, "message": "Not found."})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock da OpenWeather em :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

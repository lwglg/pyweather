"""Mock determinístico da OpenWeather (Geocoding + One Call 4.0) para os smoke tests.

Somente biblioteca padrão. Serve fixtures **relativas ao instante atual** (assim, a vigência do
alerta e o "agora" sempre fazem sentido) e **valores determinísticos**:

* condições atuais: 24,5 °C, 70 % de umidade, chuva leve, com um alerta ativo;
* linha do tempo horária: 20 registros por página, com ``next`` apontando para o próprio mock
  (exercita a paginação e a proteção de host do ETL); ``pop`` = (hora UTC % 10) / 10;
* linha do tempo diária: 8 dias, mínima 15+i e máxima 25+i;
* exige ``appid`` igual a ``MOCK_API_KEY`` (padrão ``smoke-test-key``), como a API real.
"""

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


API_KEY = os.environ.get("MOCK_API_KEY", "smoke-test-key")
PORT = int(os.environ.get("MOCK_PORT", "8080"))

LAT, LON = -27.5954, -48.548
TZ = {"timezone": "America/Sao_Paulo", "timezone_offset": -10800}
ALERT_ID = "MOCK-ALERT-1"
HOURLY_PAGE_SIZE = 20
DAILY_DAYS = 8
HOUR = 3600
DAY = 86400


def _weather(code: int, main: str, description: str, icon: str) -> list[dict[str, Any]]:
    return [{"id": code, "main": main, "description": description, "icon": icon}]


def current_payload(now: int) -> dict[str, Any]:
    midnight = now - now % DAY
    return {
        "lat": LAT,
        "lon": LON,
        **TZ,
        "data": [
            {
                "dt": now,
                "sunrise": midnight + 8 * HOUR,
                "sunset": midnight + 21 * HOUR,
                "temp": 24.5,
                "feels_like": 25.1,
                "pressure": 1018,
                "humidity": 70,
                "dew_point": 18.2,
                "uvi": 5.5,
                "clouds": 40,
                "visibility": 10000,
                "wind_speed": 4.2,
                "wind_deg": 120,
                "wind_gust": 7.1,
                "rain": {"1h": 0.4},
                "weather": _weather(500, "Rain", "chuva leve", "10d"),
                "alerts": [ALERT_ID],
            }
        ],
    }


def hourly_record(dt: int) -> dict[str, Any]:
    step = (dt // HOUR) % 10
    return {
        "dt": dt,
        "temp": 20.0 + step,
        "feels_like": 20.5 + step,
        "pressure": 1015,
        "humidity": 60 + step,
        "dew_point": 17.0,
        "uvi": 3.0,
        "clouds": 50,
        "visibility": 10000,
        "wind_speed": 3.5,
        "wind_deg": 100,
        "pop": step / 10,
        "weather": _weather(803, "Clouds", "nublado", "04d"),
    }


def hourly_payload(start: int, next_url: str) -> dict[str, Any]:
    records = [hourly_record(start + i * HOUR) for i in range(HOURLY_PAGE_SIZE)]
    return {"lat": LAT, "lon": LON, **TZ, "data": records, "next": next_url}


def daily_payload(now: int) -> dict[str, Any]:
    midnight = now - now % DAY
    records = []
    for i in range(DAILY_DAYS):
        dt = midnight + i * DAY
        records.append(
            {
                "dt": dt,
                "sunrise": dt + 8 * HOUR,
                "sunset": dt + 21 * HOUR,
                "moonrise": dt + 19 * HOUR,
                "moonset": dt + 7 * HOUR,
                "moon_phase": 0.43,
                "temp": {
                    "day": 24.0 + i,
                    "min": 15.0 + i,
                    "max": 25.0 + i,
                    "night": 17.0 + i,
                    "eve": 22.0 + i,
                    "morn": 16.0 + i,
                },
                "feels_like": {
                    "day": 25.0 + i,
                    "night": 17.5 + i,
                    "eve": 22.5 + i,
                    "morn": 16.5 + i,
                },
                "pressure": 1016,
                "humidity": 65,
                "dew_point": 17.5,
                "wind_speed": 5.0,
                "wind_deg": 90,
                "weather": _weather(800, "Clear", "céu limpo", "01d"),
                "clouds": 5,
                "pop": (i % 4) / 4,
                "uvi": 9.0,
                "rain": {"1h": 1.5} if i % 2 == 0 else None,
            }
        )
    return {"lat": LAT, "lon": LON, **TZ, "data": records}


def alert_payload(now: int) -> dict[str, Any]:
    return {
        "id": ALERT_ID,
        "sender_name": "Defesa Civil (mock)",
        "event": "Tempestade",
        "start": now - HOUR,
        "end": now + 23 * HOUR,
        "description": [
            {"language": "pt-BR", "description": "Chuvas intensas e rajadas de vento."},
            {"language": "en-GB", "description": "Heavy rain and wind gusts."},
        ],
        "tags": ["Thunderstorm", "Rain"],
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
        elif path == "/data/4.0/onecall/current":
            self._send(200, current_payload(now))
        elif path == "/data/4.0/onecall/timeline/1h":
            first = now - now % HOUR
            start = int(query.get("start", first))
            host = self.headers.get("Host", f"localhost:{PORT}")
            next_url = (
                f"http://{host}{path}?lat={LAT}&lon={LON}&start={start + HOURLY_PAGE_SIZE * HOUR}"
            )
            self._send(200, hourly_payload(start, next_url))
        elif path == "/data/4.0/onecall/timeline/1day":
            self._send(200, daily_payload(now))
        elif re.fullmatch(r"/data/4\.0/onecall/alert/[\w.:-]+", path):
            if path.rsplit("/", 1)[1] == ALERT_ID:
                self._send(200, alert_payload(now))
            else:
                self._send(404, {"cod": 404, "message": "Alert not found."})
        else:
            self._send(404, {"cod": 404, "message": "Not found."})


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock da OpenWeather em :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

"""Esquema inicial: locais, condições atuais, previsões horárias/diárias e alertas.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def _condition_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("condition_code", sa.Integer()),
        sa.Column("condition_main", sa.String(32)),
        sa.Column("condition_description", sa.String(128)),
        sa.Column("condition_icon", sa.String(8)),
    ]


def _wind_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("wind_speed", sa.Float()),
        sa.Column("wind_deg", sa.Integer()),
        sa.Column("wind_gust", sa.Float()),
    ]


def _hourly_like_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("feels_like", sa.Float(), nullable=False),
        sa.Column("pressure", sa.Integer(), nullable=False),
        sa.Column("humidity", sa.Integer(), nullable=False),
        sa.Column("dew_point", sa.Float()),
        sa.Column("uvi", sa.Float()),
        sa.Column("clouds", sa.Integer()),
        sa.Column("visibility", sa.Integer()),
        sa.Column("rain_1h", sa.Float()),
        sa.Column("snow_1h", sa.Float()),
    ]


def _location_fk() -> sa.Column[object]:
    return sa.Column(
        "location_id",
        sa.Integer(),
        sa.ForeignKey("locations.id", ondelete="CASCADE"),
        primary_key=True,
    )


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120)),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6, asdecimal=False), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6, asdecimal=False), nullable=False),
        sa.Column("timezone", sa.String(64)),
        sa.Column("timezone_offset", sa.Integer()),
        sa.Column("created_at", _TS, nullable=False),
        sa.Column("updated_at", _TS, nullable=False),
        sa.UniqueConstraint("latitude", "longitude", name="uq_locations_coordinates"),
    )

    op.create_table(
        "current_weather",
        _location_fk(),
        sa.Column("observed_at", _TS, primary_key=True),
        *_hourly_like_columns(),
        *_wind_columns(),
        *_condition_columns(),
        sa.Column("sunrise", _TS),
        sa.Column("sunset", _TS),
        sa.Column("fetched_at", _TS, nullable=False),
    )

    op.create_table(
        "hourly_forecasts",
        _location_fk(),
        sa.Column("forecast_at", _TS, primary_key=True),
        *_hourly_like_columns(),
        *_wind_columns(),
        *_condition_columns(),
        sa.Column("pop", sa.Float()),
        sa.Column("fetched_at", _TS, nullable=False),
    )

    op.create_table(
        "daily_forecasts",
        _location_fk(),
        sa.Column("forecast_at", _TS, primary_key=True),
        sa.Column("temp_day", sa.Float()),
        sa.Column("temp_min", sa.Float()),
        sa.Column("temp_max", sa.Float()),
        sa.Column("temp_night", sa.Float()),
        sa.Column("temp_eve", sa.Float()),
        sa.Column("temp_morn", sa.Float()),
        sa.Column("feels_like_day", sa.Float()),
        sa.Column("feels_like_night", sa.Float()),
        sa.Column("feels_like_eve", sa.Float()),
        sa.Column("feels_like_morn", sa.Float()),
        sa.Column("pressure", sa.Integer()),
        sa.Column("humidity", sa.Integer()),
        sa.Column("dew_point", sa.Float()),
        sa.Column("uvi", sa.Float()),
        sa.Column("clouds", sa.Integer()),
        *_wind_columns(),
        sa.Column("rain", sa.Float()),
        sa.Column("snow", sa.Float()),
        sa.Column("pop", sa.Float()),
        *_condition_columns(),
        sa.Column("sunrise", _TS),
        sa.Column("sunset", _TS),
        sa.Column("moonrise", _TS),
        sa.Column("moonset", _TS),
        sa.Column("moon_phase", sa.Float()),
        sa.Column("fetched_at", _TS, nullable=False),
    )

    op.create_table(
        "weather_alerts",
        _location_fk(),
        sa.Column("alert_id", sa.String(255), primary_key=True),
        sa.Column("sender_name", sa.String(255), nullable=False),
        sa.Column("event", sa.String(255), nullable=False),
        sa.Column("starts_at", _TS, nullable=False),
        sa.Column("ends_at", _TS, nullable=False),
        sa.Column("descriptions", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("fetched_at", _TS, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("weather_alerts")
    op.drop_table("daily_forecasts")
    op.drop_table("hourly_forecasts")
    op.drop_table("current_weather")
    op.drop_table("locations")

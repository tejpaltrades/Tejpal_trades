"""Load configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"

# Always load from project folder (works even if you run python from another directory)
load_dotenv(ENV_FILE)

TIMEFRAME_MAP = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    login: int
    password: str
    server: str
    symbol: str
    timeframe: str
    lot_size: float
    magic_number: int
    atr_multiplier: float
    atr_period: int
    ema_fast: int
    ema_slow: int
    poll_seconds: float
    dry_run: bool
    mt5_terminal_path: str | None
    restart_delay_seconds: float
    heartbeat_seconds: float

    @property
    def mt5_timeframe(self) -> int:
        key = self.timeframe.upper()
        if key not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported TIMEFRAME '{self.timeframe}'. Use one of {list(TIMEFRAME_MAP)}")
        return TIMEFRAME_MAP[key]


def load_settings() -> Settings:
    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if not login or not password or not server:
        example = PROJECT_DIR / ".env.example"
        if not ENV_FILE.exists():
            hint = (
                f"No .env file found at:\n  {ENV_FILE}\n\n"
                f"Create it by copying the example:\n"
                f'  copy "{example}" "{ENV_FILE}"\n'
                f"Then edit .env with your MT5 login, password, and server.\n"
                f"(Do not put secrets only in .env.example — the bot reads .env only.)"
            )
        else:
            hint = (
                f".env exists at {ENV_FILE} but MT5_LOGIN, MT5_PASSWORD, or "
                f"MT5_SERVER is missing/empty. Use this format (no quotes needed):\n"
                f"  MT5_LOGIN=12345678\n"
                f"  MT5_PASSWORD=your_password\n"
                f"  MT5_SERVER=XMGlobal-MT5 2"
            )
        raise ValueError(hint)

    return Settings(
        login=int(login),
        password=password,
        server=server,
        symbol=os.getenv("SYMBOL", "XAUUSD"),
        timeframe=os.getenv("TIMEFRAME", "M5"),
        lot_size=float(os.getenv("LOT_SIZE", "0.01")),
        magic_number=int(os.getenv("MAGIC_NUMBER", "20240523")),
        atr_multiplier=float(os.getenv("ATR_MULTIPLIER", "1.5")),
        atr_period=int(os.getenv("ATR_PERIOD", "14")),
        ema_fast=int(os.getenv("EMA_FAST", "9")),
        ema_slow=int(os.getenv("EMA_SLOW", "21")),
        poll_seconds=float(os.getenv("POLL_SECONDS", "2")),
        dry_run=_bool(os.getenv("DRY_RUN"), default=False),
        mt5_terminal_path=os.getenv("MT5_TERMINAL_PATH") or None,
        restart_delay_seconds=float(os.getenv("RESTART_DELAY_SECONDS", "30")),
        heartbeat_seconds=float(os.getenv("HEARTBEAT_SECONDS", "60")),
    )

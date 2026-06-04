"""MetaTrader 5 connection and order helpers for XM."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import MetaTrader5 as mt5
import pandas as pd

from config import Settings

logger = logging.getLogger(__name__)


class MT5Client:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.symbol = settings.symbol
        self._connected = False

    def connect(self) -> None:
        init_kwargs: dict[str, str] = {}
        if self.settings.mt5_terminal_path:
            init_kwargs["path"] = self.settings.mt5_terminal_path

        if not mt5.initialize(**init_kwargs):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        authorized = mt5.login(
            self.settings.login,
            password=self.settings.password,
            server=self.settings.server,
        )
        if not authorized:
            err = mt5.last_error()
            mt5.shutdown()
            raise RuntimeError(f"MT5 login failed: {err}")

        info = mt5.account_info()
        if info is None:
            raise RuntimeError("Could not read account info after login")

        self.symbol = self._resolve_symbol(self.settings.symbol)
        if not mt5.symbol_select(self.symbol, True):
            raise RuntimeError(f"Could not select symbol {self.symbol}")

        self._connected = True
        logger.info(
            "Connected: account=%s server=%s symbol=%s",
            info.login,
            info.server,
            self.symbol,
        )

    def shutdown(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False

    def _resolve_symbol(self, preferred: str) -> str:
        """XM may suffix gold as XAUUSD, XAUUSD#, GOLD, etc."""
        candidates = [
            preferred,
            "XAUUSD",
            "GOLD",
            "XAUUSD#",
            "XAUUSDm",
            "GOLD#",
        ]
        for name in dict.fromkeys(candidates):
            info = mt5.symbol_info(name)
            if info is not None:
                return name
        visible = [s.name for s in (mt5.symbols_get() or []) if "XAU" in s.name or "GOLD" in s.name.upper()]
        raise RuntimeError(
            f"Gold symbol not found. Tried {candidates}. "
            f"Visible gold-like symbols: {visible[:20]}"
        )

    def fetch_bars(self, count: int = 500) -> pd.DataFrame:
        rates = mt5.copy_rates_from_pos(
            self.symbol,
            self.settings.mt5_timeframe,
            0,
            count,
        )
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No rates for {self.symbol}: {mt5.last_error()}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.set_index("time").sort_index()
        df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close"})
        return df

    def fetch_m5_rsi(self, period: int = 14) -> float | None:
        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 0, period + 50)
        if rates is None or len(rates) < period + 2:
            return None
        close = pd.Series([r["close"] for r in rates])
        from strategy.indicators import rsi as calc_rsi

        return float(calc_rsi(close, period).iloc[-2])

    def symbol_point(self) -> float:
        info = mt5.symbol_info(self.symbol)
        if info is None:
            raise RuntimeError("symbol_info failed")
        return info.point

    def normalize_price(self, price: float) -> float:
        info = mt5.symbol_info(self.symbol)
        if info is None:
            return price
        digits = info.digits
        return round(price, digits)

    def current_tick(self) -> tuple[float, float]:
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError("No tick data")
        return tick.bid, tick.ask

    def positions_for_bot(self) -> list[Any]:
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == self.settings.magic_number]

    def open_market(
        self,
        side: int,
        volume: float,
        sl: float,
        comment: str = "BrahMos",
    ) -> int | None:
        if self.settings.dry_run:
            logger.info("[DRY RUN] Would open side=%s vol=%s sl=%s", side, volume, sl)
            return -1

        tick = mt5.symbol_info_tick(self.symbol)
        info = mt5.symbol_info(self.symbol)
        if tick is None or info is None:
            logger.error("Tick/symbol info unavailable")
            return None

        if side > 0:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid

        sl = self.normalize_price(sl)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": 0.0,
            "deviation": 30,
            "magic": self.settings.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(info),
        }
        result = mt5.order_send(request)
        if result is None:
            logger.error("order_send returned None: %s", mt5.last_error())
            return None
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Open failed retcode=%s comment=%s", result.retcode, result.comment)
            return None
        logger.info("Opened ticket=%s price=%s sl=%s", result.order, price, sl)
        return result.order

    def modify_sl(self, ticket: int, new_sl: float) -> bool:
        pos_list = mt5.positions_get(ticket=ticket)
        if not pos_list:
            logger.warning("Position %s not found for SL modify", ticket)
            return False
        pos = pos_list[0]
        new_sl = self.normalize_price(new_sl)

        if self.settings.dry_run:
            logger.info("[DRY RUN] Would modify ticket=%s sl=%s", ticket, new_sl)
            return True

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": pos.tp,
            "magic": self.settings.magic_number,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                "Modify SL failed ticket=%s retcode=%s %s",
                ticket,
                getattr(result, "retcode", None),
                getattr(result, "comment", mt5.last_error()),
            )
            return False
        logger.info("SL updated ticket=%s -> %s", ticket, new_sl)
        return True

    def close_position(self, ticket: int) -> bool:
        pos_list = mt5.positions_get(ticket=ticket)
        if not pos_list:
            return True
        pos = pos_list[0]

        if self.settings.dry_run:
            logger.info("[DRY RUN] Would close ticket=%s", ticket)
            return True

        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return False

        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "price": price,
            "deviation": 30,
            "magic": self.settings.magic_number,
            "comment": "BrahMos TP5 exit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(mt5.symbol_info(pos.symbol)),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Close failed ticket=%s", ticket)
            return False
        logger.info("Closed ticket=%s at %s", ticket, price)
        return True

    @staticmethod
    def _filling_mode(symbol_info: Any) -> int:
        filling = symbol_info.filling_mode
        if filling & mt5.SYMBOL_FILLING_IOC:
            return mt5.ORDER_FILLING_IOC
        if filling & mt5.SYMBOL_FILLING_FOK:
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

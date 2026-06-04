"""
BrahMos / Dr Atul Rawal V.02 — signal engine ported from Pine Script.

Entry: EMA 9/21 crossover with alternating signal state (no repeat buys in a row).
SL/TP: ATR(14) * multiplier from entry; five take-profit levels at 1R–5R.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import pandas as pd

from strategy.indicators import adx, atr, ema, macd, rsi, session_vwap


class Side(IntEnum):
    FLAT = 0
    LONG = 1
    SHORT = -1


@dataclass(frozen=True)
class TradeLevels:
    side: Side
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    tp5: float
    risk: float
    atr: float


@dataclass(frozen=True)
class Signal:
    side: Side
    levels: TradeLevels
    bar_time: pd.Timestamp


class StrategyEngine:
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
    ) -> None:
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self._last_signal_state = Side.FLAT

    def reset_state(self) -> None:
        self._last_signal_state = Side.FLAT

    def set_last_signal_state(self, state: Side) -> None:
        self._last_signal_state = state

    @property
    def last_signal_state(self) -> Side:
        return self._last_signal_state

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add indicator columns used by the Pine dashboard (optional for logging)."""
        out = df.copy()
        out["ema9"] = ema(out["close"], self.ema_fast)
        out["ema21"] = ema(out["close"], self.ema_slow)
        out["atr"] = atr(out["high"], out["low"], out["close"], self.atr_period)
        out["rsi"] = rsi(out["close"], 14)
        m, s = macd(out["close"])
        out["macd"] = m
        out["macd_signal"] = s
        out["adx"] = adx(out["high"], out["low"], out["close"], 14)
        vol = out.get("tick_volume", out.get("real_volume", pd.Series(0, index=out.index)))
        out["vwap"] = session_vwap(out["high"], out["low"], out["close"], vol)
        return out

    def evaluate_on_closed_bar(self, df: pd.DataFrame) -> Signal | None:
        """
        Evaluate using the last *closed* candle (index -2 vs -3 for crossover).
        df must be OHLCV with datetime index, oldest first.
        """
        if len(df) < max(self.ema_slow, self.atr_period) + 3:
            return None

        data = self.enrich(df)
        prev = data.iloc[-3]
        curr = data.iloc[-2]  # last fully closed bar

        ema9_prev, ema21_prev = prev["ema9"], prev["ema21"]
        ema9_curr, ema21_curr = curr["ema9"], curr["ema21"]

        buy_cross = ema9_prev <= ema21_prev and ema9_curr > ema21_curr
        sell_cross = ema9_prev >= ema21_prev and ema9_curr < ema21_curr

        trigger_buy = buy_cross and self._last_signal_state <= Side.FLAT
        trigger_sell = sell_cross and self._last_signal_state >= Side.FLAT

        if not trigger_buy and not trigger_sell:
            return None

        side = Side.LONG if trigger_buy else Side.SHORT
        entry = float(curr["close"])
        risk = float(curr["atr"]) * self.atr_multiplier

        if risk <= 0:
            return None

        if side == Side.LONG:
            sl = entry - risk
            tp1, tp2, tp3, tp4, tp5 = (
                entry + risk,
                entry + 2 * risk,
                entry + 3 * risk,
                entry + 4 * risk,
                entry + 5 * risk,
            )
        else:
            sl = entry + risk
            tp1, tp2, tp3, tp4, tp5 = (
                entry - risk,
                entry - 2 * risk,
                entry - 3 * risk,
                entry - 4 * risk,
                entry - 5 * risk,
            )

        self._last_signal_state = side
        levels = TradeLevels(
            side=side,
            entry=entry,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            tp4=tp4,
            tp5=tp5,
            risk=risk,
            atr=float(curr["atr"]),
        )
        return Signal(side=side, levels=levels, bar_time=curr.name)

    @staticmethod
    def levels_from_fill(side: Side, fill_price: float, risk: float) -> TradeLevels:
        """Rebuild SL/TP ladder from actual fill price (keeps same R distance)."""
        entry = fill_price
        if side == Side.LONG:
            sl = entry - risk
            tp1, tp2, tp3, tp4, tp5 = (
                entry + risk,
                entry + 2 * risk,
                entry + 3 * risk,
                entry + 4 * risk,
                entry + 5 * risk,
            )
        else:
            sl = entry + risk
            tp1, tp2, tp3, tp4, tp5 = (
                entry - risk,
                entry - 2 * risk,
                entry - 3 * risk,
                entry - 4 * risk,
                entry - 5 * risk,
            )
        return TradeLevels(
            side=side,
            entry=entry,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            tp4=tp4,
            tp5=tp5,
            risk=risk,
            atr=0.0,
        )

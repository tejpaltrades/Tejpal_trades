"""
Manage open trade: detect TP hits and trail stop loss per Pine rules.

TP1 hit  -> SL to breakeven (entry)
TP2 hit  -> SL to TP1
TP3 hit  -> SL to TP2
TP4 hit  -> SL to TP3
TP5 hit  -> close full position
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from broker.mt5_client import MT5Client
from strategy.brahmos_strategy import Side, TradeLevels

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "trade_state.json"


@dataclass
class ActiveTrade:
    ticket: int
    side: int
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    tp5: float
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    tp4_hit: bool = False
    tp5_hit: bool = False

    @classmethod
    def from_levels(cls, ticket: int, levels: TradeLevels) -> ActiveTrade:
        return cls(
            ticket=ticket,
            side=int(levels.side),
            entry=levels.entry,
            sl=levels.sl,
            tp1=levels.tp1,
            tp2=levels.tp2,
            tp3=levels.tp3,
            tp4=levels.tp4,
            tp5=levels.tp5,
        )


class PositionManager:
    def __init__(self, client: MT5Client) -> None:
        self.client = client
        self.active: ActiveTrade | None = None
        self._load_state()

    def _load_state(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            self.active = ActiveTrade(**raw)
            logger.info("Restored trade state for ticket=%s", self.active.ticket)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Could not load trade state: %s", exc)
            self.active = None

    def _save_state(self) -> None:
        if self.active is None:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
            return
        STATE_FILE.write_text(json.dumps(asdict(self.active), indent=2), encoding="utf-8")

    def has_open_trade(self) -> bool:
        if self.active is None:
            return False
        positions = self.client.positions_for_bot()
        tickets = {p.ticket for p in positions}
        if self.active.ticket not in tickets:
            self.active = None
            self._save_state()
            return False
        return True

    def register_new_trade(self, ticket: int, levels: TradeLevels) -> None:
        self.active = ActiveTrade.from_levels(ticket, levels)
        self._save_state()

    def sync_with_broker(self) -> None:
        """If bot restarted, attach to existing position by magic number."""
        if self.active is not None:
            return
        positions = self.client.positions_for_bot()
        if len(positions) == 1:
            logger.warning(
                "Found open position %s without local state; manage manually or delete trade_state.json",
                positions[0].ticket,
            )

    def on_tick(self, bid: float, ask: float) -> None:
        if self.active is None:
            return

        trade = self.active
        is_long = trade.side == Side.LONG

        # For longs use bid for TP/SL checks (conservative); for shorts use ask.
        price_high = ask if is_long else bid
        price_low = bid if is_long else ask

        def hit_tp(level: float) -> bool:
            return price_high >= level if is_long else price_low <= level

        changed = False

        if not trade.tp1_hit and hit_tp(trade.tp1):
            trade.tp1_hit = True
            self._trail_to(trade.entry, "TP1 -> breakeven SL")
            changed = True

        if not trade.tp2_hit and hit_tp(trade.tp2):
            trade.tp2_hit = True
            self._trail_to(trade.tp1, "TP2 -> SL at TP1")
            changed = True

        if not trade.tp3_hit and hit_tp(trade.tp3):
            trade.tp3_hit = True
            self._trail_to(trade.tp2, "TP3 -> SL at TP2")
            changed = True

        if not trade.tp4_hit and hit_tp(trade.tp4):
            trade.tp4_hit = True
            self._trail_to(trade.tp3, "TP4 -> SL at TP3")
            changed = True

        if not trade.tp5_hit and hit_tp(trade.tp5):
            trade.tp5_hit = True
            logger.info("TP5 hit — closing position")
            self.client.close_position(trade.ticket)
            self.active = None
            changed = True

        if changed:
            self._save_state()

    def _trail_to(self, new_sl: float, reason: str) -> None:
        if self.active is None:
            return
        trade = self.active
        new_sl = self.client.normalize_price(new_sl)

        # Only move SL in favorable direction
        if trade.side == Side.LONG and new_sl <= trade.sl:
            return
        if trade.side == Side.SHORT and new_sl >= trade.sl:
            return

        if self.client.modify_sl(trade.ticket, new_sl):
            logger.info("%s: ticket=%s sl %s -> %s", reason, trade.ticket, trade.sl, new_sl)
            trade.sl = new_sl

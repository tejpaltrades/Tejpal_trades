"""
BrahMos Gold Bot — XM / MetaTrader 5

Runs the EMA crossover strategy from Pine Script and manages trailing stops:
  TP1 -> breakeven | TP2 -> SL@TP1 | ... | TP5 -> full exit

Cloud/VPS: auto-reconnects on errors; logs to logs/bot.log; writes logs/heartbeat.txt
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

from config import PROJECT_DIR, load_settings
from broker.mt5_client import MT5Client
from logging_config import setup_logging
from strategy.brahmos_strategy import Side, StrategyEngine
from trade.position_manager import PositionManager

logger = logging.getLogger("brahmos_bot")


def _last_closed_bar_time(df) -> datetime:
    return df.index[-2].to_pydatetime()


def _resolve_position_ticket(client: MT5Client) -> int | None:
    positions = client.positions_for_bot()
    if not positions:
        return None
    return positions[0].ticket


def _write_heartbeat(log_dir: Path) -> None:
    path = log_dir / "heartbeat.txt"
    path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def run_trading_loop(settings) -> None:
    strategy = StrategyEngine(
        ema_fast=settings.ema_fast,
        ema_slow=settings.ema_slow,
        atr_period=settings.atr_period,
        atr_multiplier=settings.atr_multiplier,
    )
    client = MT5Client(settings)
    positions = PositionManager(client)
    log_dir = PROJECT_DIR / "logs"
    last_heartbeat = 0.0

    try:
        client.connect()
        positions.sync_with_broker()

        if positions.has_open_trade() and positions.active:
            strategy.set_last_signal_state(Side(positions.active.side))
            logger.info(
                "Resumed with open %s ticket=%s",
                positions.active.side,
                positions.active.ticket,
            )

        last_processed_bar: datetime | None = None
        logger.info(
            "Bot started | %s %s | lot=%s | dry_run=%s",
            client.symbol,
            settings.timeframe,
            settings.lot_size,
            settings.dry_run,
        )

        while True:
            now = time.monotonic()
            if now - last_heartbeat >= settings.heartbeat_seconds:
                _write_heartbeat(log_dir)
                last_heartbeat = now

            bid, ask = client.current_tick()
            positions.on_tick(bid, ask)

            df = client.fetch_bars(count=500)
            closed_time = _last_closed_bar_time(df)

            if last_processed_bar is None:
                last_processed_bar = closed_time
                time.sleep(settings.poll_seconds)
                continue

            if closed_time <= last_processed_bar:
                time.sleep(settings.poll_seconds)
                continue

            last_processed_bar = closed_time
            logger.info("New closed bar: %s", closed_time)

            if positions.has_open_trade():
                time.sleep(settings.poll_seconds)
                continue

            signal = strategy.evaluate_on_closed_bar(df)
            if signal is None:
                time.sleep(settings.poll_seconds)
                continue

            lv = signal.levels
            logger.info(
                "SIGNAL %s @ %s | entry=%.2f sl=%.2f tp1=%.2f ... tp5=%.2f (ATR=%.2f)",
                signal.side.name,
                signal.bar_time,
                lv.entry,
                lv.sl,
                lv.tp1,
                lv.tp5,
                lv.atr,
            )

            ticket = client.open_market(
                side=int(signal.side),
                volume=settings.lot_size,
                sl=lv.sl,
            )
            if ticket is None:
                time.sleep(settings.poll_seconds)
                continue

            pos_ticket = _resolve_position_ticket(client)
            if pos_ticket is None and settings.dry_run:
                pos_ticket = ticket

            if pos_ticket is not None:
                pos = mt5.positions_get(ticket=pos_ticket)
                if pos:
                    fill = float(pos[0].price_open)
                    lv = StrategyEngine.levels_from_fill(signal.side, fill, lv.risk)
                    client.modify_sl(pos_ticket, lv.sl)
                positions.register_new_trade(pos_ticket, lv)
            else:
                logger.error("Order sent but no position found — check MT5 terminal")

            time.sleep(settings.poll_seconds)

    finally:
        client.shutdown()


def main() -> None:
    settings = load_settings()
    setup_logging()

    logger.info("BrahMos bot | project=%s", PROJECT_DIR)

    while True:
        try:
            run_trading_loop(settings)
            return
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            return
        except Exception:
            logger.exception(
                "Bot error — restarting in %s seconds",
                settings.restart_delay_seconds,
            )
            time.sleep(settings.restart_delay_seconds)


if __name__ == "__main__":
    main()

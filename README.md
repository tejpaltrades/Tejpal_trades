# BrahMos Gold Trading Bot (XM + MT5)

Python bot that replicates your **Dr Atul Rawal V.02** Pine Script signals on **gold (XAUUSD)** via **MetaTrader 5** (XM account).

## Strategy (matches Pine)

| Rule | Behavior |
|------|----------|
| **Buy** | EMA 9 crosses above EMA 21, and last signal was not already long |
| **Sell** | EMA 9 crosses below EMA 21, and last signal was not already short |
| **Stop loss** | Entry ± (ATR(14) × 1.5) |
| **Take profits** | TP1–TP5 at 1R, 2R, 3R, 4R, 5R (R = ATR × multiplier) |

Signals are evaluated on the **last closed candle** only (reduces repainting vs tick-by-tick).

## Trailing stop (your rules)

| Event | Action |
|-------|--------|
| Price hits **TP1** | Move SL to **breakeven** (entry) |
| Price hits **TP2** | Move SL to **TP1** |
| Price hits **TP3** | Move SL to **TP2** |
| Price hits **TP4** | Move SL to **TP3** |
| Price hits **TP5** | **Close** the full position |

The bot does **not** place five separate broker TP orders. It holds one position and updates SL (or closes at TP5), same idea as your Pine labels.

## Requirements

1. **Windows PC** (MetaTrader5 Python package is Windows-only).
2. **XM MT5** terminal installed and logged in.
3. **Algo trading** enabled in MT5: *Tools → Options → Expert Advisors → Allow algorithmic trading*.
4. Python 3.10+.

## Setup

```powershell
cd d:\Tejpal_trades
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` — from XM (e.g. `XMGlobal-MT5 2`; use exact name from MT5 login window).
- `SYMBOL` — often `XAUUSD` or `GOLD` on XM (bot auto-tries common names).
- `TIMEFRAME` — default **M5** (5-minute); must match your TradingView chart.
- `LOT_SIZE` — start small (e.g. `0.01`) on demo first.
- `DRY_RUN=true` — logs actions without sending orders (good for first test).

## Run

1. Open **XM MT5** and stay logged in.
2. In terminal:

```powershell
.\.venv\Scripts\activate
python bot.py
```

Logs print signals, SL moves, and TP5 exits. On VPS, logs also go to `logs/bot.log`.

## Cloud / 24-7 deployment

**MT5 requires Windows.** Deploy on a **Windows VPS** (AWS, Azure, Contabo, forex VPS), not Linux Lambda/Docker.

See **[DEPLOY.md](DEPLOY.md)** for full steps. Quick version:

```powershell
.\deploy\setup_vps.ps1      # once
.\deploy\start_bot.ps1        # test
.\deploy\install_task.ps1     # auto-start on boot (Admin)
```

## Project layout

```
d:\Tejpal_trades\
  bot.py                 # Main loop
  config.py              # .env settings
  strategy/
    brahmos_strategy.py  # EMA cross + ATR levels
    indicators.py        # EMA, ATR, RSI, MACD, VWAP, ADX
  broker/
    mt5_client.py        # MT5 login, orders, modify SL
  trade/
    position_manager.py  # TP hit detection + trailing SL
  trade_state.json       # Created at runtime (survives restart)
```

## Important notes

- **Demo first**: Run on an XM demo account until behavior matches your chart.
- **Symbol name**: XM variants differ; if connect fails, set `SYMBOL` to the exact name in *Market Watch*.
- **Timeframe**: Pine and MT5 must use the **same** timeframe for signals to align.
- **VWAP / scores**: Dashboard scores in Pine are for display; **entries use only EMA cross + signal state**, as in your script.
- **Risk**: Live trading can lose money. This is not financial advice.
- **Restart**: `trade_state.json` stores TP flags and levels; delete it if you close the trade manually in MT5.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `MT5 initialize failed` | Start MT5 before `python bot.py` |
| `login failed` | Check server string exactly as in MT5 |
| `Invalid volume` | Use min lot from symbol spec |
| Orders not sent | Enable algo trading; check Experts tab in MT5 |
| Signals differ from TV | Same symbol, timeframe, and use **closed bar** in TV for comparison |

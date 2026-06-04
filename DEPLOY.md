# Deploy BrahMos Bot on Cloud (24/7)

This bot **cannot run on Linux cloud** (AWS Lambda, Render, Heroku, etc.) because **MetaTrader 5 only works on Windows** with the MT5 terminal installed.

Use a **Windows VPS** that runs 24/7.

---

## Recommended cloud options

| Provider | Notes |
|----------|--------|
| **AWS EC2** | Windows Server instance (e.g. `t3.small`) |
| **Azure VM** | Windows Server |
| **Contabo / Vultr** | Cheaper Windows VPS |
| **Forex VPS** | Optimized for MT5 (low latency to broker) |

Pick a region **close to XM servers** (often **London** or **Europe**) for lower delay.

---

## Easiest path: Git clone on VPS (one script)

After MT5 is installed on the VPS, you do **not** need to copy files by hand. Push this project to GitHub (private repo recommended), then on the VPS run **one command**:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
cd C:\
# Download deploy_from_git.ps1 once, or clone the repo first:
git clone https://github.com/YOU/Tejpal_trades.git C:\Tejpal_trades
cd C:\Tejpal_trades
.\deploy\deploy_from_git.ps1 -RepoUrl "https://github.com/YOU/Tejpal_trades.git" -AutoStart
```

The script will:

1. `git clone` or `git pull` into `C:\Tejpal_trades`
2. Create Python venv and install `requirements.txt`
3. Create `.env` from `.env.example` if missing
4. With `-AutoStart`: register the 24/7 Windows task and start the bot

**You still type MT5 password once** in `C:\Tejpal_trades\.env` on the VPS (never commit `.env` to Git).

**Updates later** (same VPS):

```powershell
cd C:\Tejpal_trades
.\deploy\deploy_from_git.ps1 -RepoUrl "https://github.com/YOU/Tejpal_trades.git"
```

Then restart: `Stop-ScheduledTask -TaskName BrahMosGoldBot; Start-ScheduledTask -TaskName BrahMosGoldBot`

---

## Step-by-step deployment

### 1. Create Windows VPS

- OS: **Windows Server 2019/2022** or **Windows 10/11**
- RAM: **2 GB minimum** (4 GB recommended)
- Enable **RDP** so you can connect remotely

### 2. Connect via Remote Desktop (RDP)

From your PC: `Win + R` → `mstsc` → enter VPS IP and login.

### 3. Install software on VPS

1. **Python 3.11+** — https://www.python.org/downloads/ (check **Add to PATH**)
2. **XM MetaTrader 5** — download from XM, install, login to your account
3. In MT5:
   - *Tools → Options → Expert Advisors* → enable **Allow algorithmic trading**
   - *File → Login to trade account* — save password if you want auto-login after reboot
   - Add **GOLD** / **XAUUSD** to Market Watch

### 4. Copy bot project to VPS

Copy the whole `Tejpal_trades` folder to the VPS, e.g.:

```
C:\Tejpal_trades\
```

Options: USB, zip upload, Git clone, or RDP copy-paste.

### 5. One-time setup (PowerShell as Administrator)

```powershell
cd C:\Tejpal_trades
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\setup_vps.ps1
```

Edit `C:\Tejpal_trades\.env` with your MT5 credentials:

```env
MT5_LOGIN=your_number
MT5_PASSWORD=your_password
MT5_SERVER=XMGlobal-MT5 7
SYMBOL=GOLD
TIMEFRAME=M5
LOT_SIZE=0.01
DRY_RUN=false

# If MT5 is not in default folder:
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
```

### 6. Test manually first

```powershell
cd C:\Tejpal_trades
.\deploy\start_bot.ps1
```

Check:

- `logs\bot.log` — activity log
- `logs\heartbeat.txt` — updated every 60s (proves bot is alive)
- MT5 *Experts* tab — no connection errors

Press `Ctrl+C` to stop after confirming it works.

### 7. Install auto-start (runs 24/7 after reboot)

```powershell
cd C:\Tejpal_trades
Set-ExecutionPolicy -Scope Process Bypass
.\deploy\install_task.ps1
```

This creates Windows task **BrahMosGoldBot** that:

- Starts when VPS boots
- Restarts the bot if it crashes (every 1 minute)

Start immediately without reboot:

```powershell
Start-ScheduledTask -TaskName BrahMosGoldBot
```

---

## Monitoring on cloud

| File | Purpose |
|------|---------|
| `logs\bot.log` | All signals, orders, errors (rotates at 5 MB) |
| `logs\heartbeat.txt` | Last alive timestamp (UTC) |

If `heartbeat.txt` is older than 2–3 minutes, the bot may be down — RDP in and check MT5 + task.

**Useful commands:**

```powershell
Get-ScheduledTask -TaskName BrahMosGoldBot
Get-Content C:\Tejpal_trades\logs\bot.log -Tail 50
Get-Content C:\Tejpal_trades\logs\heartbeat.txt
Stop-ScheduledTask -TaskName BrahMosGoldBot
Start-ScheduledTask -TaskName BrahMosGoldBot
```

---

## Important VPS notes

1. **MT5 must stay running** — `start_bot.ps1` launches MT5 automatically if closed.
2. **Do not log out of RDP in a way that kills apps** — on VPS, disconnect RDP normally (X button); avoid "Sign out".
3. **Windows Update** may reboot the VPS — scheduled task will restart the bot after reboot.
4. **Demo first** — test on demo account on VPS before live money.
5. **Security** — use strong RDP password; only open RDP to your IP if possible; never commit `.env` to Git.

---

## Why not AWS Lambda / Docker Linux?

The `MetaTrader5` Python library talks to the **Windows MT5 terminal**. There is no official headless MT5 for Linux. Standard cloud containers cannot run this bot without a Windows VM.

---

## Quick checklist

- [ ] Windows VPS created
- [ ] XM MT5 installed and logged in
- [ ] Algo trading enabled in MT5
- [ ] Project copied to `C:\Tejpal_trades`
- [ ] `.env` configured
- [ ] `setup_vps.ps1` completed
- [ ] Manual test with `start_bot.ps1` OK
- [ ] `install_task.ps1` installed
- [ ] `heartbeat.txt` updating every minute

# Scripts

Utility scripts organized by purpose. All scripts use prefixes to indicate their domain:
- `forex_` - Forex trading scripts (Phase 1: USD/SGD)
- `crypto_` - Crypto/Solana scripts (original project)

---

## Forex Scripts (Phase 1 - USD/SGD)

| File | Description |
|------|-------------|
| `forex_download_history.py` | Download historical forex data from Yahoo Finance |
| `forex_run_backtest.py` | Run backtest simulation with USD/SGD data |
| `forex_test_oanda.py` | Test OANDA API connection |
| `forex_fetch_live_price.py` | Fetch live USD/SGD price from OANDA |

### Download Historical Data

```bash
python scripts/forex_download_history.py --pair USD_SGD --period 2y
```

### Run Backtest

```bash
python scripts/forex_run_backtest.py --capital 1000
```

### Test OANDA Connection

Set up your `.env` file first, then:

```bash
python scripts/forex_test_oanda.py
```

### Fetch Live Price

```bash
python scripts/forex_fetch_live_price.py
python scripts/forex_fetch_live_price.py --pair EUR_USD
```

---

## Crypto Scripts (Original Solana Bot)

| File | Description |
|------|-------------|
| `crypto_sync_roadmap.py` | Syncs roadmap.md status to GitHub issues |

### Roadmap Sync

Syncs `roadmap.md` status emojis with GitHub issue states.

**Dry run (preview changes):**
```bash
python scripts/crypto_sync_roadmap.py --dry-run
```

**Apply changes:**
```bash
python scripts/crypto_sync_roadmap.py
```

### Status Mapping

| Emoji | Status | GitHub Action |
|-------|--------|---------------|
| 📝 | Todo | Issue stays open |
| 🚧 | In Progress | Issue stays open |
| ✅ | Done | Issue gets closed |
| ⏸️ | Blocked | Issue stays open, adds label |

---

## GitHub Project Automation

Project fields (Epic, Priority, Story Points, Sprint) are automatically synced via GitHub Actions:

- **Auto-sync**: `.github/workflows/sync-issue-to-project.yml` - triggers on issue edits
- **Manual sync**: `.github/workflows/sync-all-issues.yml` - bulk update all issues

### Running Manual Sync

Go to **Actions** → **Sync All Issues to Project (Manual)** → **Run workflow**

Or via CLI:
```bash
gh workflow run sync-all-issues.yml
```

---

## Quick Reference

```bash
# Forex workflow
python scripts/forex_download_history.py --pair USD_SGD --period 2y
python scripts/forex_run_backtest.py --capital 1000
python scripts/forex_test_oanda.py
python scripts/forex_fetch_live_price.py

# Crypto workflow  
python scripts/crypto_sync_roadmap.py --dry-run
```

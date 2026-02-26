# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### `uv: command not found`

**Problem:** uv not in PATH

**Solution:**
```bash
# macOS/Linux
export PATH="$HOME/.cargo/bin:$PATH"

# Windows (PowerShell)
$env:PATH += ";$HOME\.cargo\bin"

# Or restart terminal
```

#### `ModuleNotFoundError: No module named 'snail_scalp'`

**Problem:** Package not installed correctly

**Solution:**
```bash
# Reinstall
uv sync --reinstall

# Or install in editable mode
uv pip install -e .
```

#### `ImportError: cannot import name 'X'`

**Problem:** Version mismatch or partial install

**Solution:**
```bash
# Clean and reinstall
rm -rf .venv
uv sync
```

---

## Runtime Issues

### Simulation Issues

#### "No trades executed"

**Problem:** Strategy conditions not met

**Diagnostic:**
```bash
# Check if data exists
ls -la data/*.csv

# Generate test data with guaranteed volatility
uv run python -m snail_scalp.generate_data --scenario volatile
```

**Solutions:**
1. Use more volatile data: `--scenario volatile`
2. Extend time period: `--days 14`
3. Try different token: `--token bonk`
4. Lower entry threshold in config.py:
   ```python
   rsi_oversold_max = 40  # Was 35
   ```

#### "Simulation data exhausted"

**Problem:** Not enough data points

**Solution:**
```bash
# Generate more data
uv run python -m snail_scalp.generate_data --days 7
```

#### "Outside trading window"

**Problem:** Data timestamps not in 9-11 UTC

**Solution:**
```bash
# Check data timestamps
head -20 data/sample_price_data.csv

# Generate fresh data with correct times
uv run python -m snail_scalp.generate_data
```

---

### Real Data Issues

#### "Failed to fetch: HTTP 429"

**Problem:** Rate limited by CoinGecko

**Solutions:**
1. Wait 1-2 minutes
2. Use Birdeye API (higher limits)
3. Cache data and reuse:
   ```bash
   # Save fetched data
   cp data/real_sol_7d.csv data/real_sol_7d_backup.csv
   ```

#### "No data received"

**Problem:** Invalid token or no trading activity

**Diagnostic:**
```bash
# Check if token exists on CoinGecko
curl "https://api.coingecko.com/api/v3/coins/solana"
```

**Solutions:**
1. Use correct token ID (not symbol)
2. Try major tokens: `solana`, `bonk`, `dogwifcoin`
3. Check token has trading volume

---

### Performance Issues

#### Simulation running very slow

**Problem:** Speed multiplier not set

**Solution:**
```bash
# Increase speed
uv run python -m snail_scalp --simulate --speed 50
```

#### High memory usage

**Problem:** Too much data loaded

**Solutions:**
1. Reduce data points:
   ```bash
   uv run python -m snail_scalp.generate_data --days 3 --interval 5
   ```
2. Clear state files:
   ```bash
   uv run python -m snail_scalp --reset
   ```

---

## Data Issues

### CSV Format Errors

#### "KeyError: 'price'"

**Problem:** CSV has wrong column names

**Solution:**
```bash
# Check CSV headers
head -1 data/your_file.csv

# Should be:
# timestamp,datetime,price,volume24h,liquidity
```

#### "ValueError: could not convert string to float"

**Problem:** Non-numeric data in CSV

**Diagnostic:**
```python
import pandas as pd
df = pd.read_csv("data/your_file.csv")
print(df.dtypes)  # Check types
print(df.isnull().sum())  # Check nulls
```

---

## Trading Logic Issues

### Entry Signal Not Triggering

**Diagnostic Script:**
```python
from snail_scalp import TechnicalIndicators

indicators = TechnicalIndicators()

# Add your price data
prices = [100, 101, 102, 101, 100, 99, 98, 97, 96, 95,
          94, 93, 92, 91, 90, 89, 88, 87, 86, 85]  # Downtrend

for p in prices:
    indicators.add_price(p)

# Check indicators
stats = indicators.get_stats()
print(f"RSI: {stats['rsi']:.1f}")
print(f"BB Width: {stats['bb_width']:.2f}%")
print(f"BB Lower: {stats['bb_lower']:.2f}")

# Test signal
price = 85
is_signal = indicators.is_entry_signal(price)
print(f"Signal at {price}: {is_signal}")
```

**Common Causes:**
1. RSI not in range (need 25-35)
2. BB width < 2%
3. Price not at lower BB
4. Not enough data points (need 20+)

### Position Not Closing

**Diagnostic:**
```python
# Check exit levels
from snail_scalp.indicators import TechnicalIndicators

indicators = TechnicalIndicators()
# ... add prices ...

levels = indicators.get_exit_levels(entry_price=100)
print(f"TP1: {levels.tp1:.2f}")  # Should be +2.5%
print(f"TP2: {levels.tp2:.2f}")  # Should be +4%
print(f"Stop: {levels.stop:.2f}")  # Should be -1.5%
```

---

## Configuration Issues

### Changes Not Applying

**Problem:** Config cached or wrong file

**Solution:**
```bash
# Reset state
uv run python -m snail_scalp --reset

# Verify config location
cat src/snail_scalp/config.py | grep "rsi_oversold"
```

### Strategy Too Aggressive/Conservative

**Adjust Parameters:**
```python
# src/snail_scalp/config.py

# More aggressive (more trades, higher risk)
rsi_oversold_max = 40  # Easier entry
tp1_percent = 2.0      # Faster profit
tp2_percent = 3.5
stop_loss_percent = 2.0

# More conservative (fewer trades, lower risk)
rsi_oversold_max = 30  # Harder entry
tp1_percent = 3.0      # Higher targets
tp2_percent = 5.0
stop_loss_percent = 1.0
```

---

## Platform-Specific Issues

### Windows

#### UnicodeEncodeError

**Problem:** Emoji in output

**Solution:** Already fixed in latest version. If persists:
```bash
# Set console encoding
chcp 65001
```

#### Path Issues

**Problem:** Backslashes in paths

**Solution:** Use forward slashes or raw strings:
```python
log_file = "data/sample_price_data.csv"  # Good
log_file = r"data\sample_price_data.csv"  # Also good
```

### macOS/Linux

#### Permission Denied

**Solution:**
```bash
chmod +x -R .
```

#### SSL Certificate Errors

**Solution:**
```bash
# Update certificates
brew install ca-certificates  # macOS
sudo apt-get install ca-certificates  # Ubuntu
```

---

## Debug Mode

### Enable Detailed Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run your code
```

### Check State Files

```bash
# View portfolio state
cat data/simulation_portfolio.json | python -m json.tool

# View trade history
cat data/simulation_trades.json | python -m json.tool
```

---

## Getting Help

### Before Asking

1. Check this troubleshooting guide
2. Search existing issues on GitHub
3. Enable debug logging and check output
4. Try with default configuration

### Information to Provide

When reporting issues:
- Error message (full traceback)
- Command you ran
- OS and Python version
- Contents of relevant config files
- State files (if applicable)

### Debug Output Template

```bash
# Run with debug info
uv run python -m snail_scalp --simulate --speed 10 2>&1 | tee debug.log

# Share debug.log
```

---

## Emergency Procedures

### Stop Everything

```bash
# Find and kill process
ps aux | grep snail_scalp
kill -9 <PID>

# Or reset all state
uv run python -m snail_scalp --reset
```

### Recover From Bad State

```bash
# Backup and reset
mv data/portfolio_state.json data/portfolio_state.json.backup
uv run python -m snail_scalp --reset
```

### Live Trading Emergency

If bot misbehaving in live mode:
1. Ctrl+C to stop
2. Check open positions on Jupiter
3. Close positions manually if needed
4. Review logs
5. Fix issue before restarting

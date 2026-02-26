# Using Real Data for Simulations

This guide explains how to fetch and use real historical price data from Solana DEXs for backtesting and simulations.

## Data Source Options

### 1. Birdeye API (Recommended)

**Pros:**
- Free tier: 100k credits/month
- Historical OHLCV data
- 1m, 5m, 15m, 1h, 4h, 1d timeframes
- Fast and reliable

**Cons:**
- Requires API key for higher limits
- Rate limited on free tier

**Setup:**
1. Sign up at https://birdeye.so
2. Get API key from dashboard
3. Use in code:

```python
from snail_scalp.real_data_fetcher import RealDataSimulation

sim = RealDataSimulation(
    token_address="ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz",  # FARTCOIN
    capital=20.0,
    days=7,
    api_key="your_birdeye_api_key_here"
)

await sim.run_simulation()
```

### 2. DexScreener (Free)

**Pros:**
- No API key needed
- Free forever
- Good for current data

**Cons:**
- No historical OHLCV
- Limited to recent trades

**Usage:**
```python
from snail_scalp.real_data_fetcher import DexScreenerFetcher

fetcher = DexScreenerFetcher()
pair_data = await fetcher.get_pair_data("8sLbNZoY3HWP8krpPjWBP1u3ZcD7nRRd6m8vPWH6Y5Pq")
```

### 3. Helius RPC

**Pros:**
- Direct Solana access
- Full historical data
- Fast queries

**Cons:**
- Requires paid plan for history
- More complex setup

**Setup:**
1. Sign up at https://helius.xyz
2. Get RPC endpoint
3. Use in config.py

### 4. Jupiter API

**Pros:**
- Best for live trading
- Real-time quotes
- Free

**Cons:**
- No historical data
- Rate limited

## Quick Start: Real Data Simulation

### Step 1: Get Birdeye API Key

```bash
# 1. Visit https://birdeye.so
# 2. Sign up for free account
# 3. Go to API section
# 4. Copy your API key
```

### Step 2: Fetch and Simulate

```python
import asyncio
from snail_scalp.real_data_fetcher import RealDataSimulation

async def run_real_sim():
    # FARTCOIN address
    token = "ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz"
    
    sim = RealDataSimulation(
        token_address=token,
        capital=20.0,
        days=7,  # Last 7 days
        api_key="your_api_key_here"
    )
    
    # Fetch and run
    await sim.run_simulation()

asyncio.run(run_real_sim())
```

### Step 3: Run via Command Line

```bash
# Set API key as environment variable
$env:BIRDEYE_API_KEY="your_key_here"

# Run simulation
uv run python -c "
import asyncio
from snail_scalp.real_data_fetcher import RealDataSimulation

async def main():
    sim = RealDataSimulation(
        token_address='ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz',
        capital=20.0,
        days=7,
        api_key='$env:BIRDEYE_API_KEY'
    )
    await sim.run_simulation()

asyncio.run(main())
"
```

## Popular Solana Token Addresses

| Token | Address | Use Case |
|-------|---------|----------|
| SOL | `So11111111111111111111111111111111111111112` | Native token |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` | Stablecoin |
| BONK | `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` | Meme coin |
| WIF | `EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm` | Meme coin |
| FARTCOIN | `ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz` | AI meme |
| PENGU | `2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd3gnGpo2jP` | NFT meme |

Find more at:
- https://birdeye.so/tokens
- https://dexscreener.com/solana

## Alternative: Download Historical Data

### Option 1: CoinGecko API

```python
import requests
import pandas as pd

# Get historical data
token_id = "solana"  # CoinGecko ID
url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
params = {
    "vs_currency": "usd",
    "days": "30",
    "interval": "hourly"
}

response = requests.get(url, params=params)
data = response.json()

# Convert to DataFrame
prices = data["prices"]
df = pd.DataFrame(prices, columns=["timestamp", "price"])
df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

# Save as CSV for simulation
df.to_csv("data/sol_30d.csv", index=False)
```

### Option 2: CSV Format for Bot

The bot expects this CSV format:
```csv
timestamp,datetime,price,volume24h,liquidity
1705312800,2024-01-15T10:00:00,145.23,150000000,25000000
1705313100,2024-01-15T10:05:00,146.10,152000000,25500000
```

Create from any data source:
```python
import csv
from datetime import datetime

# Your historical data
historical_prices = [...]  # From any API

with open("data/my_token_history.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f, 
        fieldnames=["timestamp", "datetime", "price", "volume24h", "liquidity"]
    )
    writer.writeheader()
    
    for price_data in historical_prices:
        writer.writerow({
            "timestamp": price_data["time"],
            "datetime": datetime.fromtimestamp(price_data["time"]).isoformat(),
            "price": price_data["close"],
            "volume24h": price_data["volume"],
            "liquidity": price_data.get("liquidity", 0),
        })
```

## Running Simulation with Real Data

### Method 1: Direct Simulation

```python
import asyncio
from snail_scalp import HybridDataFeed, TechnicalIndicators, RiskManager, Trader
from snail_scalp.config import strategy_config

async def simulate_with_real_data():
    # Use your fetched data file
    feed = HybridDataFeed(
        simulate=True,
        log_file="data/real_fartcoin_7d.csv",  # Your real data
        speed_multiplier=50
    )
    
    indicators = TechnicalIndicators()
    risk = RiskManager(simulate=True)
    
    trader = Trader(
        strategy_config={
            "rsi_oversold_min": 25,
            "rsi_oversold_max": 35,
            "tp1_percent": 2.5,
            "tp2_percent": 4.0,
            "stop_loss_percent": 1.5,
        },
        risk_manager=risk,
        simulate=True
    )
    
    capital = 20.0
    
    while True:
        price_data = await feed.get_price_data(None, "")
        if not price_data:
            break
        
        current_price = price_data.price
        indicators.add_price(current_price, price_data.volume24h)
        
        if len(indicators.prices) >= strategy_config.bb_period:
            if not trader.active_position:
                if indicators.is_entry_signal(current_price):
                    await trader.check_entry(current_price, indicators, capital)
            else:
                await trader.manage_position(current_price, indicators)
    
    # Results
    summary = trader.get_summary()
    print(f"\nPnL: ${summary['total_pnl']:+.2f}")
    print(f"Return: {(summary['total_pnl']/capital*100):+.2f}%")

asyncio.run(simulate_with_real_data())
```

### Method 2: Multi-Token with Real Data

```python
from snail_scalp import MultiTokenFeed, PortfolioManager
from snail_scalp.token_screener import RiskLevel

# Screen tokens
feed = MultiTokenFeed()
candidates = feed.get_best_scalping_candidates(n=3)

# For each candidate, fetch real data and simulate
portfolio = PortfolioManager(initial_capital=20.0, simulate=True)

for token in candidates:
    # Fetch real data for this token
    # ... (use BirdeyeFetcher)
    
    # Simulate trades
    # ... (run simulation loop)
    pass
```

## Data Quality Checklist

Before running simulation:

- [ ] Data covers at least 3+ days
- [ ] 5-minute or 1-minute intervals
- [ ] Includes trading hours (9-11 UTC)
- [ ] Price range is realistic
- [ ] Volume data is present
- [ ] No missing data points

## Troubleshooting

### Issue: "No data fetched"
**Solution:** Check API key and token address

### Issue: "Rate limited"
**Solution:** Add delays between requests or upgrade API plan

### Issue: "Empty CSV file"
**Solution:** Verify token has trading activity

### Issue: "Simulation shows no trades"
**Solution:** Check if data includes trading window (9-11 UTC)

## Best Practices

1. **Test Multiple Time Periods**
   - Bull market data
   - Bear market data
   - Sideways market

2. **Use Sufficient Data**
   - Minimum 7 days for reliable results
   - 30 days recommended
   - Include volatile periods

3. **Validate Data Quality**
   - Check for gaps
   - Verify price ranges
   - Compare with chart

4. **Save Fetched Data**
   - Reuse for multiple backtests
   - Avoid API rate limits
   - Track data versions

## Free Data Sources Summary

| Source | Historical | API Key | Rate Limit |
|--------|-----------|---------|------------|
| Birdeye (free) | Yes | Optional | 100k/mo |
| DexScreener | No | No | 300/min |
| CoinGecko | Yes | No | 10-30/min |
| Solana FM | Limited | No | 100/min |

## Example: Complete Workflow

```bash
# 1. Fetch real data
uv run python -c "
from snail_scalp.real_data_fetcher import BirdeyeDataFetcher
import asyncio

async def fetch():
    fetcher = BirdeyeDataFetcher(api_key='your_key')
    data = await fetcher.get_token_price_history(
        'ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz',
        timeframe='5m',
        days=7
    )
    print(f'Fetched {len(data)} candles')

asyncio.run(fetch())
"

# 2. Run simulation
uv run python -m snail_scalp --simulate \
  --log data/real_fartcoin_7d.csv \
  --capital 20 \
  --speed 50

# 3. Check results
cat data/simulation_results.json
```

## Next Steps

1. Get Birdeye API key
2. Fetch data for your target tokens
3. Run backtests on historical data
4. Validate strategy performance
5. Go live with confidence

---

*Remember: Real data gives accurate backtests, but past performance doesn't guarantee future results. Always start with small capital.*

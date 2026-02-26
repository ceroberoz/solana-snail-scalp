# Using Real Market Data

## Quick Start

```bash
# Simulate with real SOL data
uv run python -m snail_scalp --real-data --capital 20

# Different token
uv run python -m snail_scalp --real-data --token bonk --days 14

# More capital, longer period
uv run python -m snail_scalp --real-data --days 30 --capital 100
```

## Available Data Sources

### CoinGecko (Free, Default)

```bash
uv run python -m snail_scalp --real-data --token solana --days 7
```

**Available Tokens:**
- `solana` - SOL/USD
- `bonk` - BONK/USD
- `dogwifcoin` - WIF/USD

**Limitations:**
- Hourly data points
- Rate limited: 10-30 calls/minute
- Limited to 1-2 years history

### Birdeye API (Recommended)

Get free API key at [birdeye.so](https://birdeye.so)

```python
from snail_scalp.real_data_fetcher import RealDataSimulation

sim = RealDataSimulation(
    token_address="ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz",
    capital=20.0,
    days=7,
    api_key="your_api_key_here"
)

await sim.run_simulation()
```

**Benefits:**
- OHLCV data
- 1m, 5m, 15m, 1h timeframes
- 100k credits/month free

### DexScreener (Free)

```python
from snail_scalp.real_data_fetcher import DexScreenerFetcher

fetcher = DexScreenerFetcher()
pairs = await fetcher.get_token_pairs("So11111111111111111111111111111111111111112")
```

**Note:** Current data only, no historical OHLCV.

## Token Addresses

Popular Solana token addresses for reference:

| Token | Address |
|-------|---------|
| SOL | `So11111111111111111111111111111111111111112` |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| BONK | `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` |
| WIF | `EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm` |
| FARTCOIN | `ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz` |
| PENGU | `2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd3gnGpo2jP` |

## Expected Output

```
======================================================================
REAL DATA SIMULATION MODE
======================================================================
Token: SOLANA
Days: 7
Capital: $20.00
======================================================================

[FETCH] Getting 7 days of solana data from CoinGecko...
[OK] Downloaded 168 price points

[MARKET DATA]
  Price Range: $76.56 - $89.98
  Current: $87.60
  Change: +7.39%

======================================================================
SIMULATION RESULTS (REAL DATA)
======================================================================
Initial Capital:    $20.00
Total PnL:          $+0.45
Return:             +2.25%
Total Trades:       3
Win Rate:           66.7%
======================================================================
```

## Why No Trades?

If simulation shows 0 trades, common reasons:

1. **Strong Uptrend**: Price never touched lower BB
2. **Low Volatility**: BB width < 2%
3. **Wrong Timeframe**: Data outside 9-11 UTC window
4. **Extreme Move**: RSI never reached 25-35 zone

**This is normal!** The bot waits for confirmed setups.

## Custom Data Format

To use your own data, create CSV:

```csv
timestamp,datetime,price,volume24h,liquidity
1705312800,2024-01-15T10:00:00,145.23,150000000,25000000
1705313100,2024-01-15T10:05:00,146.10,152000000,25500000
```

Then run:
```bash
uv run python -m snail_scalp --simulate --log data/my_data.csv
```

## Data Sources Comparison

| Source | Historical | API Key | Rate Limit | Best For |
|--------|-----------|---------|------------|----------|
| CoinGecko | ✅ 7+ days | ❌ Free | 10-30/min | Quick testing |
| Birdeye | ✅ OHLCV | ⚠️ Optional | 100k/mo | Production |
| DexScreener | ❌ Current | ❌ Free | 300/min | Live prices |
| Helius | ✅ Full | ✅ Required | Varies | Professional |

## Troubleshooting

### "No data received"
- Check token symbol/address
- Verify API key if using Birdeye
- Wait and retry (rate limit)

### "Simulation shows 0 trades"
- Try longer time period (14+ days)
- Try more volatile token (BONK, WIF)
- Check if data includes trading window hours

### "Rate limited"
- Add delay between requests
- Upgrade API plan
- Use cached data

## Advanced: Fetch Custom Data

```python
import aiohttp
import csv
import asyncio
from datetime import datetime

async def fetch_custom():
    url = "https://api.example.com/solana/price"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            
            # Save to CSV format
            with open("data/custom.csv", "w", newline="") as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=["timestamp", "price", "volume24h"]
                )
                writer.writeheader()
                for point in data:
                    writer.writerow(point)

asyncio.run(fetch_custom())
```

## Best Practices

1. **Test Multiple Periods**
   - Bull markets
   - Bear markets
   - Sideways

2. **Minimum Data**
   - 7 days absolute minimum
   - 30 days recommended
   - Include volatile periods

3. **Cache Fetched Data**
   ```python
   # Save for reuse
   data_file = f"data/real_{token}_{days}d.csv"
   ```

4. **Validate Data**
   - Check price ranges
   - Verify volume
   - Look for gaps

## Next Steps

After testing with real data:
1. Review backtest results
2. Adjust strategy parameters if needed
3. Start with small live capital
4. Monitor performance

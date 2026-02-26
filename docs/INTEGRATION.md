# Integration Guide

## Programmatic Usage

Use the bot components in your own scripts.

### Basic Trading Loop

```python
import asyncio
from snail_scalp import (
    HybridDataFeed,
    TechnicalIndicators,
    RiskManager,
    Trader
)

async def custom_trading():
    # Initialize
    feed = HybridDataFeed(simulate=True, log_file="data/price.csv")
    indicators = TechnicalIndicators()
    risk = RiskManager()
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
    
    # Trading loop
    while True:
        price_data = await feed.get_price_data(None, "")
        if not price_data:
            break
        
        indicators.add_price(price_data.price, price_data.volume24h)
        
        if not trader.active_position:
            if indicators.is_entry_signal(price_data.price):
                await trader.check_entry(price_data.price, indicators, capital)
        else:
            await trader.manage_position(price_data.price, indicators)

asyncio.run(custom_trading())
```

### Token Screening

```python
from snail_scalp import MultiTokenFeed

feed = MultiTokenFeed()

# Get top candidates
candidates = feed.get_best_scalping_candidates(n=5)

for token in candidates:
    print(f"{token.metrics.symbol}: Hype={token.hype.total_hype_score:.1f}")
    print(f"  Price: ${token.metrics.price_usd}")
    print(f"  24h: {token.metrics.change_24h:+.1f}%")
```

### Portfolio Management

```python
from snail_scalp import PortfolioManager
from snail_scalp.token_screener import RiskLevel

portfolio = PortfolioManager(
    initial_capital=20.0,
    max_positions=3,
    simulate=True
)

# Open position
portfolio.open_position(
    symbol="SOL",
    address="So11111111111111111111111111111111111111112",
    entry_price=150.0,
    size_usd=3.0,
    hype_score=75.0,
    risk_level=RiskLevel.MODERATE
)

# Update price
portfolio.update_position_price("SOL", 155.0)

# Get summary
summary = portfolio.get_portfolio_summary()
print(f"Total Value: ${summary['total_value']:.2f}")
print(f"Return: {summary['total_return_pct']:+.2f}%")
```

### Backtesting

```python
from snail_scalp import run_backtest

result = run_backtest(
    capital=20.0,
    days=30,
    save=True
)

print(f"Return: {result.total_return_pct:+.2f}%")
print(f"Win Rate: {result.win_rate:.1f}%")
print(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
```

## Custom Strategies

### Modify Entry Criteria

```python
from snail_scalp.indicators import TechnicalIndicators

class CustomIndicators(TechnicalIndicators):
    def is_entry_signal(self, current_price, **kwargs):
        # Add custom condition
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        
        # Standard conditions
        at_bb = current_price <= bb.lower * 1.001
        rsi_ok = 25 <= rsi <= 35
        
        # Custom: Volume spike
        recent_volume = sum(self.volumes[-5:]) / 5
        avg_volume = sum(self.volumes) / len(self.volumes)
        volume_spike = recent_volume > avg_volume * 1.5
        
        return at_bb and rsi_ok and volume_spike
```

### Custom Risk Manager

```python
from snail_scalp.risk_manager import RiskManager

class CustomRiskManager(RiskManager):
    def check_position_size(self, available_capital, allocation, max_position):
        # Custom sizing logic
        if self.daily_stats.consecutive_losses > 0:
            # Reduce size after loss
            return max_position * 0.5
        return super().check_position_size(available_capital, allocation, max_position)
```

## API Integration

### Jupiter Swap (Live Trading)

```python
import aiohttp

async def execute_jupiter_swap(
    input_mint: str,
    output_mint: str,
    amount: int,  # In lamports/smallest unit
    slippage_bps: int = 50  # 0.5%
):
    """Execute swap via Jupiter API"""
    
    # Get quote
    quote_url = "https://quote-api.jup.ag/v6/quote"
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "slippageBps": slippage_bps,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(quote_url, params=params) as resp:
            quote = await resp.json()
        
        # Execute swap (requires wallet signing)
        # ... implementation
```

### Webhook Notifications

```python
import aiohttp

async def send_discord_alert(message: str, webhook_url: str):
    """Send trade alert to Discord"""
    async with aiohttp.ClientSession() as session:
        await session.post(
            webhook_url,
            json={"content": message}
        )

# Usage in trader
async def on_trade_close(trade):
    await send_discord_alert(
        f"Trade closed: {trade.pnl_usd:+.2f} USD",
        webhook_url="https://discord.com/api/webhooks/..."
    )
```

## Configuration

### Environment Variables

```bash
# .env file
BIRDEYE_API_KEY=your_key_here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
RPC_ENDPOINT=https://your-rpc-endpoint.com
```

```python
import os

api_key = os.getenv("BIRDEYE_API_KEY")
webhook = os.getenv("DISCORD_WEBHOOK_URL")
```

### Custom Config File

```python
# my_config.py
from snail_scalp.config import StrategyConfig

my_strategy = StrategyConfig(
    rsi_oversold_min=20,  # More aggressive
    rsi_oversold_max=40,
    tp1_percent=3.0,  # Higher targets
    tp2_percent=5.0,
    stop_loss_percent=2.0,  # Wider stops
)
```

## Database Integration

### SQLite for Trade History

```python
import sqlite3
from datetime import datetime

class TradeDatabase:
    def __init__(self, db_path="trades.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                entry_price REAL,
                exit_price REAL,
                size_usd REAL,
                pnl_usd REAL,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                close_reason TEXT
            )
        """)
    
    def save_trade(self, trade):
        self.conn.execute("""
            INSERT INTO trades 
            (symbol, entry_price, exit_price, size_usd, pnl_usd, 
             entry_time, exit_time, close_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.symbol,
            trade.entry_price,
            trade.exit_price,
            trade.size_usd,
            trade.pnl_usd,
            trade.entry_time,
            trade.exit_time,
            trade.close_reason
        ))
        self.conn.commit()
```

## Performance Optimization

### Async Batch Processing

```python
import asyncio

async def screen_multiple_tokens(tokens):
    """Screen multiple tokens concurrently"""
    tasks = []
    for token in tokens:
        task = asyncio.create_task(screen_token(token))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_indicators(price_data):
    """Cache indicator calculations"""
    # ... calculation
    return indicators
```

## Testing

### Unit Test Example

```python
import pytest
from snail_scalp.indicators import TechnicalIndicators

def test_entry_signal():
    indicators = TechnicalIndicators()
    
    # Add price data
    for price in [100, 101, 102, 101, 100, 99, 98, 97, 96, 95,
                  94, 93, 92, 91, 90, 91, 92, 93, 94, 95]:
        indicators.add_price(price)
    
    # Check signal at oversold level
    assert indicators.is_entry_signal(91) == True
```

## Deployment

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

CMD ["uv", "run", "python", "-m", "snail_scalp", "--multi"]
```

### Systemd Service

```ini
# /etc/systemd/system/snail-scalp.service
[Unit]
Description=Solana Snail Scalp Bot
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/solana-snail-scalp
ExecStart=/home/trader/.cargo/bin/uv run python -m snail_scalp --multi
Restart=always

[Install]
WantedBy=multi-user.target
```

## Further Reading

- [API Reference](API_REFERENCE.md) - Full module documentation
- [Examples](../examples/) - Sample scripts
- [Architecture](ARCHITECTURE.md) - System design

"""Screening Trading Bot

Integrates token screening with live trading/simulation.
Automatically selects best tokens and trades them using
the scalping strategy.
"""

import asyncio
import aiohttp
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from snail_scalp.config import trading_config, strategy_config
from snail_scalp.multi_token_feed import MultiTokenFeed, TokenData
from snail_scalp.portfolio_manager import PortfolioManager, PositionStatus, CloseReason
from snail_scalp.indicators import TechnicalIndicators
from snail_scalp.risk_manager import RiskManager
from snail_scalp.token_screener import RiskLevel


class TokenTrader:
    """Handles trading logic for a single token"""
    
    def __init__(self, symbol: str, address: str, portfolio: PortfolioManager):
        self.symbol = symbol
        self.address = address
        self.portfolio = portfolio
        self.indicators = TechnicalIndicators(period=strategy_config.bb_period)
        
        # Track price history for indicators
        self.price_history: List[tuple] = []  # (timestamp, price, volume)
        self.last_price: Optional[float] = None
    
    def add_price(self, price: float, volume: float = 0):
        """Add new price point"""
        self.indicators.add_price(price, volume)
        self.last_price = price
        self.price_history.append((datetime.now(), price, volume))
        
        # Keep only last 100 points
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
    
    def check_entry_signal(self) -> bool:
        """Check if we should enter a position"""
        if not self.last_price:
            return False
        
        # Use existing strategy
        return self.indicators.is_entry_signal(
            self.last_price,
            rsi_min=strategy_config.rsi_oversold_min,
            rsi_max=strategy_config.rsi_oversold_max,
            min_band_width=strategy_config.min_band_width_percent,
        )
    
    def check_exit_signals(self, position) -> Optional[CloseReason]:
        """Check if we should exit position"""
        if not self.last_price or not position:
            return None
        
        entry = position.entry_price
        pnl_pct = (self.last_price - entry) / entry * 100
        
        # Check stop loss
        if pnl_pct <= -strategy_config.stop_loss_percent:
            return CloseReason.STOP_LOSS
        
        # Check TP2 (only if TP1 already hit)
        if position.tp1_hit and pnl_pct >= strategy_config.tp2_percent:
            return CloseReason.TP2
        
        return None
    
    def check_tp1(self, position) -> bool:
        """Check if TP1 hit"""
        if not self.last_price or not position or position.tp1_hit:
            return False
        
        entry = position.entry_price
        pnl_pct = (self.last_price - entry) / entry * 100
        
        return pnl_pct >= strategy_config.tp1_percent
    
    def check_dca_trigger(self, position) -> bool:
        """Check if DCA should trigger"""
        if not self.last_price or not position or position.dca_done:
            return False
        
        entry = position.entry_price
        pnl_pct = (self.last_price - entry) / entry * 100
        
        return pnl_pct <= -strategy_config.dca_trigger_percent
    
    def get_stats(self) -> Dict:
        """Get indicator stats"""
        return self.indicators.get_stats()


class ScreeningTradingBot:
    """Bot that screens tokens and trades the best ones"""
    
    def __init__(
        self,
        initial_capital: float = 20.0,
        max_positions: int = 3,
        simulate: bool = True,
        data_file: str = "data/top10_solana_coins.json",
        min_hype_score: float = 60.0,
        max_risk_level: RiskLevel = RiskLevel.HIGH,
        trading_hours: tuple = (9, 11),  # UTC hours
    ):
        self.initial_capital = initial_capital
        self.simulate = simulate
        self.min_hype_score = min_hype_score
        self.max_risk_level = max_risk_level
        self.trading_start, self.trading_end = trading_hours
        
        # Initialize components
        self.token_feed = MultiTokenFeed(data_file=data_file)
        self.portfolio = PortfolioManager(
            initial_capital=initial_capital,
            max_positions=max_positions,
            simulate=simulate
        )
        self.risk = RiskManager(
            daily_loss_limit=trading_config.daily_loss_limit_usd,
            max_consecutive_losses=trading_config.max_consecutive_losses,
            trading_start_utc=self.trading_start,
            trading_end_utc=self.trading_end,
            simulate=simulate,
        )
        
        # Token traders
        self.token_traders: Dict[str, TokenTrader] = {}
        
        # Screening results
        self.screened_tokens: List[TokenData] = []
        self.top_tokens: List[TokenData] = []
        
        self.running = False
    
    def screen_tokens(self) -> List[TokenData]:
        """Screen and rank tokens"""
        print("\n" + "="*70)
        print("TOKEN SCREENING")
        print("="*70)
        
        # Get all ranked tokens
        self.screened_tokens = self.token_feed.get_ranked_tokens(
            min_hype_score=self.min_hype_score,
            max_risk=self.max_risk_level
        )
        
        # Get best scalping candidates
        self.top_tokens = self.token_feed.get_best_scalping_candidates(
            n=self.portfolio.state.max_concurrent_positions * 2  # 2x for rotation
        )
        
        print(f"\nScreened {len(self.screened_tokens)} tokens")
        print(f"Top candidates: {[t.metrics.symbol for t in self.top_tokens[:5]]}")
        
        # Initialize traders for top tokens
        for token in self.top_tokens:
            symbol = token.metrics.symbol
            if symbol not in self.token_traders:
                self.token_traders[symbol] = TokenTrader(
                    symbol=symbol,
                    address=token.metrics.address,
                    portfolio=self.portfolio
                )
        
        return self.top_tokens
    
    async def run(self):
        """Main trading loop"""
        self.running = True
        
        # Initial screening
        self.screen_tokens()
        self.print_banner()
        
        # Simulate price feed (in real version, this would fetch from DEX)
        await self._run_simulation_loop()
    
    def print_banner(self):
        """Print startup banner"""
        mode = "SIMULATION" if self.simulate else "LIVE TRADING"
        print("\n" + "="*70)
        print(f"SCREENING TRADING BOT - {mode}")
        print("="*70)
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Max Positions: {self.portfolio.state.max_concurrent_positions}")
        print(f"Min Hype Score: {self.min_hype_score}")
        print(f"Max Risk Level: {self.max_risk_level.name}")
        print(f"Trading Window: {self.trading_start:02d}:00-{self.trading_end:02d}:00 UTC")
        print("="*70)
    
    async def _run_simulation_loop(self):
        """Run simulation using historical/estimated price data"""
        print("\n[STARTING TRADING LOOP]")
        
        # In simulation, we use the token data to generate price movements
        iteration = 0
        
        while self.running:
            try:
                # Check trading window
                current_time = datetime.now()
                in_window = self.risk.is_trading_window(current_time)
                
                if not in_window:
                    if iteration % 60 == 0:  # Print every ~minute
                        print(f"[{current_time.strftime('%H:%M')}] Outside trading window")
                    await asyncio.sleep(1)
                    iteration += 1
                    continue
                
                # Check risk limits
                if not self.risk.can_trade_today():
                    print("[STOP] Daily risk limit reached")
                    break
                
                # Re-screen tokens every 30 iterations
                if iteration % 30 == 0:
                    self.screen_tokens()
                
                # Process each token
                for token_data in self.top_tokens[:5]:  # Top 5 tokens
                    await self._process_token(token_data)
                
                # Print portfolio status periodically
                if iteration % 10 == 0:
                    self.portfolio.print_portfolio()
                
                iteration += 1
                await asyncio.sleep(1)  # 1 second per iteration in simulation
                
            except KeyboardInterrupt:
                print("\n[STOPPED] User interrupted")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                await asyncio.sleep(5)
        
        # Print final summary
        self.print_summary()
    
    async def _process_token(self, token_data: TokenData):
        """Process a single token - check entry/exit"""
        symbol = token_data.metrics.symbol
        trader = self.token_traders.get(symbol)
        
        if not trader:
            return
        
        # Simulate price (in real version, fetch from DEX)
        current_price = self._simulate_price(token_data)
        trader.add_price(current_price, token_data.metrics.volume_24h)
        
        # Check if we have a position
        position = self.portfolio.get_position(symbol)
        
        if position and position.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]:
            # Update unrealized PnL
            self.portfolio.update_position_price(symbol, current_price)
            
            # Check TP1
            if trader.check_tp1(position):
                success, pnl = self.portfolio.partial_close(
                    symbol, current_price, portion=0.5
                )
                if success:
                    print(f"[TP1] {symbol}: Closed 50% at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                    self.risk.record_trade(pnl)
            
            # Check DCA
            elif trader.check_dca_trigger(position):
                dca_size = self.portfolio.calculate_position_size(symbol, position.risk_level_at_entry) * 0.5
                if self.portfolio.execute_dca(symbol, current_price, dca_size):
                    print(f"[DCA] {symbol}: Added ${dca_size:.2f} at ${current_price:.6f}")
            
            # Check exit signals
            exit_reason = trader.check_exit_signals(position)
            if exit_reason:
                success, pnl = self.portfolio.close_position(symbol, current_price, exit_reason)
                if success:
                    print(f"[{exit_reason.value.upper()}] {symbol}: Closed at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                    self.risk.record_trade(pnl)
        
        else:
            # Look for entry
            # Only enter if we have enough indicator data
            if len(trader.price_history) >= strategy_config.bb_period:
                if trader.check_entry_signal():
                    # Calculate position size based on risk
                    risk_level = token_data.hype.risk_level if token_data.hype else RiskLevel.MODERATE
                    size = self.portfolio.calculate_position_size(symbol, risk_level)
                    
                    hype_score = token_data.hype.total_hype_score if token_data.hype else 0
                    
                    if self.portfolio.open_position(
                        symbol=symbol,
                        address=token_data.metrics.address,
                        entry_price=current_price,
                        size_usd=size,
                        hype_score=hype_score,
                        risk_level=risk_level
                    ):
                        print(f"[ENTRY] {symbol}: Opened ${size:.2f} at ${current_price:.6f} "
                              f"(Hype: {hype_score:.1f}, Risk: {risk_level.name})")
    
    def _simulate_price(self, token_data: TokenData) -> float:
        """Simulate realistic price movement for backtesting"""
        import random
        import math
        
        base_price = token_data.metrics.price_usd
        
        # Add random walk with trend bias
        volatility = 0.002  # 0.2% per step
        trend_bias = (token_data.metrics.change_24h / 100) / 1440  # Spread 24h change over minutes
        
        # Random walk
        change = random.gauss(trend_bias, volatility)
        
        # If we have price history, use last price
        symbol = token_data.metrics.symbol
        trader = self.token_traders.get(symbol)
        if trader and trader.last_price:
            return trader.last_price * (1 + change)
        
        return base_price
    
    def print_summary(self):
        """Print final trading summary"""
        print("\n" + "="*70)
        print("FINAL SUMMARY")
        print("="*70)
        
        summary = self.portfolio.get_portfolio_summary()
        
        print(f"Initial Capital: ${summary['initial_capital']:.2f}")
        print(f"Final Value: ${summary['total_value']:.2f}")
        print(f"Total Return: {summary['total_return_pct']:+.2f}%")
        print(f"Realized PnL: ${summary['total_realized_pnl']:+.2f}")
        print(f"Unrealized PnL: ${summary['total_unrealized_pnl']:+.2f}")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        
        if summary['open_positions']:
            print(f"\nOpen Positions: {len(summary['open_positions'])}")
        
        print("="*70)


async def main():
    """Run the screening bot"""
    bot = ScreeningTradingBot(
        initial_capital=20.0,
        max_positions=3,
        simulate=True,
        min_hype_score=60.0,
        max_risk_level=RiskLevel.HIGH,
    )
    
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

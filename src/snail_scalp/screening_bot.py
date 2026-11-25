"""Screening Trading Bot

Integrates token screening with live trading/simulation.
Automatically selects best tokens and trades them using
the scalping strategy.
"""

import asyncio
import aiohttp
from typing import List, Optional, Dict
from datetime import datetime, timezone
from pathlib import Path

from snail_scalp.config import trading_config, strategy_config, execution_config, Stage
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
        
        # Regime-aware gate + entry mode
        regime = "UNKNOWN"
        if strategy_config.use_regime_detection:
            regime = self.indicators.detect_market_regime(strategy_config.regime_adx_threshold)
            if regime == "TRENDING_DOWN" and strategy_config.skip_trending_down_entries:
                return False
            if regime == "CHOPPY" and strategy_config.skip_choppy_markets:
                return False

        # Confidence gate
        if strategy_config.use_confidence_gate:
            conf = self.indicators.calculate_confidence_score()
            if conf < strategy_config.min_confidence_score:
                return False

        # Bull trends use momentum; everything else uses mean reversion
        if strategy_config.regime_aware_entries and regime == "TRENDING_UP":
            return self.indicators.is_momentum_entry_signal(
                self.last_price,
                rsi_min=strategy_config.momentum_rsi_min,
                rsi_max=strategy_config.momentum_rsi_max,
                min_band_width=strategy_config.min_band_width_percent,
                volume_threshold=strategy_config.momentum_volume_threshold,
            )

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
        stage: Stage = Stage.PAPER,
        data_file: str = "data/top10_solana_coins.json",
        min_hype_score: float = 60.0,
        max_risk_level: RiskLevel = RiskLevel.HIGH,
        trading_hours: tuple = (9, 11),  # UTC hours
    ):
        self.initial_capital = initial_capital
        self.simulate = simulate
        self.stage = Stage(stage) if isinstance(stage, (str, Stage)) else Stage.PAPER
        self.min_hype_score = min_hype_score
        self.max_risk_level = max_risk_level
        self.trading_start, self.trading_end = trading_hours
        
        # Initialize components
        feed_use_live = not self.simulate
        self.token_feed = MultiTokenFeed(
            data_file="live" if feed_use_live else data_file,
            use_live=feed_use_live,
            min_liquidity=20000.0,
        )
        self.portfolio = PortfolioManager(
            initial_capital=initial_capital,
            max_positions=max_positions,
            reserve_pct=execution_config.reserve_pct,
            simulate=simulate,
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
        
        if self.simulate:
            await self._run_simulation_loop()
        else:
            await self._run_live_loop()
    
    def print_banner(self):
        """Print startup banner"""
        mode = "SIMULATION" if self.simulate else f"LIVE TRADING ({self.stage.value.upper()})"
        print("\n" + "="*70)
        print(f"SCREENING TRADING BOT - {mode}")
        print("="*70)
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Max Positions:   {self.portfolio.state.max_concurrent_positions}")
        print(f"Reserve:         {self.portfolio.state.reserve_pct:.0f}% (${self.initial_capital * self.portfolio.state.reserve_pct / 100:.2f})")
        print(f"Min Hype Score:  {self.min_hype_score}")
        print(f"Max Risk Level:  {self.max_risk_level.name}")
        print(f"Trading Window:  {self.trading_start:02d}:00-{self.trading_end:02d}:00 UTC")
        print("="*70)
    
    async def _run_simulation_loop(self):
        """Run simulation using historical/estimated price data"""
        print("\n[STARTING TRADING LOOP]")
        
        # In simulation, we use the token data to generate price movements
        iteration = 0
        
        while self.running:
            try:
                # Check trading window
                current_time = datetime.now(timezone.utc)
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
            # Phase filter: only trade allowed momentum phases
            token_phase = getattr(token_data, "phase", None)
            if strategy_config.use_phase_filter and token_phase is not None:
                if token_phase not in strategy_config.allowed_phases:
                    return

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
    
    async def _run_live_loop(self):
        """Run live multi-token trading loop with live prices, execution, and continuous rotation."""
        from snail_scalp.real_data_fetcher import DexScreenerFetcher

        print(f"\n[STARTING LIVE MULTI-TOKEN LOOP - STAGE: {self.stage.value.upper()}]")
        poll_interval = execution_config.exit_poll_seconds
        fetcher = DexScreenerFetcher()
        iteration = 0

        while self.running:
            try:
                # 1. Check trading window
                current_time = datetime.now(timezone.utc)
                in_window = self.risk.is_trading_window(current_time)
                if not in_window:
                    if iteration % 15 == 0:
                        print(f"[{current_time.strftime('%H:%M:%S')} UTC] Outside trading window ({self.trading_start:02d}:00-{self.trading_end:02d}:00 UTC)")
                    await asyncio.sleep(poll_interval)
                    iteration += 1
                    continue

                # 2. Check risk circuit breakers
                if not self.risk.can_trade_today():
                    print("[STOP] Daily risk limit reached. Halting live trading.")
                    break

                # 3. Continuous rotation / Re-screening:
                open_slots = self.portfolio.state.max_concurrent_positions - self.portfolio.state.open_position_count
                if open_slots > 0 and (iteration % 15 == 0 or len(self.top_tokens) == 0):
                    self.screen_tokens()

                # 4. Fetch live prices for active positions and candidate tokens
                active_symbols = [
                    sym for sym, pos in self.portfolio.state.positions.items()
                    if pos.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]
                ]
                candidate_symbols = [t.metrics.symbol for t in self.top_tokens[:open_slots + 2]]
                all_symbols = list(set(active_symbols + candidate_symbols))
                if all_symbols:
                    await self._update_live_prices(fetcher, all_symbols)

                # 5. Process exits for active positions
                for sym in active_symbols:
                    await self._manage_live_position(sym)

                # 6. Process entries if slots are available
                if self.portfolio.state.open_position_count < self.portfolio.state.max_concurrent_positions:
                    for token_data in self.top_tokens:
                        if self.portfolio.state.open_position_count >= self.portfolio.state.max_concurrent_positions:
                            break
                        sym = token_data.metrics.symbol
                        if not self.portfolio.has_open_position(sym):
                            await self._evaluate_live_entry(token_data)

                # 7. Print portfolio status periodically
                if iteration % 10 == 0:
                    self.portfolio.print_portfolio()

                iteration += 1
                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                break
            except KeyboardInterrupt:
                print("\n[STOPPED] User interrupted")
                break
            except Exception as e:
                print(f"[LIVE][ERROR] Loop error: {e}")
                await asyncio.sleep(poll_interval)

        self.print_summary()

    async def _update_live_prices(self, fetcher, symbols: List[str]):
        """Fetch live prices for a list of symbols and feed them to token traders."""
        addrs_map: Dict[str, str] = {}
        for sym in symbols:
            trader = self.token_traders.get(sym)
            if trader and trader.address:
                addrs_map[trader.address] = sym
            else:
                for t in self.top_tokens:
                    if t.metrics.symbol == sym:
                        addrs_map[t.metrics.address] = sym
                        if sym not in self.token_traders:
                            self.token_traders[sym] = TokenTrader(
                                symbol=sym,
                                address=t.metrics.address,
                                portfolio=self.portfolio,
                            )
                        break

        if not addrs_map:
            return

        try:
            pairs = await fetcher.get_tokens_batch(list(addrs_map.keys()))
            for pair in pairs:
                base_addr = pair.get("baseToken", {}).get("address")
                sym = addrs_map.get(base_addr)
                if not sym:
                    continue
                trader = self.token_traders.get(sym)
                if not trader:
                    continue
                price_usd = float(pair.get("priceUsd", 0) or 0)
                vol_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
                if price_usd > 0:
                    trader.add_price(price_usd, vol_24h)
                    self.portfolio.update_position_price(sym, price_usd)
        except Exception as e:
            print(f"[LIVE][WARN] Price update failed: {e}")

    async def _manage_live_position(self, symbol: str):
        """Monitor and exit an active live/paper position."""
        trader = self.token_traders.get(symbol)
        position = self.portfolio.get_position(symbol)
        if not trader or not position or position.status not in [PositionStatus.OPEN, PositionStatus.PARTIAL]:
            return

        current_price = trader.last_price
        if not current_price:
            return

        # Check TP1
        if trader.check_tp1(position):
            if self.stage == Stage.LIVE:
                from snail_scalp.jupiter import swap, to_base_units, USDT_MINT
                swap_res = await swap(
                    position.mint,
                    USDT_MINT,
                    to_base_units(position.size_usd * 0.5, position.decimals),
                    slippage_bps=int(execution_config.slippage_pct * 100),
                )
                if swap_res.get("status") in ["executed", "pending_signature"]:
                    success, pnl = self.portfolio.partial_close(symbol, current_price, portion=0.5)
                    if success:
                        print(f"[LIVE][TP1] {symbol}: Sold 50% on-chain at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                        self.risk.record_trade(pnl)
                else:
                    print(f"[LIVE][TP1][WARN] Swap unconfirmed ({swap_res.get('status')}), retrying next poll.")
            else:
                success, pnl = self.portfolio.partial_close(symbol, current_price, portion=0.5)
                if success:
                    print(f"[PAPER][TP1] {symbol}: Closed 50% at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                    self.risk.record_trade(pnl)
            return

        # Check DCA
        if trader.check_dca_trigger(position):
            dca_size = self.portfolio.calculate_position_size(symbol, position.risk_level_at_entry) * 0.5
            if self.stage == Stage.LIVE:
                from snail_scalp.jupiter import swap, to_base_units, USDT_MINT
                swap_res = await swap(
                    USDT_MINT,
                    position.mint,
                    to_base_units(dca_size, 6),
                    slippage_bps=int(execution_config.slippage_pct * 100),
                )
                if swap_res.get("status") in ["executed", "pending_signature"]:
                    if self.portfolio.execute_dca(symbol, current_price, dca_size):
                        print(f"[LIVE][DCA] {symbol}: Added ${dca_size:.2f} on-chain at ${current_price:.6f}")
                else:
                    print(f"[LIVE][DCA][WARN] DCA swap unconfirmed ({swap_res.get('status')}).")
            else:
                if self.portfolio.execute_dca(symbol, current_price, dca_size):
                    print(f"[PAPER][DCA] {symbol}: Added ${dca_size:.2f} at ${current_price:.6f}")
            return

        # Check exit signals
        exit_reason = trader.check_exit_signals(position)
        if exit_reason:
            if self.stage == Stage.LIVE:
                from snail_scalp.jupiter import swap, to_base_units, USDT_MINT
                swap_res = await swap(
                    position.mint,
                    USDT_MINT,
                    to_base_units(position.size_usd, position.decimals),
                    slippage_bps=int(execution_config.slippage_pct * 100),
                )
                if swap_res.get("status") in ["executed", "pending_signature"]:
                    success, pnl = self.portfolio.close_position(symbol, current_price, exit_reason)
                    if success:
                        print(f"[LIVE][{exit_reason.value.upper()}] {symbol}: Sold on-chain at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                        self.risk.record_trade(pnl)
                        # Immediately re-screen to fill vacated slot (continuous rotation)
                        self.screen_tokens()
                else:
                    print(f"[LIVE][EXIT][WARN] Exit swap unconfirmed ({swap_res.get('status')}), retrying next poll.")
            else:
                success, pnl = self.portfolio.close_position(symbol, current_price, exit_reason)
                if success:
                    print(f"[PAPER][{exit_reason.value.upper()}] {symbol}: Closed at ${current_price:.6f}, PnL: ${pnl:+.2f}")
                    self.risk.record_trade(pnl)
                    self.screen_tokens()

    async def _evaluate_live_entry(self, token_data: TokenData):
        """Evaluate a candidate token and enter position if signal triggers."""
        symbol = token_data.metrics.symbol
        trader = self.token_traders.get(symbol)
        if not trader or not trader.last_price:
            return

        # Phase filter
        token_phase = getattr(token_data, "phase", None)
        if strategy_config.use_phase_filter and token_phase is not None:
            if token_phase not in strategy_config.allowed_phases:
                return

        # Indicators check
        if len(trader.price_history) >= strategy_config.bb_period:
            if trader.check_entry_signal():
                risk_level = token_data.hype.risk_level if token_data.hype else RiskLevel.MODERATE
                size = self.portfolio.calculate_position_size(symbol, risk_level)
                if size < 1.0 or not self.portfolio.state.can_open_position(size):
                    return

                hype_score = token_data.hype.total_hype_score if token_data.hype else 0.0
                current_price = trader.last_price

                if self.stage == Stage.LIVE:
                    from snail_scalp.jupiter import swap, to_base_units, USDT_MINT
                    swap_res = await swap(
                        USDT_MINT,
                        token_data.metrics.address,
                        to_base_units(size, 6),
                        slippage_bps=int(execution_config.slippage_pct * 100),
                    )
                    if swap_res.get("status") in ["executed", "pending_signature"]:
                        opened = self.portfolio.open_position(
                            symbol=symbol,
                            address=token_data.metrics.address,
                            entry_price=current_price,
                            size_usd=size,
                            hype_score=hype_score,
                            risk_level=risk_level,
                            mint=token_data.metrics.address,
                            decimals=6,
                            entry_signature=swap_res.get("signature"),
                        )
                        if opened:
                            print(f"[LIVE][ENTRY] {symbol}: Opened ${size:.2f} on-chain at ${current_price:.6f} "
                                  f"(Hype: {hype_score:.1f}, Risk: {risk_level.name})")
                    else:
                        print(f"[LIVE][ENTRY][WARN] Swap failed ({swap_res.get('status')}) for {symbol}: {swap_res.get('error', '')}")
                else:
                    opened = self.portfolio.open_position(
                        symbol=symbol,
                        address=token_data.metrics.address,
                        entry_price=current_price,
                        size_usd=size,
                        hype_score=hype_score,
                        risk_level=risk_level,
                        mint=token_data.metrics.address,
                        decimals=6,
                        entry_signature="sim_paper_entry",
                    )
                    if opened:
                        print(f"[PAPER][ENTRY] {symbol}: Opened ${size:.2f} at ${current_price:.6f} "
                              f"(Hype: {hype_score:.1f}, Risk: {risk_level.name})")
    
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

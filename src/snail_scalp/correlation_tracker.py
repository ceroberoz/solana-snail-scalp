"""Correlation Risk Management - US-3.3"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TokenPriceHistory:
    """Store price history for a single token"""
    symbol: str
    prices: List[float]
    max_history: int = 50
    
    def add_price(self, price: float):
        """Add new price and maintain max history"""
        self.prices.append(price)
        if len(self.prices) > self.max_history:
            self.prices = self.prices[-self.max_history:]
    
    def get_returns(self) -> List[float]:
        """Calculate price returns (percentage changes)"""
        if len(self.prices) < 2:
            return []
        returns = []
        for i in range(1, len(self.prices)):
            ret = (self.prices[i] - self.prices[i-1]) / self.prices[i-1]
            returns.append(ret)
        return returns


class CorrelationTracker:
    """Track correlations between multiple tokens"""
    
    def __init__(self, threshold: float = 0.7, lookback: int = 20):
        self.token_histories: Dict[str, TokenPriceHistory] = {}
        self.threshold = threshold  # Correlation threshold
        self.lookback = lookback   # Lookback period for correlation calc
    
    def add_price(self, symbol: str, price: float):
        """Add price update for a token"""
        if symbol not in self.token_histories:
            self.token_histories[symbol] = TokenPriceHistory(symbol=symbol, prices=[])
        self.token_histories[symbol].add_price(price)
    
    def calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate Pearson correlation between two tokens"""
        if symbol1 not in self.token_histories or symbol2 not in self.token_histories:
            return 0.0
        
        hist1 = self.token_histories[symbol1]
        hist2 = self.token_histories[symbol2]
        
        # Get returns for both tokens
        returns1 = hist1.get_returns()[-self.lookback:]
        returns2 = hist2.get_returns()[-self.lookback:]
        
        if len(returns1) < 5 or len(returns2) < 5:
            return 0.0  # Not enough data
        
        # Ensure same length
        min_len = min(len(returns1), len(returns2))
        returns1 = returns1[-min_len:]
        returns2 = returns2[-min_len:]
        
        # Calculate Pearson correlation
        if len(returns1) < 2:
            return 0.0
        
        mean1, mean2 = np.mean(returns1), np.mean(returns2)
        std1, std2 = np.std(returns1), np.std(returns2)
        
        if std1 == 0 or std2 == 0:
            return 0.0
        
        covariance = np.mean([(r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2)])
        correlation = covariance / (std1 * std2)
        
        return correlation
    
    def get_correlated_tokens(self, symbol: str, active_symbols: List[str]) -> List[Tuple[str, float]]:
        """Get list of tokens correlated with the given symbol"""
        correlated = []
        
        for other_symbol in active_symbols:
            if other_symbol == symbol:
                continue
            
            corr = self.calculate_correlation(symbol, other_symbol)
            if abs(corr) >= self.threshold:
                correlated.append((other_symbol, corr))
        
        # Sort by correlation strength
        correlated.sort(key=lambda x: abs(x[1]), reverse=True)
        return correlated
    
    def check_correlation_risk(self, symbol: str, active_symbols: List[str], max_correlated: int = 2) -> Tuple[bool, List[str]]:
        """Check if adding this token would exceed correlation limit
        
        Returns:
            (allowed, correlated_symbols): Whether position is allowed and list of correlated tokens
        """
        correlated = self.get_correlated_tokens(symbol, active_symbols)
        
        # Count how many are already in active positions
        existing_correlated = [s for s, _ in correlated]
        
        if len(existing_correlated) >= max_correlated:
            return False, existing_correlated[:max_correlated]
        
        return True, existing_correlated
    
    def get_correlation_matrix(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get correlation matrix for all symbols"""
        matrix = {}
        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                if s1 == s2:
                    matrix[s1][s2] = 1.0
                else:
                    matrix[s1][s2] = self.calculate_correlation(s1, s2)
        return matrix
    
    def get_stats(self) -> dict:
        """Get tracker statistics"""
        return {
            "tracked_tokens": len(self.token_histories),
            "symbols": list(self.token_histories.keys()),
            "threshold": self.threshold,
            "lookback": self.lookback,
        }

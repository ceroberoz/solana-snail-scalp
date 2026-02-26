"""Position sizing calculations for forex trading"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Position sizing result"""
    lots: float           # Position size in standard lots
    micro_lots: float     # Position size in micro lots (0.01)
    units: int            # Position size in units (1 unit = 0.00001 lot)
    
    stop_pips: float      # Stop loss distance in pips
    risk_amount: float    # Risk amount in USD
    
    pip_value: float      # Value of 1 pip per micro lot
    margin_required: float  # Estimated margin required


class PositionSizer:
    """
    Calculate forex position sizes based on risk management rules
    
    Key Concepts:
    - 1 standard lot = 100,000 units
    - 1 mini lot = 10,000 units
    - 1 micro lot = 1,000 units
    - 1 pip = 0.0001 for most pairs (0.01 for JPY pairs)
    """
    
    def __init__(
        self,
        account_balance: float,
        risk_per_trade_pct: float = 2.0,
        leverage: float = 30.0,
    ):
        """
        Initialize position sizer
        
        Args:
            account_balance: Current account balance in USD
            risk_per_trade_pct: Risk per trade as % of account
            leverage: Account leverage (default 30:1 for ESMA)
        """
        self.account_balance = account_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.leverage = leverage
    
    def calculate(
        self,
        entry_price: float,
        stop_price: float,
        pip_value_per_micro_lot: float = 0.074,  # USD/SGD
        pip_size: float = 0.0001,
    ) -> PositionSize:
        """
        Calculate position size
        
        Formula:
        Risk Amount = Account Balance × Risk %
        Stop Value = Stop Pips × Pip Value × Position Size
        Position Size = Risk Amount / (Stop Pips × Pip Value)
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            pip_value_per_micro_lot: Pip value for 0.01 lot
            pip_size: Pip size for the pair
            
        Returns:
            PositionSize with all calculations
        """
        # Calculate stop distance
        stop_distance = abs(entry_price - stop_price)
        stop_pips = stop_distance / pip_size
        
        if stop_pips == 0:
            logger.error("Stop distance cannot be zero")
            raise ValueError("Stop price cannot equal entry price")
        
        # Calculate risk amount
        risk_amount = self.account_balance * (self.risk_per_trade_pct / 100)
        
        # Calculate position size in micro lots
        # Risk = Stop Pips × Pip Value × Position Size
        # Position Size = Risk / (Stop Pips × Pip Value)
        micro_lots = risk_amount / (stop_pips * pip_value_per_micro_lot)
        
        # Convert to standard lots
        lots = micro_lots / 100
        
        # Round to 2 decimal places (micro lot precision)
        lots = round(lots, 2)
        micro_lots = round(lots * 100, 2)
        
        # Calculate units (OANDA format)
        units = int(lots * 100_000)
        
        # Calculate margin required
        # Margin = (Position Size × Contract Size) / Leverage
        contract_value = lots * 100_000 * entry_price
        margin_required = contract_value / self.leverage
        
        return PositionSize(
            lots=lots,
            micro_lots=micro_lots,
            units=units,
            stop_pips=stop_pips,
            risk_amount=risk_amount,
            pip_value=pip_value_per_micro_lot,
            margin_required=margin_required,
        )
    
    def validate_position(
        self,
        position: PositionSize,
        min_lot_size: float = 0.01,  # 1 micro lot
        max_lot_size: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Validate position size
        
        Returns:
            (is_valid, reason)
        """
        # Check minimum size
        if position.lots < min_lot_size:
            return False, f"Position size {position.lots} below minimum {min_lot_size}"
        
        # Check maximum size
        if max_lot_size and position.lots > max_lot_size:
            return False, f"Position size {position.lots} above maximum {max_lot_size}"
        
        # Check margin availability
        available_margin = self.account_balance  # Simplified
        if position.margin_required > available_margin * 0.5:  # Use 50% max
            return False, f"Margin required {position.margin_required:.2f} too high"
        
        # Check risk amount
        max_risk = self.account_balance * 0.05  # Max 5% per trade
        if position.risk_amount > max_risk:
            return False, f"Risk amount {position.risk_amount:.2f} exceeds 5% limit"
        
        return True, "Valid"
    
    def adjust_for_correlation(
        self,
        base_position: PositionSize,
        correlation: float,
        max_correlation: float = 0.85
    ) -> PositionSize:
        """
        Adjust position size based on correlation with existing positions
        
        If highly correlated, reduce position size
        """
        if correlation <= max_correlation:
            return base_position
        
        # Reduce position proportionally to correlation
        reduction_factor = max(0, 1 - (correlation - max_correlation) / (1 - max_correlation))
        
        adjusted_lots = base_position.lots * reduction_factor
        adjusted_micro_lots = adjusted_lots * 100
        adjusted_units = int(adjusted_lots * 100_000)
        
        return PositionSize(
            lots=round(adjusted_lots, 2),
            micro_lots=round(adjusted_micro_lots, 2),
            units=adjusted_units,
            stop_pips=base_position.stop_pips,
            risk_amount=base_position.risk_amount * reduction_factor,
            pip_value=base_position.pip_value,
            margin_required=base_position.margin_required * reduction_factor,
        )


# Pre-calculated pip values for common pairs
# These are approximate and should be verified with your broker
PIP_VALUES = {
    "USD_SGD": 0.074,   # ~$0.074 per pip per micro lot (varies with rate)
    "USD_MYR": 0.022,   # ~$0.022 per pip per micro lot
    "EUR_USD": 0.10,    # $0.10 per pip per micro lot
    "GBP_USD": 0.10,    # $0.10 per pip per micro lot
    "USD_JPY": 0.067,   # ~$0.067 per pip per micro lot (varies with rate)
    "AUD_USD": 0.10,    # $0.10 per pip per micro lot
    "USD_CHF": 0.11,    # ~$0.11 per pip per micro lot (varies with rate)
}


def get_pip_value(pair_code: str) -> float:
    """Get pip value for a pair"""
    return PIP_VALUES.get(pair_code, 0.10)  # Default to $0.10


def calculate_position_size(
    account_balance: float,
    entry_price: float,
    stop_price: float,
    pair_code: str = "USD_SGD",
    risk_pct: float = 2.0,
    leverage: float = 30.0,
) -> PositionSize:
    """
    Convenience function to calculate position size
    
    Example:
        >>> pos = calculate_position_size(
        ...     account_balance=1000,
        ...     entry_price=1.3400,
        ...     stop_price=1.3375,  # 25 pip stop
        ...     pair_code="USD_SGD",
        ...     risk_pct=2.0,
        ... )
        >>> print(f"Size: {pos.lots} lots, Risk: ${pos.risk_amount:.2f}")
    """
    sizer = PositionSizer(
        account_balance=account_balance,
        risk_per_trade_pct=risk_pct,
        leverage=leverage,
    )
    
    pip_value = get_pip_value(pair_code)
    
    return sizer.calculate(
        entry_price=entry_price,
        stop_price=stop_price,
        pip_value_per_micro_lot=pip_value,
    )


# Example usage
if __name__ == "__main__":
    # Example: USD/SGD position sizing
    print("Position Sizing Example - USD/SGD")
    print("="*60)
    
    account = 1000.0
    entry = 1.3400
    stop = 1.3375  # 25 pips
    
    pos = calculate_position_size(
        account_balance=account,
        entry_price=entry,
        stop_price=stop,
        pair_code="USD_SGD",
        risk_pct=2.0,
    )
    
    print(f"Account Balance: ${account:,.2f}")
    print(f"Entry: {entry:.5f}")
    print(f"Stop: {stop:.5f}")
    print(f"Stop Distance: {pos.stop_pips:.1f} pips")
    print()
    print(f"Position Size: {pos.lots:.2f} lots ({pos.micro_lots:.0f} micro lots)")
    print(f"Units: {pos.units:,}")
    print(f"Risk Amount: ${pos.risk_amount:.2f}")
    print(f"Pip Value: ${pos.pip_value:.4f} per micro lot")
    print(f"Margin Required: ~${pos.margin_required:.2f}")

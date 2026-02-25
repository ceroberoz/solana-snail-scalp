#!/usr/bin/env python3
"""
Generate sample price data for simulation testing
Creates realistic SOL/USDC price movements with volatility patterns
"""

import csv
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def generate_sample_data(
    days: int = 2,
    interval_minutes: int = 5,
    base_price: float = 150.0,
    volatility: float = 0.008,
    output_file: str = "data/sample_price_data.csv",
):
    """
    Generate sample OHLCV-like price data

    Args:
        days: Number of days to generate
        interval_minutes: Data interval in minutes
        base_price: Starting price
        volatility: Price volatility per interval
        output_file: Output CSV filename
    """
    print(f"📊 Generating {days} days of {interval_minutes}-minute price data...")

    # Calculate total data points
    intervals_per_day = 24 * 60 // interval_minutes
    total_points = days * intervals_per_day

    data_points = []
    current_price = base_price

    # Start timestamp (begin at midnight UTC)
    timestamp = datetime(2024, 1, 15, 0, 0, 0)

    # Track daily high/low for realistic patterns
    daily_high = current_price
    daily_low = current_price
    current_day = timestamp.day

    for i in range(total_points):
        hour = timestamp.hour

        # Random walk with mean reversion
        change = np.random.normal(0, volatility)

        # Add time-of-day patterns
        if 9 <= hour < 11:  # Trading window - slightly more volatile
            change *= 1.3
            # Slight upward bias during trading hours
            change += 0.0005
        elif hour < 6 or hour > 22:  # Low volume hours - less volatile
            change *= 0.6

        # Mean reversion if price drifts too far
        price_drift = (current_price - base_price) / base_price
        change -= price_drift * 0.001  # Pull back to base

        # Apply change
        current_price *= 1 + change

        # Update daily high/low
        if timestamp.day != current_day:
            daily_high = current_price
            daily_low = current_price
            current_day = timestamp.day
        else:
            daily_high = max(daily_high, current_price)
            daily_low = min(daily_low, current_price)

        # Ensure price stays in reasonable range
        current_price = max(base_price * 0.5, min(base_price * 1.5, current_price))

        # Generate volume (higher during trading hours)
        base_volume = 80000000
        if 9 <= hour < 11:
            volume = random.randint(int(base_volume * 1.5), int(base_volume * 2.5))
        else:
            volume = random.randint(int(base_volume * 0.5), int(base_volume * 1.5))

        # Generate liquidity
        liquidity = random.randint(15000000, 40000000)

        data_points.append(
            {
                "timestamp": timestamp.timestamp(),
                "datetime": timestamp.isoformat(),
                "price": round(current_price, 4),
                "volume24h": volume,
                "liquidity": liquidity,
            }
        )

        timestamp += timedelta(minutes=interval_minutes)

    # Write to CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["timestamp", "datetime", "price", "volume24h", "liquidity"]
        )
        writer.writeheader()
        writer.writerows(data_points)

    print(f"✅ Generated {len(data_points)} data points")
    print(f"💾 Saved to: {output_file}")

    # Print statistics
    prices = [d["price"] for d in data_points]
    print(f"\n📈 Price Statistics:")
    print(f"   Min: ${min(prices):.2f}")
    print(f"   Max: ${max(prices):.2f}")
    print(f"   Avg: ${sum(prices) / len(prices):.2f}")
    print(
        f"   Trading windows: {sum(1 for d in data_points if 9 <= datetime.fromtimestamp(d['timestamp']).hour < 11)}"
    )

    return output_file


def generate_scenario_data(scenario: str, output_file: str = None):
    """
    Generate specific test scenarios

    Scenarios:
        - 'trending_up': Strong uptrend with pullbacks
        - 'trending_down': Downtrend with bounces
        - 'sideways': Range-bound market
        - 'volatile': High volatility chop
        - 'perfect_entry': Ideal entry setup sequence
    """
    if scenario == "trending_up":
        return generate_sample_data(
            days=1,
            base_price=140.0,
            volatility=0.01,
            output_file=output_file or "data/scenario_trending_up.csv",
        )
    elif scenario == "trending_down":
        return generate_sample_data(
            days=1,
            base_price=160.0,
            volatility=0.012,
            output_file=output_file or "data/scenario_trending_down.csv",
        )
    elif scenario == "sideways":
        return generate_sample_data(
            days=1,
            base_price=150.0,
            volatility=0.004,
            output_file=output_file or "data/scenario_sideways.csv",
        )
    elif scenario == "volatile":
        return generate_sample_data(
            days=1,
            base_price=150.0,
            volatility=0.02,
            output_file=output_file or "data/scenario_volatile.csv",
        )
    else:
        return generate_sample_data(output_file=output_file or "data/sample_price_data.csv")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate sample price data for simulation")
    parser.add_argument("--days", "-d", type=int, default=2, help="Number of days")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Interval in minutes")
    parser.add_argument(
        "--output", "-o", type=str, default="data/sample_price_data.csv", help="Output file"
    )
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        choices=["trending_up", "trending_down", "sideways", "volatile"],
        help="Generate specific scenario",
    )

    args = parser.parse_args()

    if args.scenario:
        generate_scenario_data(args.scenario, args.output)
    else:
        generate_sample_data(
            days=args.days,
            interval_minutes=args.interval,
            output_file=args.output,
        )

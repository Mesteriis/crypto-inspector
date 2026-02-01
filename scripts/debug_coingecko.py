#!/usr/bin/env python
"""Debug CoinGecko API responses."""

import asyncio
import sys

sys.path.insert(0, "src")

from core.http_client import get_coingecko_client


async def debug_markets():
    """Debug markets endpoint."""
    client = get_coingecko_client()

    # Test altseason query
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "90d",
    }

    print("Fetching /coins/markets with altseason params...")
    data = await client.get("/coins/markets", params=params)

    if data:
        print(f"Got {len(data)} coins")
        # Check for BTC
        btc = next((c for c in data if c["id"] == "bitcoin"), None)
        if btc:
            print(f"BTC found: price_change_90d={btc.get('price_change_percentage_90d_in_currency')}")

        # Check how many have 90d data
        with_90d = [c for c in data if c.get("price_change_percentage_90d_in_currency") is not None]
        print(f"Coins with 90d data: {len(with_90d)}")

        # Print first 5
        print("\nFirst 5 coins:")
        for c in data[:5]:
            print(f"  {c['symbol'].upper()}: 90d={c.get('price_change_percentage_90d_in_currency')}")
    else:
        print("No data returned!")


if __name__ == "__main__":
    asyncio.run(debug_markets())

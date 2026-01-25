#!/usr/bin/env python
"""Test the new CoinGecko client with retry and backoff."""

import asyncio
import sys

sys.path.insert(0, "src")

from service.analysis.altseason import AltseasonAnalyzer
from service.analysis.stablecoins import StablecoinAnalyzer


async def test_altseason():
    """Test altseason analyzer."""
    print("Testing Altseason Analyzer...")
    analyzer = AltseasonAnalyzer()
    try:
        result = await analyzer.analyze()
        print(f"  SUCCESS: index={result.index}, alts_analyzed={result.total_alts_analyzed}")
        print(f"  Status: {result.status.value}")
        print(f"  BTC 90d: {result.btc_performance_90d:.2f}%")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    finally:
        await analyzer.close()


async def test_stablecoins():
    """Test stablecoin analyzer."""
    print("\nTesting Stablecoin Analyzer...")
    analyzer = StablecoinAnalyzer()
    try:
        result = await analyzer.analyze()
        print(f"  SUCCESS: total={result.total_market_cap_formatted}, stablecoins={len(result.stablecoins)}")
        print(f"  Flow signal: {result.flow_signal.value}")
        print(f"  Dominance: {result.dominance:.2f}%")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False
    finally:
        await analyzer.close()


async def main():
    """Run all tests."""
    print("=" * 50)
    print("CoinGecko Client Test with Retry/Backoff")
    print("=" * 50)
    
    altseason_ok = await test_altseason()
    stablecoin_ok = await test_stablecoins()
    
    print("\n" + "=" * 50)
    print("Results:")
    print(f"  Altseason: {'PASS' if altseason_ok else 'FAIL'}")
    print(f"  Stablecoin: {'PASS' if stablecoin_ok else 'FAIL'}")
    print("=" * 50)
    
    return altseason_ok and stablecoin_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

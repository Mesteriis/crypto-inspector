"""
Centralized HTTP client with retry, backoff, and rate limiting.

All external API calls should use this client to handle:
- Rate limiting (429 errors)
- Server errors (5xx)
- Exponential backoff
- Request caching
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 5
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Maximum delay between retries
    exponential_base: float = 2.0  # Exponential backoff multiplier
    jitter: float = 0.1  # Random jitter factor (0-1)
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 30  # CoinGecko free tier: ~30/min
    min_request_interval: float = 2.0  # Minimum seconds between requests


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    data: Any
    expires_at: float


class ResilientHttpClient:
    """
    HTTP client with built-in retry, backoff, rate limiting, and caching.
    
    Features:
    - Exponential backoff on 429/5xx errors
    - Rate limiting to stay within API limits
    - Response caching to reduce API calls
    - Automatic retry with jitter
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        cache_ttl: int = 300,  # Cache for 5 minutes by default
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._retry_config = retry_config or RetryConfig()
        self._rate_limit_config = rate_limit_config or RateLimitConfig()
        self._cache_ttl = cache_ttl
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0
        self._cache: dict[str, CacheEntry] = {}
        self._request_count = 0
        self._rate_limit_window_start = time.time()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "crypto-inspect/1.0",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_cache_key(self, method: str, url: str, params: dict | None) -> str:
        """Generate cache key from request details."""
        params_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        return f"{method}:{url}?{params_str}"

    def _get_cached(self, cache_key: str) -> Any | None:
        """Get cached response if valid."""
        entry = self._cache.get(cache_key)
        if entry and time.time() < entry.expires_at:
            logger.debug(f"Cache hit: {cache_key[:50]}...")
            return entry.data
        return None

    def _set_cached(self, cache_key: str, data: Any, ttl: int | None = None) -> None:
        """Cache response data."""
        expires_at = time.time() + (ttl or self._cache_ttl)
        self._cache[cache_key] = CacheEntry(data=data, expires_at=expires_at)

    async def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Reset counter every minute
        if now - self._rate_limit_window_start > 60:
            self._request_count = 0
            self._rate_limit_window_start = now
        
        # Check if we've hit the rate limit
        if self._request_count >= self._rate_limit_config.requests_per_minute:
            wait_time = 60 - (now - self._rate_limit_window_start)
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._rate_limit_window_start = time.time()
        
        # Enforce minimum interval between requests
        elapsed = now - self._last_request_time
        if elapsed < self._rate_limit_config.min_request_interval:
            await asyncio.sleep(self._rate_limit_config.min_request_interval - elapsed)
        
        self._last_request_time = time.time()
        self._request_count += 1

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with jitter."""
        import random
        
        delay = min(
            self._retry_config.base_delay * (self._retry_config.exponential_base ** attempt),
            self._retry_config.max_delay,
        )
        
        # Add jitter
        jitter = delay * self._retry_config.jitter * random.random()
        return delay + jitter

    async def get(
        self,
        url: str,
        params: dict | None = None,
        use_cache: bool = True,
        cache_ttl: int | None = None,
    ) -> dict | list | None:
        """
        Make GET request with retry and caching.
        
        Args:
            url: URL to fetch
            params: Query parameters
            use_cache: Whether to use cached response
            cache_ttl: Custom cache TTL for this request
            
        Returns:
            JSON response or None on failure
        """
        cache_key = self._get_cache_key("GET", url, params)
        
        # Check cache first
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached
        
        client = await self._get_client()
        last_error: Exception | None = None
        
        for attempt in range(self._retry_config.max_retries):
            try:
                # Respect rate limits
                await self._wait_for_rate_limit()
                
                response = await client.get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    backoff = max(self._calculate_backoff(attempt), retry_after)
                    logger.warning(
                        f"Rate limited (429) on {url}, attempt {attempt + 1}/{self._retry_config.max_retries}, "
                        f"waiting {backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)
                    continue
                
                # Handle server errors
                if response.status_code in self._retry_config.retry_on_status:
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Server error {response.status_code} on {url}, attempt {attempt + 1}/{self._retry_config.max_retries}, "
                        f"waiting {backoff:.1f}s"
                    )
                    await asyncio.sleep(backoff)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Cache successful response
                if use_cache:
                    self._set_cached(cache_key, data, cache_ttl)
                
                return data
                
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code not in self._retry_config.retry_on_status:
                    logger.error(f"HTTP error {e.response.status_code} on {url}: {e}")
                    raise
            except httpx.TimeoutException as e:
                last_error = e
                backoff = self._calculate_backoff(attempt)
                logger.warning(f"Timeout on {url}, attempt {attempt + 1}, waiting {backoff:.1f}s")
                await asyncio.sleep(backoff)
            except httpx.ConnectError as e:
                # DNS resolution failures, connection refused, etc.
                last_error = e
                backoff = self._calculate_backoff(attempt)
                logger.warning(
                    f"Connection error on {url}, attempt {attempt + 1}/{self._retry_config.max_retries}, "
                    f"waiting {backoff:.1f}s: {e}"
                )
                await asyncio.sleep(backoff)
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on {url}: {e}")
                raise
        
        # All retries exhausted
        logger.error(f"All {self._retry_config.max_retries} retries exhausted for {url}")
        if last_error:
            raise last_error
        return None

    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()

    def invalidate_cache(self, pattern: str = "") -> int:
        """Invalidate cache entries matching pattern."""
        keys_to_remove = [k for k in self._cache if pattern in k]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)


# CoinGecko-specific client with appropriate rate limits
class CoinGeckoClient(ResilientHttpClient):
    """
    CoinGecko API client with proper rate limiting.
    
    Free tier limits:
    - 10-30 requests per minute
    - No API key required
    """
    
    def __init__(self):
        super().__init__(
            base_url="https://api.coingecko.com/api/v3",
            timeout=30.0,
            retry_config=RetryConfig(
                max_retries=5,
                base_delay=2.0,  # Start with 2s delay
                max_delay=120.0,  # Up to 2 minutes
                exponential_base=2.0,
            ),
            rate_limit_config=RateLimitConfig(
                requests_per_minute=10,  # Conservative for free tier
                min_request_interval=6.0,  # ~10 requests per minute
            ),
            cache_ttl=300,  # 5 minute cache
        )


# Global instances
_coingecko_client: CoinGeckoClient | None = None


def get_coingecko_client() -> CoinGeckoClient:
    """Get global CoinGecko client instance."""
    global _coingecko_client
    if _coingecko_client is None:
        _coingecko_client = CoinGeckoClient()
    return _coingecko_client


async def close_all_clients() -> None:
    """Close all global HTTP clients."""
    global _coingecko_client
    if _coingecko_client:
        await _coingecko_client.close()
        _coingecko_client = None

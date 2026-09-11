"""
BHOOMI NEXUS - OSINT / Public-Source Land Intelligence
Rate Limiting & Domain Throttler

Enforces strict request pacing and backoff policies per external target domain
to comply with government portal terms of service, robots.txt, and fair use limits.
"""

import time
import threading
from typing import Dict, Tuple


class TokenBucketLimiter:
    """
    Thread-safe token bucket rate limiter for external OSINT domains.
    Default: max 10 requests per minute per domain, refill rate 1 token per 6 seconds.
    """

    def __init__(self, rate_per_minute: int = 10, burst_limit: int = 5):
        self.capacity = burst_limit
        self.tokens = float(burst_limit)
        self.refill_rate = rate_per_minute / 60.0  # tokens per second
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> Tuple[bool, float]:
        """
        Attempts to acquire tokens.
        Returns: (success, retry_after_seconds)
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Refill tokens up to capacity
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                deficit = tokens - self.tokens
                retry_after = deficit / self.refill_rate if self.refill_rate > 0 else 60.0
                return False, retry_after


class OSINTRateLimiter:
    """
    Domain-level and client-level rate limiter manager.
    """

    def __init__(self):
        self._domain_limiters: Dict[str, TokenBucketLimiter] = {}
        self._lock = threading.Lock()
        # Default limits per domain category
        self.default_rate_per_min = 10
        self.default_burst = 3

    def get_limiter_for_domain(self, domain: str) -> TokenBucketLimiter:
        with self._lock:
            if domain not in self._domain_limiters:
                # Sensitive domains get stricter pacing
                rate = 5 if ("gov.in" in domain or "nic.in" in domain) else self.default_rate_per_min
                burst = 2 if ("gov.in" in domain or "nic.in" in domain) else self.default_burst
                self._domain_limiters[domain] = TokenBucketLimiter(rate_per_minute=rate, burst_limit=burst)
            return self._domain_limiters[domain]

    def check_rate_limit(self, domain: str) -> Tuple[bool, float]:
        """
        Checks if a request to `domain` is permitted right now.
        Returns: (allowed, retry_after_seconds)
        """
        limiter = self.get_limiter_for_domain(domain)
        return limiter.acquire(1.0)


# Global singleton rate limiter instance
osint_rate_limiter = OSINTRateLimiter()

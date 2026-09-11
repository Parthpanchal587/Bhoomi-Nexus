"""
BHOOMI-NEXUS: Security Middleware Layer.

Components:
1. SecurityHeadersMiddleware:
   - Injects Content-Security-Policy (CSP), X-Frame-Options, X-Content-Type-Options,
     Strict-Transport-Security (HSTS), Referrer-Policy, and Permissions-Policy.
   - Strips revealing Server and X-Powered-By headers.
2. RateLimiterMiddleware:
   - Thread-safe in-memory sliding-window token bucket per client IP.
   - Separate strict quotas for authentication, document processing, and AI queries.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces defense-in-depth HTTP security headers on all responses."""

    CSP_POLICY = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data: blob:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https: http://127.0.0.1:8000 http://localhost:8000 https://bhoomi-nexus.vercel.app; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Standard Defensive Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=(), payment=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = self.CSP_POLICY

        # Remove information-disclosure headers
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window IP rate limiter protecting against brute-force attacks,
    denial of service, and resource exhaustion on sensitive endpoints.
    """

    # Quotas: (max_requests, window_seconds)
    ROUTE_LIMITS: List[Tuple[str, int, int]] = [
        ("/api/v1/auth/login", 10, 60),       # Max 10 login attempts per minute per IP
        ("/api/v1/documents", 30, 60),        # Max 30 document operations per minute per IP
        ("/api/ai", 40, 60),                  # Max 40 AI queries per minute per IP
        ("/api/blockchain/notarize", 20, 60), # Max 20 notarizations per minute per IP
        ("/api", 150, 60),                    # Global API: 150 requests per minute per IP
    ]

    def __init__(self, app):
        super().__init__(app)
        self._ip_history: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Whitelist health checks and static files from rate limiting
        if path.startswith(("/static", "/ashoka_stambh", "/india_mask", "/favicon.ico")) or path in ("/api/health", "/api/v1/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Check rate limits
        for prefix, max_reqs, window_sec in self.ROUTE_LIMITS:
            if path.startswith(prefix):
                with self._lock:
                    history = self._ip_history[client_ip][prefix]
                    # Filter out timestamps older than the window
                    cutoff = now - window_sec
                    self._ip_history[client_ip][prefix] = [t for t in history if t > cutoff]
                    current_count = len(self._ip_history[client_ip][prefix])

                    if current_count >= max_reqs:
                        retry_after = int(window_sec - (now - self._ip_history[client_ip][prefix][0]))
                        return JSONResponse(
                            status_code=429,
                            content={
                                "error": "RATE_LIMIT_EXCEEDED",
                                "message": f"Too many requests to {prefix}. Security rate limit exceeded.",
                                "retry_after_seconds": max(1, retry_after),
                                "client_ip": client_ip,
                            },
                            headers={"Retry-After": str(max(1, retry_after))},
                        )

                    # Record current request timestamp
                    self._ip_history[client_ip][prefix].append(now)
                break  # Matched the most specific route prefix

        return await call_next(request)

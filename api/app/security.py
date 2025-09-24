"""
Security middleware for API authentication and authorization
"""

import os
from typing import Optional, List
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import hashlib
import hmac
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# API Key configurations
API_KEY_NAME = "X-API-Key"
API_KEY_QUERY_NAME = "api_key"

# Environment variable for API keys (comma-separated list)
VALID_API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Optional: Use a more secure key storage in production
# For development, we can use a default key if none are set
if not VALID_API_KEYS:
    # In development mode, allow a default test key
    if os.getenv("ENVIRONMENT", "development") == "development":
        VALID_API_KEYS = ["dev-test-key-123"]
        logger.warning("Using default development API key. Set API_KEYS environment variable in production!")

# Header and query parameter extractors
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name=API_KEY_QUERY_NAME, auto_error=False)


async def get_api_key(
    api_key_from_header: Optional[str] = Security(api_key_header),
    api_key_from_query: Optional[str] = Security(api_key_query)
) -> str:
    """
    Validate and return API key from header or query parameter
    """
    # Check header first, then query parameter
    api_key = api_key_from_header or api_key_from_query

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Provide via X-API-Key header or api_key query parameter",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Validate API key
    if not is_valid_api_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return api_key


def is_valid_api_key(api_key: str) -> bool:
    """
    Check if API key is valid
    In production, this should check against a database or secure store
    """
    if not VALID_API_KEYS:
        return False

    # Use constant-time comparison to prevent timing attacks
    for valid_key in VALID_API_KEYS:
        if hmac.compare_digest(api_key, valid_key):
            return True

    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication on all endpoints
    """

    def __init__(self, app, excluded_paths: List[str] = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.excluded_paths = excluded_paths or [
            "/",  # Health check
            "/docs",  # API documentation
            "/openapi.json",  # OpenAPI spec
            "/redoc",  # ReDoc documentation
            "/favicon.ico",
            "/ws/",  # WebSocket connections (handled separately)
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        path = request.url.path

        # Check if path is excluded
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return await call_next(request)

        # Get API key from header or query
        api_key = None

        # Check header
        if API_KEY_NAME in request.headers:
            api_key = request.headers[API_KEY_NAME]
        # Check query parameters
        elif API_KEY_QUERY_NAME in request.query_params:
            api_key = request.query_params[API_KEY_QUERY_NAME]

        # Validate API key
        if not api_key:
            return Response(
                content='{"detail": "API Key required"}',
                status_code=401,
                headers={"WWW-Authenticate": "ApiKey", "Content-Type": "application/json"}
            )

        if not is_valid_api_key(api_key):
            return Response(
                content='{"detail": "Invalid API Key"}',
                status_code=403,
                headers={"WWW-Authenticate": "ApiKey", "Content-Type": "application/json"}
            )

        # Store API key in request state for logging/auditing
        request.state.api_key = api_key

        # Continue with request
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware based on API key or IP
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # Track requests by key/IP
        self.window_start = time.time()

    async def dispatch(self, request: Request, call_next):
        # Get identifier (API key or IP)
        identifier = getattr(request.state, "api_key", None) or request.client.host

        # Check and update rate limit
        current_time = time.time()

        # Reset window every minute
        if current_time - self.window_start > 60:
            self.request_counts = {}
            self.window_start = current_time

        # Check rate limit
        if identifier in self.request_counts:
            if self.request_counts[identifier] >= self.requests_per_minute:
                return Response(
                    content='{"detail": "Rate limit exceeded. Try again later."}',
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(self.window_start + 60)),
                        "Retry-After": str(int(60 - (current_time - self.window_start))),
                        "Content-Type": "application/json"
                    }
                )
            self.request_counts[identifier] += 1
        else:
            self.request_counts[identifier] = 1

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - self.request_counts[identifier]
        )
        response.headers["X-RateLimit-Reset"] = str(int(self.window_start + 60))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to responses
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


def setup_security(app, enable_api_key: bool = True, enable_rate_limit: bool = True):
    """
    Setup all security middleware for the application
    """
    # Add security headers (always enabled)
    app.add_middleware(SecurityHeadersMiddleware)

    # Add rate limiting if enabled
    if enable_rate_limit:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        )

    # Add API key authentication if enabled
    if enable_api_key and os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true":
        app.add_middleware(
            APIKeyMiddleware,
            excluded_paths=[
                "/",
                "/docs",
                "/openapi.json",
                "/redoc",
                "/favicon.ico",
                "/supported-configurations",  # Allow public access to configurations
                "/datasets",  # Allow browsing datasets
                "/example-data",  # Allow viewing example data info
            ]
        )
        logger.info("API Key authentication enabled")
    else:
        logger.info("API Key authentication disabled (set ENABLE_API_KEY_AUTH=true to enable)")
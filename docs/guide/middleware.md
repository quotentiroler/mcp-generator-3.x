# Middleware

Every generated server includes a configurable middleware stack built on FastMCP 3.x's native middleware pipeline.

## Default Middleware Stack

The following middleware is always included:

```
Request → Error Handling → Authentication → Timing → Logging → Tool Execution
```

```python
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from middleware.authentication import ApiClientContextMiddleware

middleware = [
    ErrorHandlingMiddleware(),
    ApiClientContextMiddleware(transport_mode="http", validate_tokens=False),
    DetailedTimingMiddleware(),
    LoggingMiddleware(),
]
```

### Error Handling

Catches all exceptions during tool execution and returns structured error responses. Prevents unhandled exceptions from crashing the server.

### Authentication

The `ApiClientContextMiddleware` handles:

- **STDIO mode** — forwards `BACKEND_API_TOKEN` to the backend API
- **HTTP mode** — optionally validates JWT tokens via JWKS
- **Identity injection** — makes authenticated user context available to tools

### Timing

`DetailedTimingMiddleware` tracks execution duration for every tool call. Useful for identifying slow operations and setting up monitoring.

### Logging

`LoggingMiddleware` provides structured request/response logging for observability.

## Optional Middleware

### Response Caching

Enable with `--enable-storage --enable-caching`:

```bash
uv run generate-mcp --enable-storage --enable-caching
```

Caches API responses with configurable TTL. Reduces backend API calls for rate-limited or expensive endpoints.

### Storage Backend

Enable with `--enable-storage`:

```bash
uv run generate-mcp --enable-storage
```

A persistent storage backend for:

- OAuth refresh tokens
- Session state
- User preferences
- Cache persistence

## Customizing Middleware

The generated middleware files are meant to be customized. Edit `middleware/authentication.py` directly to add custom logic, additional validation, or domain-specific middleware.

# Configuration

## Tool Name Customization

Edit `mcp_generator/config.py` to control how tool names are generated:

```python
# Abbreviations for long names
TOOL_NAME_ABBREVIATIONS = {
    'healthcare': 'hc',
    'organization': 'org',
}

# Complete overrides
TOOL_NAME_OVERRIDES = {
    'list_healthcare_users_by_role': 'list_users_by_role',
    'create_smart_app_registration': 'register_smart_app',
}

# Maximum tool name length (MCP/OpenAI limit)
MAX_TOOL_NAME_LENGTH = 64
```

## FastMCP Configuration

Each generated server includes a `fastmcp.json` with comprehensive feature configuration:

```json
{
  "composition": {
    "strategy": "mount",
    "resource_prefix_format": "path"
  },
  "middleware": {
    "config": {
      "authentication": {
        "validate_tokens": false
      }
    }
  },
  "features": {
    "tool_tags": true,
    "tool_timeouts": {
      "enabled": true,
      "default_seconds": 30
    },
    "search_tools": {
      "enabled": false,
      "description": "BM25 text search over tool catalog for large servers"
    },
    "code_mode": {
      "enabled": false,
      "description": "Experimental meta-tool transform (search → inspect → execute)"
    },
    "response_limiting": {
      "enabled": true,
      "max_size_bytes": 1048576
    },
    "ping_middleware": {
      "enabled": true
    },
    "multi_auth": {
      "enabled": false,
      "providers": []
    },
    "component_versioning": {
      "enabled": true
    },
    "validate_output": false,
    "dynamic_visibility": {
      "enabled": false
    },
    "opentelemetry": {
      "enabled": false,
      "service_name": "your-api-mcp"
    }
  }
}
```

### Feature Reference

| Feature | Default | Description |
|---|---|---|
| `tool_tags` | `true` | Automatic per-module tag grouping |
| `tool_timeouts.enabled` | `true` | Per-tool timeout enforcement |
| `tool_timeouts.default_seconds` | `30` | Default timeout for all tools |
| `search_tools.enabled` | `false` | BM25 text search over tool catalog |
| `code_mode.enabled` | `false` | Experimental meta-tool transform |
| `response_limiting.enabled` | `true` | UTF-8-safe response truncation |
| `response_limiting.max_size_bytes` | `1048576` | Max response size (1MB) |
| `ping_middleware.enabled` | `true` | HTTP keepalive for long connections |
| `multi_auth.enabled` | `false` | Compose multiple token verifiers |
| `component_versioning.enabled` | `true` | Deprecated endpoint annotations |
| `validate_output` | `false` | FastMCP output validation |
| `dynamic_visibility.enabled` | `false` | Per-session component toggling |
| `opentelemetry.enabled` | `false` | OpenTelemetry tracing |

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `API_TOKEN` | Token forwarded to the backend API | For authenticated APIs |
| `JWKS_URI` | Override JWKS endpoint for JWT validation | No (auto-discovered) |
| `JWT_ISSUER` | Override JWT issuer claim | No (auto-discovered) |
| `JWT_AUDIENCE` | Override JWT audience claim | No (auto-discovered) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry OTLP exporter endpoint | No (uses console) |

## Code Quality

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type checking
uv run mypy mcp_generator/

# Run tests
uv run pytest
```

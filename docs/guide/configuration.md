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

Each generated server includes a `fastmcp.json`:

```json
{
  "name": "Swagger Petstore OpenAPI",
  "version": "1.0.0",
  "description": "MCP server for Swagger Petstore OpenAPI",
  "middleware": {
    "config": {
      "authentication": {
        "validate_tokens": false,
        "backend_url": "https://petstore3.swagger.io/api/v3"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `BACKEND_API_TOKEN` | Token forwarded to the backend API | For authenticated APIs |
| `JWKS_URI` | Override JWKS endpoint for JWT validation | No (auto-discovered) |
| `JWT_ISSUER` | Override JWT issuer claim | No (auto-discovered) |
| `JWT_AUDIENCE` | Override JWT audience claim | No (auto-discovered) |

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

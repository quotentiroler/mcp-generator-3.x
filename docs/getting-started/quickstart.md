# Quick Start

Generate a fully-functional MCP server from an OpenAPI spec in under a minute.

## 0. Install

```bash
pip install mcp-generator
```

## 1. Generate

=== "Local file"

    ```bash
    # Default: reads ./openapi.json
    generate-mcp

    # Or specify a file
    generate-mcp --file ./my-api-spec.yaml
    ```

=== "From URL"

    ```bash
    generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json
    ```

**What gets generated:**

- :white_check_mark: Python API client from the OpenAPI spec
- :white_check_mark: Modular MCP server modules (one per API tag)
- :white_check_mark: Authentication middleware
- :white_check_mark: OAuth2 provider (if spec contains OAuth2 security schemes)
- :white_check_mark: Package files, tests, and Docker configuration
- :white_check_mark: Everything outputs to `generated_mcp/`

### Optional Features

By default, the generator creates a minimal, production-ready server. Enable additional features as needed:

```bash
# Enable persistent storage (for OAuth tokens, session state)
generate-mcp --enable-storage

# Enable response caching (reduces backend API calls)
generate-mcp --enable-storage --enable-caching

# Enable MCP resources (expose GET endpoints as MCP resources)
generate-mcp --enable-resources

# Enable all features
generate-mcp --enable-storage --enable-caching --enable-resources
```

| Flag | Description | When to Use |
|---|---|---|
| `--enable-storage` | Persistent storage backend | OAuth refresh tokens, session data |
| `--enable-caching` | Response caching with TTL | Rate-limited APIs, slow endpoints |
| `--enable-resources` | MCP resource templates | Expose API data for context/retrieval |

!!! note
    `--enable-caching` requires `--enable-storage` as it uses the storage backend for cache persistence.

## 2. Register

```bash
# Register the generated server
register-mcp ./generated_mcp

# Verify registration
run-mcp --list
```

This adds your server to the local registry at `~/.mcp-generator/servers.json`.

## 3. Run

=== "STDIO (local AI clients)"

    ```bash
    export BACKEND_API_TOKEN="your-api-token-here"
    run-mcp swagger_petstore_openapi
    ```

=== "HTTP (network)"

    ```bash
    run-mcp swagger_petstore_openapi --mode http --port 8000
    ```

=== "Direct Python"

    ```bash
    cd generated_mcp
    python swagger_petstore_openapi_mcp_generated.py --transport stdio
    ```

=== "FastMCP CLI"

    ```bash
    cd generated_mcp
    uv run fastmcp run swagger_petstore_openapi_mcp_generated.py:create_server
    # Or with config:
    uv run fastmcp run fastmcp.json
    ```

## 4. Connect to AI Clients

### Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": ["/path/to/generated_mcp/swagger_petstore_openapi_mcp_generated.py"],
      "env": {
        "BACKEND_API_TOKEN": "your-api-token-here"
      }
    }
  }
}
```

### HTTP Mode

Any MCP-compatible client can connect to:

```
http://localhost:8000/mcp
```

## Next Steps

- [Architecture](../guide/architecture.md) — understand the generated code structure
- [CLI Reference](../guide/cli.md) — full command documentation
- [Authentication](../guide/authentication.md) — JWT, OAuth2, and token validation

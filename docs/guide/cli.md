# CLI Reference

MCP Generator installs three CLI commands.

## generate-mcp

Generate a FastMCP 3.x server from an OpenAPI spec.

```bash
uv run generate-mcp [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--file <path>` | `./openapi.json` | Path to OpenAPI spec file (JSON or YAML) |
| `--url <url>` | — | Download spec from URL (overrides `--file`) |
| `--enable-storage` | off | Enable persistent storage backend |
| `--enable-caching` | off | Enable response caching (requires `--enable-storage`) |
| `--enable-resources` | off | Expose GET endpoints as MCP resources |

### Examples

```bash
# Local file (default)
uv run generate-mcp

# Custom file
uv run generate-mcp --file ./my-api.yaml

# From URL
uv run generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# All features enabled
uv run generate-mcp --url https://example.com/api.json \
  --enable-storage --enable-caching --enable-resources
```

---

## register-mcp

Manage the local server registry at `~/.mcp-generator/servers.json`.

```bash
uv run register-mcp <COMMAND> [OPTIONS]
```

### Commands

| Command | Description |
|---|---|
| `add <path>` | Register a generated server (default when a path is given) |
| `list` | Show all registered servers |
| `remove <name>` | Unregister a server by name |
| `export <name>` | Export server metadata as `server.json` |

### Options

| Option | Command | Description |
|---|---|---|
| `--json` | `list` | Output as JSON for scripting |
| `-o, --output <file>` | `export` | Write to file (default: stdout) |

### Examples

```bash
# Register (explicit)
uv run register-mcp add ./generated_mcp

# Register (shorthand)
uv run register-mcp ./generated_mcp

# List registered servers
uv run register-mcp list

# List as JSON
uv run register-mcp list --json

# Remove
uv run register-mcp remove swagger_petstore_openapi

# Export metadata
uv run register-mcp export swagger_petstore_openapi -o server.json
```

---

## run-mcp

Run a registered server by name.

```bash
uv run run-mcp <SERVER_NAME> [OPTIONS]
```

### Options

| Option | Default | Description |
|---|---|---|
| `--list` | — | List registered servers and exit |
| `--mode` / `--transport` | `stdio` | Transport mode: `stdio` or `http` |
| `--host` | `0.0.0.0` | HTTP host |
| `--port` | `8000` | HTTP port |
| `--validate-tokens` | off | Enable JWT validation (HTTP mode) |

### Examples

```bash
# List servers
uv run run-mcp --list

# Run via STDIO
export BACKEND_API_TOKEN="your-token"
uv run run-mcp swagger_petstore_openapi

# Run via HTTP
uv run run-mcp swagger_petstore_openapi --mode http --port 8000

# HTTP with JWT validation
uv run run-mcp swagger_petstore_openapi --mode http --port 8000 --validate-tokens
```

### Notes

- The registry lives at `~/.mcp-generator/servers.json`
- `run-mcp` forwards flags to the generated server's entry point
- You can also run the generated script directly: `python <name>_mcp_generated.py`

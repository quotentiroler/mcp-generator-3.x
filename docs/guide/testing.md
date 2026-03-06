# Testing

MCP Generator creates auto-generated test suites and supports the official MCP Inspector for interactive debugging.

## Auto-Generated Tests

Every generated server includes test files that verify tool discovery, execution, and resource availability.

```bash
cd examples/petstore
uv run python test/run_tests.py
```

The test runner:

1. Starts the generated server on a random port
2. Connects via the MCP client
3. Calls `tools/list` to verify all tools are registered
4. Executes sample tool calls
5. Reports results

## MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official debugging tool for MCP servers.

### Quick Start

```bash
cd generated_mcp

# Interactive UI (recommended for development)
uv run fastmcp dev swagger_petstore_openapi_mcp_generated.py:create_server

# Or with the Inspector directly
npx @modelcontextprotocol/inspector python swagger_petstore_openapi_mcp_generated.py
```

The Inspector opens a browser UI at `http://localhost:6274` where you can:

- :material-hammer-wrench: **List and test all tools** with interactive parameter forms
- :material-package-variant: **Browse resources** hierarchically
- :material-chat: **Test prompts** with streaming visualization
- :material-bug: **Debug** with request/response history and timing

!!! tip
    When using `fastmcp dev` or `fastmcp run`, always include `:create_server` to properly compose the modular architecture.

### CLI Mode

For CI/CD and scripting:

```bash
# List tools
npx @modelcontextprotocol/inspector --cli \
  python swagger_petstore_openapi_mcp_generated.py \
  --method tools/list

# Call a tool
npx @modelcontextprotocol/inspector --cli \
  python swagger_petstore_openapi_mcp_generated.py \
  --method tools/call \
  --tool-name create_pet \
  --tool-arg 'name=Fluffy' \
  --tool-arg 'status=available'
```

### Testing HTTP Transport

```bash
# Start server in HTTP mode
python swagger_petstore_openapi_mcp_generated.py --transport http --port 8000

# Connect Inspector via Streamable HTTP
npx @modelcontextprotocol/inspector http://localhost:8000/mcp --transport http
```

## Unit Tests

Run the generator's own test suite:

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=mcp_generator

# Specific test
uv run pytest test/test_generator.py -v
```

## Example Tests

Run the pre-built example tests:

```bash
# Run all example tests
uv run python scripts/test_examples.py

# Or individually
cd examples/petstore
uv run python test/run_tests.py
```

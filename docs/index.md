---
hide:
  - navigation
---

# MCP Generator 3.x

**Transform any OpenAPI specification into a production-ready [FastMCP 3.x](https://github.com/PrefectHQ/fastmcp) server.**

[![GitHub Release](https://img.shields.io/github/v/release/quotentiroler/mcp-generator-3.x?include_prereleases&label=version)](https://github.com/quotentiroler/mcp-generator-3.x/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-v3.11-3776ab.svg)](https://www.python.org/downloads/)
[![FastMCP 3.x](https://img.shields.io/badge/FastMCP-3.x-green.svg)](https://github.com/PrefectHQ/fastmcp)

---

## What is MCP Generator?

MCP Generator automatically creates **modular, composable MCP servers** from OpenAPI 3.0.x, 3.1.x, and Swagger 2.0 specifications. It bridges REST APIs and AI agents by generating fully-functional MCP tools that AI assistants like Claude, ChatGPT, and others can use to interact with your APIs.

## Key Features

<div class="grid cards" markdown>

-   :material-view-module:{ .lg .middle } **Modular Architecture**

    ---

    One sub-server per API tag — composable, scalable, and organized.

-   :material-shield-lock:{ .lg .middle } **Enterprise Auth**

    ---

    JWT/JWKS validation, OAuth2 flows, scope enforcement — all generated automatically.

-   :material-layers:{ .lg .middle } **Middleware Stack**

    ---

    Timing, logging, caching, error handling — full FastMCP 3.x middleware pipeline.

-   :material-test-tube:{ .lg .middle } **Auto-Generated Tests**

    ---

    Test suites generated alongside your server — ready to run out of the box.

-   :material-docker:{ .lg .middle } **Docker Ready**

    ---

    Dockerfile and docker-compose generated for instant containerized deployment.

-   :material-language-python:{ .lg .middle } **Pure Python**

    ---

    Zero external runtime dependencies — no Java, no Node.js, just Python.

</div>

## Quick Example

```bash
# Install
git clone https://github.com/quotentiroler/mcp-generator-3.x.git
cd mcp-generator-3.x && uv sync

# Generate from any OpenAPI spec
uv run generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

# Run it
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py --transport http --port 8000
```

That's it — a fully functional MCP server with 19 tools, modular sub-servers, authentication middleware, and auto-generated tests.

## Supported Specs

| Format | Status |
|---|---|
| OpenAPI 3.0.x | :white_check_mark: Fully supported |
| OpenAPI 3.1.x | :white_check_mark: Fully supported |
| Swagger 2.0 | :white_check_mark: Fully supported |
| JSON | :white_check_mark: |
| YAML | :white_check_mark: |

## Next Steps

- [**Installation**](getting-started/installation.md) — set up the generator in 2 minutes
- [**Quick Start**](getting-started/quickstart.md) — generate your first MCP server
- [**Architecture**](guide/architecture.md) — understand the generated code structure
- [**Comparison**](comparison.md) — see how we compare to alternatives

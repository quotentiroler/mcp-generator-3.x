# Installation

## Prerequisites

- **Python 3.11+** — required for modern type hints and features
- **uv** (recommended) or **pip** — for dependency management
- **OpenAPI Specification** — your API's OpenAPI 3.0.x, 3.1.x, or Swagger 2.0 spec (JSON or YAML)

!!! note "Pure Python"
    MCP Generator is 100% Python — no Java, Node.js, or other runtimes needed.

## Install with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/quotentiroler/mcp-generator-3.x.git
cd mcp-generator-3.x

# Install dependencies
uv sync

# Verify installation
uv run generate-mcp --help
```

## Install with pip

```bash
# Clone the repository
git clone https://github.com/quotentiroler/mcp-generator-3.x.git
cd mcp-generator-3.x

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
generate-mcp --help
```

## Verify Installation

You should see output similar to:

```
usage: generate-mcp [-h] [--file FILE] [--url URL] [--enable-storage]
                    [--enable-caching] [--enable-resources]
...
```

## Next Steps

Head to the [Quick Start](quickstart.md) to generate your first MCP server.

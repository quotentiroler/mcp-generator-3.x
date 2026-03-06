# Authentication

MCP Generator automatically generates authentication support based on your OpenAPI spec's security schemes.

## Overview

```mermaid
flowchart LR
    A[Client Request] --> B{Transport?}
    B -->|STDIO| C[Backend Token Forwarding]
    B -->|HTTP| D{validate-tokens?}
    D -->|Yes| E[JWT/JWKS Validation]
    D -->|No| C
    E --> F[Scope Enforcement]
    F --> G[Tool Execution]
    C --> G
```

## Backend Token Forwarding (Default)

By default, the generated server forwards the `BACKEND_API_TOKEN` environment variable to the backend API. This is the simplest setup:

```bash
export BACKEND_API_TOKEN="your-api-token-here"
python server_mcp_generated.py --transport stdio
```

The token is attached to every outbound API request as a Bearer token.

## JWT Validation

When `--validate-tokens` is enabled, the server validates incoming JWT tokens at the HTTP layer:

1. **Token Extraction** — extracts JWT from `Authorization: Bearer <token>` header
2. **JWKS Discovery** — auto-discovers JWKS endpoint from OpenAPI spec or `{backend_url}/.well-known/jwks.json`
3. **Signature Verification** — validates JWT signature using the public key
4. **Claims Validation** — checks expiration, issuer, audience
5. **Scope Enforcement** — verifies required scopes per operation
6. **Identity Injection** — makes user identity available to tools

### Configuration

JWT configuration is **automatically extracted** from your OpenAPI specification during generation:

| Setting | Source | Default |
|---|---|---|
| JWKS URI | OpenAPI security scheme | `{backend_url}/.well-known/jwks.json` |
| Issuer | OpenAPI security scheme | `{backend_url}` |
| Audience | OpenAPI security scheme | `backend-api` |

### Enable at Runtime

```bash
python server_mcp_generated.py --transport http --validate-tokens
```

Or set as default in `fastmcp.json`:

```json
{
  "middleware": {
    "config": {
      "authentication": {
        "validate_tokens": true
      }
    }
  }
}
```

!!! note
    All JWT configuration is baked into the generated code — no environment variables needed.

## OAuth2 Support

When your OpenAPI spec contains OAuth2 security schemes, the generator automatically creates an OAuth2 provider.

### Supported Flows

- **Implicit** flow
- **Authorization Code** flow
- **Client Credentials** flow
- **Password** flow

### Features

- Scope extraction and validation from the OpenAPI spec
- Token introspection
- JWKS-based JWT verification
- Scope enforcement middleware

## Testing Authentication

### Generate a Test Keypair

```bash
uv run python scripts/generate_jwt_keypair.py
```

This generates an RSA keypair for local JWT testing.

### Test with MCP Inspector

```bash
# Without validation
npx @modelcontextprotocol/inspector python server_mcp_generated.py

# With token
npx @modelcontextprotocol/inspector \
  -e BACKEND_API_TOKEN=your-token \
  python server_mcp_generated.py
```

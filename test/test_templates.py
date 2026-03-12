"""Tests for generated template code — FastMCP 3.x compliance."""

import re

import pytest

from mcp_generator.models import OAuthConfig, OAuthFlowConfig, SecurityConfig
from mcp_generator.templates.authentication import generate_authentication_middleware
from mcp_generator.templates.event_store import generate_event_store
from mcp_generator.templates.oauth_provider import generate_oauth_provider

# ---------------------------------------------------------------------------
# Authentication template
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_code() -> str:
    from mcp_generator.models import ApiMetadata

    meta = ApiMetadata(
        title="Test",
        version="1.0.0",
        servers=[{"url": "http://localhost:3001"}],
    )
    sc = SecurityConfig(
        schemes={"bearerAuth": {"type": "http", "scheme": "bearer"}},
        oauth_config=OAuthConfig(
            scheme_name="oauth2",
            flows={
                "clientCredentials": OAuthFlowConfig(
                    token_url="https://auth.example.com/token",
                    scopes={"read": "Read"},
                )
            },
            all_scopes={"read": "Read"},
        ),
        jwks_uri="https://auth.example.com/.well-known/jwks.json",
        issuer="https://auth.example.com",
        audience="backend-api",
    )
    return generate_authentication_middleware(meta, sc)


class TestAuthenticationTemplate:
    def test_set_state_is_async(self, auth_code: str) -> None:
        """FastMCP 3.x: set_state must be awaited."""
        # Every call to set_state should be preceded by 'await'
        set_state_calls = re.findall(r"(?:await\s+)?fastmcp_ctx\.set_state\(", auth_code)
        for call in set_state_calls:
            assert call.startswith("await"), f"set_state call not awaited: {call!r}"

    def test_openapi_client_serializable_false(self, auth_code: str) -> None:
        """Non-JSON objects need serializable=False in FastMCP 3.x."""
        assert "serializable=False" in auth_code

    def test_contains_api_client_middleware(self, auth_code: str) -> None:
        assert "class ApiClientContextMiddleware" in auth_code


# ---------------------------------------------------------------------------
# EventStore template
# ---------------------------------------------------------------------------


class TestEventStoreTemplate:
    def test_generates_code(self) -> None:
        code = generate_event_store()
        assert isinstance(code, str)
        assert "class InMemoryEventStore" in code

    def test_imports_from_fastmcp_3x(self) -> None:
        code = generate_event_store()
        assert "fastmcp.server.event_store" in code

    def test_has_store_event_method(self) -> None:
        code = generate_event_store()
        assert "async def store_event" in code

    def test_has_replay_events_method(self) -> None:
        code = generate_event_store()
        assert "async def replay_events_after" in code

    def test_has_cleanup_stream(self) -> None:
        code = generate_event_store()
        assert "def cleanup_stream" in code

    def test_imports_streamid_and_eventid_types(self) -> None:
        code = generate_event_store()
        for type_name in ("EventCallback", "EventId", "EventMessage", "StreamId"):
            assert type_name in code, f"Missing import for {type_name}"


# ---------------------------------------------------------------------------
# Authentication template — Dynamic component visibility (FastMCP 3.0)
# ---------------------------------------------------------------------------


class TestAuthenticationDynamicVisibility:
    def test_dynamic_visibility_block_present(self, auth_code: str) -> None:
        """Dynamic component visibility code should be in auth middleware."""
        assert "enable_components" in auth_code or "disable_components" in auth_code

    def test_dynamic_visibility_scope_based(self, auth_code: str) -> None:
        """Visibility logic should reference scopes/roles."""
        assert "admin" in auth_code.lower() or "write" in auth_code.lower()


# ---------------------------------------------------------------------------
# OAuth provider template — MultiAuth (FastMCP 3.1)
# ---------------------------------------------------------------------------


@pytest.fixture
def oauth_code() -> str:
    from mcp_generator.models import ApiMetadata

    meta = ApiMetadata(
        title="Test",
        version="1.0.0",
        servers=[{"url": "http://localhost:3001"}],
    )
    sc = SecurityConfig(
        schemes={"bearerAuth": {"type": "http", "scheme": "bearer"}},
        oauth_config=OAuthConfig(
            scheme_name="oauth2",
            flows={
                "clientCredentials": OAuthFlowConfig(
                    token_url="https://auth.example.com/token",
                    scopes={"read": "Read"},
                )
            },
            all_scopes={"read": "Read"},
        ),
        jwks_uri="https://auth.example.com/.well-known/jwks.json",
        issuer="https://auth.example.com",
        audience="backend-api",
    )
    return generate_oauth_provider(meta, sc)


class TestOAuthProviderMultiAuth:
    def test_multi_auth_function_present(self, oauth_code: str) -> None:
        """create_multi_auth_verifier function should exist."""
        assert "def create_multi_auth_verifier" in oauth_code

    def test_multi_auth_imports_fastmcp(self, oauth_code: str) -> None:
        """Should import MultiAuth from fastmcp."""
        assert "MultiAuth" in oauth_code

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

    def test_multi_auth_primary_verifier(self, oauth_code: str) -> None:
        """MultiAuth should include the primary JWT verifier."""
        assert "create_jwt_verifier()" in oauth_code

    def test_multi_auth_additional_providers(self, oauth_code: str) -> None:
        """MultiAuth should iterate over additional provider configs."""
        assert "for prov in providers:" in oauth_code

    def test_multi_auth_returns_multi_auth_instance(self, oauth_code: str) -> None:
        """Should return MultiAuth(verifiers)."""
        assert "MultiAuth(verifiers)" in oauth_code


# ---------------------------------------------------------------------------
# OAuth provider template — PropelAuth (FastMCP 3.1)
# ---------------------------------------------------------------------------


class TestOAuthProviderPropelAuth:
    def test_propelauth_function_present(self, oauth_code: str) -> None:
        """create_propelauth_provider function should exist."""
        assert "def create_propelauth_provider" in oauth_code

    def test_propelauth_imports_provider(self, oauth_code: str) -> None:
        """Should import PropelAuthProvider from fastmcp."""
        assert "PropelAuthProvider" in oauth_code

    def test_propelauth_config_keys(self, oauth_code: str) -> None:
        """Should read auth_url, introspection_client_id, introspection_client_secret."""
        assert 'config.get("auth_url")' in oauth_code
        assert 'config.get("introspection_client_id")' in oauth_code
        assert 'config.get("introspection_client_secret")' in oauth_code

    def test_propelauth_validates_required_fields(self, oauth_code: str) -> None:
        """Should validate that required fields are present."""
        assert "not all([auth_url, client_id, client_secret])" in oauth_code

    def test_propelauth_returns_none_on_import_error(self, oauth_code: str) -> None:
        """Should handle ImportError gracefully."""
        assert "except ImportError" in oauth_code

    def test_propelauth_passes_base_url(self, oauth_code: str) -> None:
        """Should pass base_url to PropelAuthProvider."""
        assert "base_url=base_url" in oauth_code

    def test_propelauth_passes_required_scopes(self, oauth_code: str) -> None:
        """Should pass required_scopes to PropelAuthProvider."""
        assert "required_scopes=required_scopes" in oauth_code


# ---------------------------------------------------------------------------
# Server integration test template (FastMCP 3.1)
# ---------------------------------------------------------------------------


class TestServerIntegrationTemplate:
    """Test that generate_server_integration_tests produces valid test code."""

    @pytest.fixture
    def integration_code(self) -> str:
        from mcp_generator.models import ApiMetadata, ModuleSpec
        from mcp_generator.templates.test.test_server_integration import (
            generate_server_integration_tests,
        )

        meta = ApiMetadata(
            title="Test API",
            version="1.0.0",
            servers=[{"url": "http://localhost:3001"}],
        )
        sc = SecurityConfig()
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=3,
                code="",
            ),
            "store": ModuleSpec(
                filename="store_server.py",
                api_var_name="store_api",
                api_class_name="StoreApi",
                module_name="store",
                tool_count=2,
                code="",
            ),
        }
        return generate_server_integration_tests(modules, meta, sc)

    def test_generates_code(self, integration_code: str) -> None:
        assert isinstance(integration_code, str)
        assert len(integration_code) > 500

    def test_imports_fastmcp_client(self, integration_code: str) -> None:
        assert "from fastmcp import FastMCP, Client" in integration_code

    def test_imports_server_modules(self, integration_code: str) -> None:
        assert "from servers.pet_server import mcp as pet_mcp" in integration_code
        assert "from servers.store_server import mcp as store_mcp" in integration_code

    def test_has_module_tool_counts(self, integration_code: str) -> None:
        assert "pet_mcp, 3" in integration_code
        assert "store_mcp, 2" in integration_code

    def test_has_composition_tests(self, integration_code: str) -> None:
        assert "class TestComposition" in integration_code
        assert "create_server" in integration_code

    def test_has_error_formatting_tests(self, integration_code: str) -> None:
        assert "class TestErrorFormatting" in integration_code
        assert "_format_api_error" in integration_code

    def test_has_tool_execution_tests(self, integration_code: str) -> None:
        assert "class TestToolExecutionMocked" in integration_code
        assert "call_tool" in integration_code

    def test_has_config_loading_tests(self, integration_code: str) -> None:
        assert "class TestConfigLoading" in integration_code
        assert "fastmcp.json" in integration_code

    def test_has_mock_patterns(self, integration_code: str) -> None:
        """Should use unittest.mock for mocking without live backend."""
        assert "MagicMock" in integration_code
        assert "to_dict" in integration_code

    def test_total_tool_count_in_assertions(self, integration_code: str) -> None:
        assert "TOTAL_TOOL_COUNT" in integration_code
        # 3 + 2 = 5
        assert "== 5" in integration_code


# ---------------------------------------------------------------------------
# Tool schema validation test template
# ---------------------------------------------------------------------------


class TestToolSchemaTemplate:
    """Test that generate_tool_schema_tests produces valid test code."""

    @pytest.fixture
    def schema_code(self) -> str:
        from mcp_generator.models import ApiMetadata, ModuleSpec
        from mcp_generator.templates.test.test_tool_schemas import (
            generate_tool_schema_tests,
        )

        meta = ApiMetadata(
            title="Test API",
            version="1.0.0",
            servers=[{"url": "http://localhost:3001"}],
        )
        sc = SecurityConfig()
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=3,
                code="",
            ),
        }
        return generate_tool_schema_tests(modules, meta, sc)

    def test_generates_code(self, schema_code: str) -> None:
        assert isinstance(schema_code, str)
        assert len(schema_code) > 400

    def test_imports_fastmcp_client(self, schema_code: str) -> None:
        assert "from fastmcp import Client" in schema_code

    def test_has_openapi_spec_fixture(self, schema_code: str) -> None:
        assert "def openapi_spec" in schema_code
        assert "openapi.json" in schema_code

    def test_has_coverage_tests(self, schema_code: str) -> None:
        assert "class TestToolCoverage" in schema_code

    def test_has_parameter_schema_tests(self, schema_code: str) -> None:
        assert "class TestParameterSchemas" in schema_code
        assert "test_all_params_are_typed" in schema_code
        assert "test_optional_params_have_defaults" in schema_code
        assert "test_no_internal_params_exposed" in schema_code

    def test_has_deprecated_detection(self, schema_code: str) -> None:
        assert "class TestDeprecatedTools" in schema_code

    def test_has_response_structure_tests(self, schema_code: str) -> None:
        assert "class TestResponseStructure" in schema_code

    def test_has_no_duplicate_check(self, schema_code: str) -> None:
        assert "test_no_duplicate_tool_names" in schema_code


# ---------------------------------------------------------------------------
# Behavioral edge-case test template
# ---------------------------------------------------------------------------


class TestBehavioralTemplate:
    """Test that generate_behavioral_tests produces valid test code."""

    @pytest.fixture
    def behavioral_code(self) -> str:
        from mcp_generator.models import ApiMetadata, ModuleSpec
        from mcp_generator.templates.test.test_behavioral import (
            generate_behavioral_tests,
        )

        meta = ApiMetadata(
            title="Test API",
            version="1.0.0",
            servers=[{"url": "http://localhost:3001"}],
        )
        sc = SecurityConfig()
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=3,
                code="",
            ),
            "store": ModuleSpec(
                filename="store_server.py",
                api_var_name="store_api",
                api_class_name="StoreApi",
                module_name="store",
                tool_count=2,
                code="",
            ),
        }
        return generate_behavioral_tests(modules, meta, sc)

    def test_generates_code(self, behavioral_code: str) -> None:
        assert isinstance(behavioral_code, str)
        assert len(behavioral_code) > 500

    def test_has_mock_context(self, behavioral_code: str) -> None:
        assert "class MockContext" in behavioral_code
        assert "async def get_state" in behavioral_code

    def test_imports_fastmcp(self, behavioral_code: str) -> None:
        assert "from fastmcp import FastMCP, Client" in behavioral_code

    def test_imports_server_modules(self, behavioral_code: str) -> None:
        assert "from servers.pet_server import mcp as pet_mcp" in behavioral_code
        assert "from servers.store_server import mcp as store_mcp" in behavioral_code

    def test_has_state_contract_tests(self, behavioral_code: str) -> None:
        assert "class TestStateContract" in behavioral_code
        assert "test_missing_api_client_raises" in behavioral_code
        assert "test_wrong_type_api_client" in behavioral_code

    def test_has_parameter_validation_tests(self, behavioral_code: str) -> None:
        assert "class TestParameterValidation" in behavioral_code
        assert "test_malformed_json_gives_clear_error" in behavioral_code
        assert "test_empty_json_object_gives_clear_error" in behavioral_code

    def test_has_response_normalisation_tests(self, behavioral_code: str) -> None:
        assert "class TestResponseNormalisation" in behavioral_code
        assert "test_bytes_response_normalisation" in behavioral_code
        assert "test_generator_response_normalisation" in behavioral_code
        assert "test_to_dict_raises_exception" in behavioral_code

    def test_has_error_message_quality_tests(self, behavioral_code: str) -> None:
        assert "class TestErrorMessageQuality" in behavioral_code
        assert "test_connection_error_mentions_connectivity" in behavioral_code
        assert "test_timeout_error_mentions_timeout" in behavioral_code
        assert "test_error_log_includes_tool_name" in behavioral_code

    def test_has_json_serialisability_tests(self, behavioral_code: str) -> None:
        assert "class TestJsonSerialisability" in behavioral_code
        assert "test_successful_response_is_json_serialisable" in behavioral_code

    def test_has_async_safety_tests(self, behavioral_code: str) -> None:
        assert "class TestAsyncSafety" in behavioral_code
        assert "test_coroutine_response_not_silently_wrapped" in behavioral_code

    def test_has_tool_discovery(self, behavioral_code: str) -> None:
        """Template should discover tools at runtime, not hardcode names."""
        assert "_discover_tools" in behavioral_code
        assert "ALL_TOOLS" in behavioral_code
        assert "PYDANTIC_TOOLS" in behavioral_code

    def test_has_expected_to_fail_markers(self, behavioral_code: str) -> None:
        """Template should document which tests are expected to fail."""
        assert "Expected to fail initially" in behavioral_code

    def test_has_actionable_assertion_messages(self, behavioral_code: str) -> None:
        """Assertion messages should include 'Fix:' instructions."""
        assert "Fix:" in behavioral_code

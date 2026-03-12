"""Tests for mcp_generator.generator — composition server generation."""

import pytest

from mcp_generator.generator import generate_main_composition_server
from mcp_generator.models import ApiMetadata, ModuleSpec, SecurityConfig

# ---------------------------------------------------------------------------
# Fixtures (local to this module — also re-uses conftest fixtures)
# ---------------------------------------------------------------------------


@pytest.fixture
def _two_modules() -> dict[str, ModuleSpec]:
    return {
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
            tool_count=4,
            code="",
        ),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateMainCompositionServer:
    """Test the main composition server code generation (FastMCP 3.x)."""

    def test_returns_string(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert isinstance(code, str)
        assert len(code) > 200

    # --- FastMCP 3.x API usage ---

    def test_uses_mount_namespace(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert 'mount(pet_mcp, namespace="pet")' in code
        assert 'mount(store_mcp, namespace="store")' in code

    def test_does_not_use_deprecated_import_server(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "import_server" not in code

    def test_does_not_use_mount_prefix(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "prefix=" not in code

    def test_does_not_use_resource_prefix_format(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "resource_prefix_format" not in code

    def test_uses_app_run_transport(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert 'app.run(transport="stdio")' in code
        assert 'app.run(transport="http"' in code

    def test_uses_http_app_not_create_streamable(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "app.http_app(" in code
        assert "create_streamable_http_app" not in code

    def test_uses_fastmcp_event_store(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "from fastmcp.server.event_store import EventStore" in code

    # --- Header / metadata ---

    def test_header_contains_title(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert api_metadata.title in code

    def test_header_contains_version(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert api_metadata.version in code

    def test_contact_included_when_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "test@example.com" in code

    def test_contact_absent_when_not_set(
        self,
        api_metadata_no_extras: ApiMetadata,
        security_config_none: SecurityConfig,
        _two_modules: dict,
    ) -> None:
        code = generate_main_composition_server(
            _two_modules, api_metadata_no_extras, security_config_none
        )
        assert "Contact:" not in code

    # --- Import structure ---

    def test_imports_modular_servers(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from servers.pet_server import mcp as pet_mcp" in code
        assert "from servers.store_server import mcp as store_mcp" in code

    def test_imports_fastmcp(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "from fastmcp import FastMCP" in code

    # --- Authentication variants ---

    def test_no_auth_has_no_jwt_verifier(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "create_jwt_verifier" not in code
        assert "validate-tokens" not in code

    def test_bearer_auth_has_jwt_verifier(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_jwt_verifier" in code
        assert "validate-tokens" in code

    def test_auth_middleware_always_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ApiClientContextMiddleware" in code

    # --- Tool count ---

    def test_total_tool_count_matches(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        # 3 + 4 = 7
        assert "TOTAL_TOOL_COUNT = 7" in code

    # --- create_server factory ---

    def test_has_create_server_factory(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        """create_server() is required by fastmcp CLI (dev/run/install)."""
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "async def create_server()" in code
        assert "return app" in code

    # --- FastMCP 3.x middleware ---

    def test_middleware_imports(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ErrorHandlingMiddleware" in code
        assert "DetailedTimingMiddleware" in code
        assert "LoggingMiddleware" in code

    # --- FastMCP 3.1 features ---

    def test_response_limiting_middleware_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "ResponseLimitingMiddleware" in code

    def test_ping_middleware_import(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "PingMiddleware" in code

    def test_search_tools_transform_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "SearchTools" in code

    def test_code_mode_transform_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "CodeMode" in code

    def test_features_config_loading(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "_features_config" in code
        assert "fastmcp.json" in code

    def test_transforms_passed_to_fastmcp(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "transforms=_transforms" in code

    def test_opentelemetry_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "TracerProvider" in code
        assert "OTEL_EXPORTER_OTLP_ENDPOINT" in code

    def test_dynamic_visibility_section(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_none)
        assert "dynamic_visibility" in code

    def test_multi_auth_import_with_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig, _two_modules: dict
    ) -> None:
        code = generate_main_composition_server(_two_modules, api_metadata, security_config_bearer)
        assert "create_multi_auth_verifier" in code

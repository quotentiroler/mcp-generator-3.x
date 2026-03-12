"""Tests for mcp_generator.renderers — code generation output validation."""

from mcp_generator.models import ApiMetadata, SecurityConfig
from mcp_generator.renderers import render_fastmcp_template, render_pyproject_template

# ---------------------------------------------------------------------------
# render_pyproject_template
# ---------------------------------------------------------------------------


class TestRenderPyprojectTemplate:
    def test_contains_fastmcp_3x_dep(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=5
        )
        assert "fastmcp>=3.0.0,<4.0.0" in content

    def test_does_not_contain_fastmcp_2x_dep(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=5
        )
        assert "fastmcp>=2" not in content

    def test_project_name_sanitized(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "my_cool.api", total_tools=1
        )
        assert 'name = "my-cool-api"' in content

    def test_version_sanitized(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        # Modify api_metadata version to trigger sanitization
        api_metadata.version = "1.0.0.abc123"
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1
        )
        # The version in pyproject should have '+' instead of final '.'
        assert "1.0.0+abc123" in content

    def test_middleware_package_included_when_auth(
        self, api_metadata: ApiMetadata, security_config_bearer: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_bearer, "test_api", total_tools=1
        )
        # Python list repr uses single quotes: ['servers', 'middleware']
        assert "'middleware'" in content

    def test_storage_dep_when_enabled(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1, enable_storage=True
        )
        assert "cryptography" in content


# ---------------------------------------------------------------------------
# render_fastmcp_template
# ---------------------------------------------------------------------------


class TestRenderFastmcpTemplate:
    def test_returns_valid_json(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert "composition" in parsed or isinstance(parsed, dict)

    def test_strategy_is_mount(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        assert '"mount"' in content

    def test_features_section_present(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        parsed = json.loads(content)
        assert "features" in parsed

    def test_feature_keys_complete(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """All 11 FastMCP 3.0/3.1 feature keys exist in the template."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        expected_keys = {
            "tool_tags",
            "tool_timeouts",
            "search_tools",
            "code_mode",
            "response_limiting",
            "ping_middleware",
            "multi_auth",
            "component_versioning",
            "validate_output",
            "dynamic_visibility",
            "opentelemetry",
        }
        assert expected_keys.issubset(set(features.keys()))

    def test_opentelemetry_service_name_rendered(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """service_name placeholder should be replaced with API title."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        otel = json.loads(content)["features"]["opentelemetry"]
        assert "{{service_name}}" not in otel.get("service_name", "")
        assert api_metadata.title.lower().replace(" ", "-") in otel["service_name"]

    def test_telemetry_optional_dep_in_pyproject(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig
    ) -> None:
        content = render_pyproject_template(
            api_metadata, security_config_none, "test_api", total_tools=1
        )
        assert "opentelemetry-api" in content
        assert "opentelemetry-sdk" in content

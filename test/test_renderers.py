"""Tests for mcp_generator.renderers — code generation output validation."""

import pytest

from mcp_generator.models import ApiMetadata, SecurityConfig
from mcp_generator.renderers import (
    generate_tool_for_method,
    render_fastmcp_template,
    render_pyproject_template,
)

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
        assert "fastmcp>=3.1.0,<4.0.0" in content

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
            "rate_limiting",
            "multi_auth",
            "component_versioning",
            "validate_output",
            "dynamic_visibility",
            "opentelemetry",
            "oauth_proxy",
        }
        assert expected_keys.issubset(set(features.keys()))

    def test_version_filter_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """version_filter key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "version_filter" in features
        vf = features["version_filter"]
        assert "enabled" in vf
        assert "include_unversioned" in vf
        assert "version_gte" in vf
        assert "version_lt" in vf

    def test_propelauth_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """propelauth key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "propelauth" in features
        pa = features["propelauth"]
        assert "enabled" in pa
        assert "auth_url" in pa
        assert "introspection_client_id" in pa
        assert "introspection_client_secret" in pa

    def test_search_tools_serializer_field(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """search_tools should have a serializer field."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        search = json.loads(content)["features"]["search_tools"]
        assert "serializer" in search

    def test_version_filter_defaults(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """version_filter should default to disabled with include_unversioned=true."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        vf = json.loads(content)["features"]["version_filter"]
        assert vf["enabled"] is False
        assert vf["include_unversioned"] is True

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

    def test_rate_limiting_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """rate_limiting key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "rate_limiting" in features
        rl = features["rate_limiting"]
        assert "enabled" in rl
        assert "max_requests_per_second" in rl
        assert "burst_capacity" in rl
        assert "global_limit" in rl

    def test_oauth_proxy_in_features(
        self, api_metadata: ApiMetadata, security_config_none: SecurityConfig, sample_modules: dict
    ) -> None:
        """oauth_proxy key should be present in features."""
        import json

        content = render_fastmcp_template(
            api_metadata, security_config_none, sample_modules, total_tools=5, server_name="test"
        )
        features = json.loads(content)["features"]
        assert "oauth_proxy" in features
        op = features["oauth_proxy"]
        assert "enabled" in op
        assert "upstream_authorization_endpoint" in op
        assert "upstream_token_endpoint" in op
        assert "upstream_client_id" in op
        assert "upstream_client_secret" in op
        assert "forward_pkce" in op


# ---------------------------------------------------------------------------
# Generated tool code — progress, elicitation, sampling (FastMCP 3.1)
# ---------------------------------------------------------------------------


class TestGeneratedToolFeatures:
    """Test that generated tool functions include new FastMCP features."""

    @pytest.fixture
    def tool_code(self) -> str:
        """Generate a tool function from a simple API method."""

        def get_pet(pet_id: str) -> dict:
            """Get a pet by ID."""
            return {}

        return generate_tool_for_method("pet_api", "get_pet", get_pet, tag_name="pet")

    @pytest.fixture
    def tool_code_required_params(self) -> str:
        """Generate a tool with required parameters for elicitation testing."""

        def add_pet(name: str, status: str) -> dict:
            """Add a new pet."""
            return {}

        return generate_tool_for_method("pet_api", "add_pet", add_pet, tag_name="pet")

    def test_progress_reporting_start(self, tool_code: str) -> None:
        """Tools should report progress at start."""
        assert "report_progress(0, 3" in tool_code

    def test_progress_reporting_api_call(self, tool_code: str) -> None:
        """Tools should report progress when calling API."""
        assert "report_progress(1, 3" in tool_code

    def test_progress_reporting_done(self, tool_code: str) -> None:
        """Tools should report progress on completion."""
        assert "report_progress(3, 3" in tool_code

    def test_elicitation_for_missing_params(self, tool_code_required_params: str) -> None:
        """Tools with required params should include elicitation block."""
        assert "ctx.elicit(" in tool_code_required_params

    def test_elicitation_checks_missing(self, tool_code_required_params: str) -> None:
        """Elicitation should check for missing required parameters."""
        assert "_missing" in tool_code_required_params
        assert "_required" in tool_code_required_params

    def test_elicitation_handles_decline(self, tool_code_required_params: str) -> None:
        """Elicitation should handle user declining."""
        assert "accept" in tool_code_required_params

    def test_elicitation_graceful_fallback(self, tool_code: str) -> None:
        """Elicitation should not fail if client doesn't support it."""
        assert "pass  # Elicitation not supported" in tool_code

    def test_sampling_on_api_error(self, tool_code: str) -> None:
        """Tools should use ctx.sample() for LLM-assisted error recovery on API errors."""
        assert "ctx.sample(" in tool_code

    def test_sampling_suggestion_in_error(self, tool_code: str) -> None:
        """Sampling result should be included in the error message as a suggestion."""
        assert "Suggestion" in tool_code

    def test_sampling_fallback_on_failure(self, tool_code: str) -> None:
        """If sampling fails, tool should still raise the original API error."""
        assert "API Error:" in tool_code

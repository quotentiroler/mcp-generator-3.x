"""Tests for mcp_generator.models — dataclass behaviour and helpers."""

from mcp_generator.models import ApiMetadata, ModuleSpec, OAuthConfig, SecurityConfig, ToolSpec


class TestApiMetadata:
    def test_defaults(self) -> None:
        m = ApiMetadata()
        assert m.title == "Generated API"
        assert m.description == ""
        assert m.version == "0.0.1"
        assert m.backend_url == "http://localhost:3001"

    def test_backend_url_from_servers(self) -> None:
        m = ApiMetadata(servers=[{"url": "https://api.example.com"}])
        assert m.backend_url == "https://api.example.com"

    def test_backend_url_fallback_empty_servers(self) -> None:
        m = ApiMetadata(servers=[])
        assert m.backend_url == "http://localhost:3001"


class TestSecurityConfig:
    def test_has_authentication_false_when_empty(self) -> None:
        sc = SecurityConfig()
        assert sc.has_authentication() is False

    def test_has_authentication_true_with_schemes(self) -> None:
        sc = SecurityConfig(schemes={"bearer": {"type": "http"}})
        assert sc.has_authentication() is True

    def test_has_authentication_true_with_oauth_only(self) -> None:
        sc = SecurityConfig(oauth_config=OAuthConfig(scheme_name="oauth2"))
        assert sc.has_authentication() is True

    def test_jwks_uri_fallback(self) -> None:
        sc = SecurityConfig()
        assert sc.get_jwks_uri("http://localhost") == "http://localhost/.well-known/jwks.json"

    def test_jwks_uri_explicit(self) -> None:
        sc = SecurityConfig(jwks_uri="https://custom.com/jwks")
        assert sc.get_jwks_uri("http://localhost") == "https://custom.com/jwks"

    def test_issuer_fallback(self) -> None:
        sc = SecurityConfig()
        assert sc.get_issuer("http://localhost") == "http://localhost"

    def test_audience_fallback(self) -> None:
        sc = SecurityConfig()
        assert sc.get_audience() == "backend-api"


class TestModuleSpec:
    def test_resource_count_default(self) -> None:
        ms = ModuleSpec(
            filename="test.py",
            api_var_name="test_api",
            api_class_name="TestApi",
            module_name="test",
            tool_count=5,
            code="# code",
        )
        assert ms.resource_count == 0

    def test_tag_name_default(self) -> None:
        ms = ModuleSpec(
            filename="test.py",
            api_var_name="test_api",
            api_class_name="TestApi",
            module_name="test",
            tool_count=5,
            code="# code",
        )
        assert ms.tag_name == ""


class TestToolSpec:
    def test_defaults(self) -> None:
        ts = ToolSpec(
            tool_name="list_pets",
            method_name="list_pets",
            api_var_name="pet_api",
            parameters=[],
            docstring="List all pets",
        )
        assert ts.tags == []
        assert ts.deprecated is False
        assert ts.timeout is None
        assert ts.validate_output is None

    def test_tags_assignment(self) -> None:
        ts = ToolSpec(
            tool_name="list_pets",
            method_name="list_pets",
            api_var_name="pet_api",
            parameters=[],
            docstring="List all pets",
            tags=["pet", "read"],
        )
        assert ts.tags == ["pet", "read"]

    def test_deprecated_flag(self) -> None:
        ts = ToolSpec(
            tool_name="old_method",
            method_name="old_method",
            api_var_name="pet_api",
            parameters=[],
            docstring="Deprecated method",
            deprecated=True,
        )
        assert ts.deprecated is True

    def test_timeout(self) -> None:
        ts = ToolSpec(
            tool_name="slow_op",
            method_name="slow_op",
            api_var_name="pet_api",
            parameters=[],
            docstring="Slow operation",
            timeout=60,
        )
        assert ts.timeout == 60

    def test_validate_output(self) -> None:
        ts = ToolSpec(
            tool_name="validated",
            method_name="validated",
            api_var_name="pet_api",
            parameters=[],
            docstring="Validated tool",
            validate_output=False,
        )
        assert ts.validate_output is False

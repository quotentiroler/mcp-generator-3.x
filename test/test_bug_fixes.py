"""TDD bug-fix tests — each test targets a verified bug in the codebase.

Written RED-first: these tests expose real bugs that need fixing.
Each class documents the bug, the root cause, and the expected behavior.
"""

import pytest

from mcp_generator.models import ApiMetadata, ModuleSpec, SecurityConfig

# ---------------------------------------------------------------------------
# Bug #2: OpenAPI 3.1 nullable type arrays crash schema parsing
#
# Root cause: _OPENAPI_TYPE_MAP.get(prop_type) where prop_type can be a list
# like ["string", "null"] in OpenAPI 3.1 — raises TypeError: unhashable type
# ---------------------------------------------------------------------------


class TestOpenAPI31NullableTypes:
    """OpenAPI 3.1 uses type: ["string", "null"] for nullable fields."""

    def test_nullable_string_does_not_crash(self) -> None:
        """_parse_schema_fields should handle list-typed properties."""
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "optional name"},
            },
        }
        # Should not raise TypeError: unhashable type: 'list'
        fields = _parse_schema_fields(schema, {})
        assert len(fields) == 1
        assert fields[0].name == "name"
        assert fields[0].python_type == "str"

    def test_nullable_integer_maps_correctly(self) -> None:
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "count": {"type": ["integer", "null"]},
            },
        }
        fields = _parse_schema_fields(schema, {})
        assert fields[0].python_type == "int"

    def test_nullable_boolean_maps_correctly(self) -> None:
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "active": {"type": ["boolean", "null"]},
            },
        }
        fields = _parse_schema_fields(schema, {})
        assert fields[0].python_type == "bool"


# ---------------------------------------------------------------------------
# Bug #3: Path-level parameters are ignored for resource endpoints
#
# Root cause: get_resource_endpoints only reads operation-level parameters,
# not path-level parameters defined on the path item object.
# ---------------------------------------------------------------------------


class TestPathLevelParameters:
    """OpenAPI allows parameters at the path item level, shared by all operations."""

    def test_path_level_params_are_included(self, tmp_path) -> None:
        import json

        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/pets/{petId}": {
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "get": {
                        "operationId": "getPetById",
                        "tags": ["pet"],
                        "summary": "Get pet by ID",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        (tmp_path / "openapi.json").write_text(json.dumps(spec), encoding="utf-8")
        resources = get_resource_endpoints(tmp_path)
        assert "pet" in resources
        pet_resources = resources["pet"]
        assert len(pet_resources) == 1
        assert "petId" in pet_resources[0]["path_params"]

    def test_path_level_query_params_are_included(self, tmp_path) -> None:
        import json

        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/items": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                            "description": "Max items",
                        }
                    ],
                    "get": {
                        "operationId": "listItems",
                        "tags": ["item"],
                        "summary": "List items",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        (tmp_path / "openapi.json").write_text(json.dumps(spec), encoding="utf-8")
        resources = get_resource_endpoints(tmp_path)
        assert "item" in resources
        query_names = [qp["name"] for qp in resources["item"][0]["query_params"]]
        assert "limit" in query_names


# ---------------------------------------------------------------------------
# Bug #4: $ref parameters produce None in generated function signatures
#
# Root cause: If parameter is {"$ref": "..."}, param.get("name") is None
# and this None gets appended to path_params or silently ignored.
# ---------------------------------------------------------------------------


class TestRefParameterHandling:
    """$ref parameters should be resolved before extraction."""

    def test_ref_parameter_is_resolved(self, tmp_path) -> None:
        import json

        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/pets/{petId}": {
                    "get": {
                        "operationId": "getPetById",
                        "tags": ["pet"],
                        "summary": "Get pet by ID",
                        "parameters": [{"$ref": "#/components/parameters/PetId"}],
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
            "components": {
                "parameters": {
                    "PetId": {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                }
            },
        }
        (tmp_path / "openapi.json").write_text(json.dumps(spec), encoding="utf-8")
        resources = get_resource_endpoints(tmp_path)
        assert "pet" in resources
        # The resolved parameter name should appear, not None
        assert "petId" in resources["pet"][0]["path_params"]
        assert None not in resources["pet"][0]["path_params"]


# ---------------------------------------------------------------------------
# Bug #5: Swagger 2.0 security definitions are not parsed
#
# Root cause: get_security_config only reads components.securitySchemes
# (OpenAPI 3.x), not securityDefinitions (Swagger 2.0).
# ---------------------------------------------------------------------------


class TestSwagger20SecurityParsing:
    """Swagger 2.0 uses securityDefinitions instead of components.securitySchemes."""

    def test_swagger2_bearer_auth_detected(self, tmp_path) -> None:
        import json

        from mcp_generator.introspection import get_security_config

        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "securityDefinitions": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                }
            },
            "security": [{"Bearer": []}],
            "paths": {},
        }
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        config = get_security_config(tmp_path)
        assert config.schemes, "Swagger 2.0 securityDefinitions should be detected"

    def test_swagger2_oauth2_detected(self, tmp_path) -> None:
        import json

        from mcp_generator.introspection import get_security_config

        spec = {
            "swagger": "2.0",
            "info": {"title": "OAuth API", "version": "1.0"},
            "host": "api.example.com",
            "securityDefinitions": {
                "oauth2": {
                    "type": "oauth2",
                    "flow": "accessCode",
                    "authorizationUrl": "https://auth.example.com/authorize",
                    "tokenUrl": "https://auth.example.com/token",
                    "scopes": {"read": "Read access"},
                }
            },
            "paths": {},
        }
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")

        config = get_security_config(tmp_path)
        assert config.schemes, "Swagger 2.0 OAuth2 should be detected"


# ---------------------------------------------------------------------------
# Bug #8: Required-parameter check treats falsy values as missing
#
# Root cause: `_missing = [p for p in _required if not _locals.get(p)]`
# uses truthiness instead of `is None` check.
# Values like 0, False, "" are valid but treated as missing.
# ---------------------------------------------------------------------------


class TestFalsyRequiredParameters:
    """Generated tool code must not treat 0, False, or '' as missing."""

    def test_missing_check_uses_is_none(self) -> None:
        """The generated missing-parameter check should use `is None`, not truthiness."""
        from mcp_generator.models import ParameterInfo, ToolSpec
        from mcp_generator.renderers import _render_tool

        spec = ToolSpec(
            tool_name="test_tool",
            method_name="test_method",
            api_var_name="test_api",
            docstring="Test docstring",
            parameters=[
                ParameterInfo(
                    name="count",
                    type_hint="int",
                    required=True,
                    description="A count",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                ),
            ],
        )
        code = _render_tool(spec)
        # The missing check should use `is None` not truthiness
        # `not _locals.get(p)` treats 0, False, "" as missing
        assert "_locals.get(p) is None" in code, (
            "Required-parameter missing check should use 'is None', not truthiness. "
            f"Found: {[line.strip() for line in code.splitlines() if '_missing' in line]}"
        )


# ---------------------------------------------------------------------------
# Bug #9: Resource parameter names with special chars break generated Python
#
# Root cause: render_resource uses param names directly in function args
# without sanitizing. Names like "sort-by" or "x.filter" cause SyntaxError.
# ---------------------------------------------------------------------------


class TestResourceParameterSanitization:
    """Parameter names with dashes/dots must be sanitized to valid Python identifiers."""

    def test_dash_in_param_name_produces_valid_python(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?sort-by}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="sort-by",
                    type_hint="str",
                    required=False,
                    description="Sort field",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        # The generated code must be valid Python
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")

    def test_dot_in_param_name_produces_valid_python(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="data",
            uri_template="data:///data{?x.filter}",
            method_name="list_data",
            api_var_name="data_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="x.filter",
                    type_hint="str",
                    required=False,
                    description="Filter",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List data",
            mime_type="application/json",
        )
        code = render_resource(spec)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")

    def test_dash_in_path_param_produces_valid_python(self) -> None:
        from mcp_generator.models import ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="orgs",
            uri_template="orgs:///orgs/{org-id}/members",
            method_name="get_org_members",
            api_var_name="org_api",
            path_params=["org-id"],
            query_params=[],
            description="Get org members",
            mime_type="application/json",
        )
        code = render_resource(spec)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")


# ---------------------------------------------------------------------------
# Bug #10: Resource query param defaults use wrong type
#
# Root cause: `default_val = "None" if "str" in qparam.type_hint else "0"`
# Boolean and list params get default 0 instead of None.
# ---------------------------------------------------------------------------


class TestResourceQueryParamDefaults:
    """All optional query params should default to None, not 0."""

    def test_bool_param_defaults_to_none(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?active}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="active",
                    type_hint="bool",
                    required=False,
                    description="Active filter",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        # Bool params should default to None, not 0
        assert "active: bool | None = None" in code, (
            f"Bool query param should default to None, not 0.\nGenerated:\n{code}"
        )
        assert "active: bool | None = 0" not in code

    def test_int_param_defaults_to_none(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?limit}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="limit",
                    type_hint="int",
                    required=False,
                    description="Limit results",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        assert "limit: int | None = None" in code, (
            f"Int query param should default to None, not 0.\nGenerated:\n{code}"
        )


# ---------------------------------------------------------------------------
# Bug #11: Unescaped API metadata strings can break generated Python
#
# Root cause: Title/description are interpolated into string literals
# without escaping quotes. E.g. title='Joe\'s API' breaks the f-string.
# ---------------------------------------------------------------------------


class TestMetadataStringEscaping:
    """API titles/descriptions with quotes must not break generated code."""

    def test_title_with_double_quote(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title='My "Cool" API',
            version="1.0.0",
            description="A test API",
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server code has SyntaxError with quoted title: {e}")

    def test_description_with_triple_quotes(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title="Test API",
            version="1.0.0",
            description='A description with """triple quotes""" inside',
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(
                f"Generated server code has SyntaxError with triple-quoted description: {e}"
            )

    def test_title_with_backslash(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title="My API\\v2",
            version="1.0.0",
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server code has SyntaxError with backslash in title: {e}")

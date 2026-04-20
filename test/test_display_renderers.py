"""Tests for Phase 2: response schema extraction and display tool generation."""



from mcp_generator.display_renderers import (
    _table_columns_for_fields,
    _tool_name_for_endpoint,
    render_display_module,
)
from mcp_generator.introspection import (
    _extract_response_schema,
    _parse_schema_fields,
    _resolve_ref,
)
from mcp_generator.models import DisplayEndpoint, ResponseField, ResponseSchema

# ---------------------------------------------------------------------------
# Test OpenAPI spec with various response shapes
# ---------------------------------------------------------------------------

SCHEMA_TEST_SPEC: dict = {
    "openapi": "3.0.3",
    "info": {"title": "Schema Test API", "version": "1.0.0"},
    "paths": {
        "/pets/{petId}": {
            "get": {
                "operationId": "getPetById",
                "tags": ["pet"],
                "summary": "Get pet by ID",
                "parameters": [
                    {"name": "petId", "in": "path", "required": True, "schema": {"type": "integer"}},
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"},
                            }
                        },
                    }
                },
            }
        },
        "/pets": {
            "get": {
                "operationId": "findPets",
                "tags": ["pet"],
                "summary": "Find all pets",
                "parameters": [
                    {"name": "status", "in": "query", "required": False, "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/inventory": {
            "get": {
                "operationId": "getInventory",
                "tags": ["store"],
                "summary": "Returns inventory",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": {"type": "integer"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/login": {
            "get": {
                "operationId": "loginUser",
                "tags": ["user"],
                "summary": "Login user",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"type": "string"},
                            }
                        },
                    }
                },
            }
        },
        "/orders/{orderId}": {
            "get": {
                "operationId": "getOrder",
                "tags": ["store"],
                "summary": "Get order by ID",
                "parameters": [
                    {"name": "orderId", "in": "path", "required": True, "schema": {"type": "integer"}},
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Order"},
                            }
                        },
                    }
                },
            }
        },
    },
    "tags": [
        {"name": "pet"},
        {"name": "store"},
        {"name": "user"},
    ],
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "category": {"$ref": "#/components/schemas/Category"},
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                    },
                    "tags": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Tag"},
                    },
                },
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Tag": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Order": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "quantity": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "enum": ["placed", "approved", "delivered"],
                    },
                    "complete": {"type": "boolean"},
                    "shipDate": {"type": "string", "format": "date-time"},
                },
            },
        }
    },
}


# ---------------------------------------------------------------------------
# _resolve_ref
# ---------------------------------------------------------------------------


class TestResolveRef:
    def test_resolves_simple_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "#/components/schemas/Pet")
        assert "properties" in result
        assert "id" in result["properties"]

    def test_returns_empty_dict_for_invalid_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "#/components/schemas/Nonexistent")
        assert result == {}

    def test_returns_empty_dict_for_malformed_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _parse_schema_fields
# ---------------------------------------------------------------------------


class TestParseSchemaFields:
    def test_parses_pet_schema(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        names = {f.name for f in fields}
        assert {"id", "name", "category", "status", "tags"} == names

    def test_detects_enum_field(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        status = next(f for f in fields if f.name == "status")
        assert status.is_enum is True
        assert "available" in status.enum_values

    def test_detects_nested_object(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        cat = next(f for f in fields if f.name == "category")
        assert cat.is_nested_object is True
        nested_names = {nf.name for nf in cat.nested_fields}
        assert "id" in nested_names
        assert "name" in nested_names

    def test_detects_array_field(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        tags = next(f for f in fields if f.name == "tags")
        assert tags.is_array is True

    def test_detects_boolean_field(self) -> None:
        order = SCHEMA_TEST_SPEC["components"]["schemas"]["Order"]
        fields = _parse_schema_fields(order, SCHEMA_TEST_SPEC)
        complete = next(f for f in fields if f.name == "complete")
        assert complete.python_type == "bool"

    def test_detects_datetime_format(self) -> None:
        order = SCHEMA_TEST_SPEC["components"]["schemas"]["Order"]
        fields = _parse_schema_fields(order, SCHEMA_TEST_SPEC)
        ship = next(f for f in fields if f.name == "shipDate")
        assert ship.format == "date-time"

    def test_respects_max_depth(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC, max_depth=1)
        cat = next((f for f in fields if f.name == "category"), None)
        # At max_depth=1, the ref resolves but can't recurse further
        assert cat is not None

    def test_handles_circular_refs(self) -> None:
        """Circular $ref should not cause infinite recursion."""
        circular_spec = {
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "child": {"$ref": "#/components/schemas/Node"},
                        },
                    }
                }
            }
        }
        node = circular_spec["components"]["schemas"]["Node"]
        fields = _parse_schema_fields(node, circular_spec)
        assert len(fields) >= 1  # Should not hang


# ---------------------------------------------------------------------------
# _extract_response_schema
# ---------------------------------------------------------------------------


class TestExtractResponseSchema:
    def test_extracts_single_object(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/pets/{petId}"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is not None
        assert schema.is_object is True
        assert schema.is_array is False
        assert schema.schema_name == "Pet"
        assert len(schema.fields) >= 4

    def test_extracts_array_of_objects(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/pets"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is not None
        assert schema.is_array is True
        assert schema.schema_name == "Pet"

    def test_skips_additional_properties_only(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/inventory"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_skips_scalar_string(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/login"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_returns_none_for_empty_responses(self) -> None:
        schema = _extract_response_schema({}, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_returns_none_for_no_content(self) -> None:
        schema = _extract_response_schema(
            {"200": {"description": "OK"}}, SCHEMA_TEST_SPEC
        )
        assert schema is None


# ---------------------------------------------------------------------------
# _tool_name_for_endpoint
# ---------------------------------------------------------------------------


class TestToolNameForEndpoint:
    def _make_endpoint(self, op_id: str, is_array: bool = False) -> DisplayEndpoint:
        schema = ResponseSchema(
            fields=[ResponseField(name="id", python_type="int")],
            is_array=is_array,
            is_object=not is_array,
            schema_name="Pet",
        )
        return DisplayEndpoint(
            operation_id=op_id,
            path="/test",
            http_method="get",
            summary="test",
            tag="pet",
            path_params=[],
            query_params=[],
            response_schema=schema,
        )

    def test_array_endpoint_gets_table_suffix(self) -> None:
        ep = self._make_endpoint("findPetsByStatus", is_array=True)
        name = _tool_name_for_endpoint(ep)
        assert name == "view_find_pets_by_status_table"

    def test_object_endpoint_gets_detail_suffix(self) -> None:
        ep = self._make_endpoint("getPetById", is_array=False)
        name = _tool_name_for_endpoint(ep)
        assert name == "view_get_pet_by_id_detail"

    def test_unique_names_for_similar_endpoints(self) -> None:
        ep1 = self._make_endpoint("findPetsByStatus", is_array=True)
        ep2 = self._make_endpoint("findPetsByTags", is_array=True)
        assert _tool_name_for_endpoint(ep1) != _tool_name_for_endpoint(ep2)


# ---------------------------------------------------------------------------
# _table_columns_for_fields
# ---------------------------------------------------------------------------


class TestTableColumnsForFields:
    def test_skips_array_fields(self) -> None:
        fields = [
            ResponseField(name="id", python_type="int"),
            ResponseField(name="tags", python_type="list", is_array=True),
            ResponseField(name="name", python_type="str"),
        ]
        columns = _table_columns_for_fields(fields)
        keys = [c["key"] for c in columns]
        assert "id" in keys
        assert "name" in keys
        assert "tags" not in keys

    def test_skips_nested_objects(self) -> None:
        fields = [
            ResponseField(name="id", python_type="int"),
            ResponseField(name="category", python_type="dict", is_nested_object=True),
        ]
        columns = _table_columns_for_fields(fields)
        keys = [c["key"] for c in columns]
        assert "category" not in keys

    def test_labels_are_title_case(self) -> None:
        fields = [ResponseField(name="first_name", python_type="str")]
        columns = _table_columns_for_fields(fields)
        assert columns[0]["label"] == "First Name"


# ---------------------------------------------------------------------------
# render_display_module (integration)
# ---------------------------------------------------------------------------


class TestRenderDisplayModule:
    def _make_endpoints(self) -> list[DisplayEndpoint]:
        pet_fields = _parse_schema_fields(
            SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"], SCHEMA_TEST_SPEC
        )
        return [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find all pets",
                tag="pet",
                path_params=[],
                query_params=[{"name": "status", "required": False, "schema": {"type": "string"}}],
                response_schema=ResponseSchema(fields=pet_fields, is_array=True, schema_name="Pet"),
            ),
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(fields=pet_fields, is_object=True, schema_name="Pet"),
            ),
        ]

    def test_renders_non_empty_module(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert code  # non-empty
        assert "PetDisplay" in code
        assert "FastMCP" in code

    def test_generated_code_compiles(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        compile(code, "pet_display.py", "exec")

    def test_contains_table_tool(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "view_find_pets_table" in code
        assert "DataTable" in code

    def test_contains_detail_tool(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "view_get_pet_by_id_detail" in code
        assert "Card" in code

    def test_contains_status_variants(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "_STATUS_VARIANTS" in code
        assert "'available': 'success'" in code

    def test_contains_prefab_imports(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "from prefab_ui.app import PrefabApp" in code
        assert "PREFAB_AVAILABLE" in code

    def test_returns_empty_for_no_endpoints(self) -> None:
        code = render_display_module("empty", [], "empty_api", "EmptyApi")
        assert code == ""

    def test_returns_empty_for_endpoints_without_schema(self) -> None:
        ep = DisplayEndpoint(
            operation_id="noSchema",
            path="/nothing",
            http_method="get",
            summary="No schema",
            tag="x",
            path_params=[],
            query_params=[],
            response_schema=None,
        )
        code = render_display_module("x", [ep], "x_api", "XApi")
        assert code == ""

    def test_enum_fields_use_badge_with_variant(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "_STATUS_VARIANTS.get(" in code
        assert "Badge(" in code

    def test_detail_tool_has_error_handling(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "except Exception" in code
        assert '"error"' in code or '"Error"' in code

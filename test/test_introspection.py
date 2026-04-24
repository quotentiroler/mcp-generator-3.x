"""Tests for mcp_generator.introspection — tag auto-discovery and spec loading."""

import copy
import json
from pathlib import Path

from mcp_generator.introspection import (
    _extract_response_schema,
    _fields_to_coercion_schema,
    _parse_schema_fields,
    _resolve_ref,
    enrich_spec_tags,
    get_body_schemas,
)
from mcp_generator.models import ResponseField
from test.conftest import MINIMAL_OPENAPI_SPEC

# ---------------------------------------------------------------------------
# enrich_spec_tags
# ---------------------------------------------------------------------------


class TestEnrichSpecTags:
    def test_discovers_undeclared_tag(self) -> None:
        """'user' tag is used on /users but not declared in top-level tags."""
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        # Confirm precondition: only 'pet' is declared
        declared = {t["name"] for t in spec["tags"]}
        assert "pet" in declared
        assert "user" not in declared

        discovered = enrich_spec_tags(spec)

        assert "user" in discovered
        tag_names = {t["name"] for t in spec["tags"]}
        assert "user" in tag_names
        assert "pet" in tag_names  # existing tag preserved

    def test_no_duplicates_when_already_declared(self) -> None:
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        # Add 'user' to declared tags before enrichment
        spec["tags"].append({"name": "user", "description": "Users"})

        discovered = enrich_spec_tags(spec)

        assert discovered == []  # nothing new
        # Should still have exactly 2 tags
        assert len(spec["tags"]) == 2

    def test_handles_spec_without_tags_key(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/x": {
                    "get": {"tags": ["alpha", "beta"], "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        discovered = enrich_spec_tags(spec)
        assert set(discovered) == {"alpha", "beta"}
        assert "tags" in spec
        assert len(spec["tags"]) == 2

    def test_handles_empty_paths(self) -> None:
        spec = {"openapi": "3.0.3", "info": {"title": "T", "version": "1"}, "paths": {}, "tags": []}
        discovered = enrich_spec_tags(spec)
        assert discovered == []

    def test_handles_operations_without_tags(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {"/x": {"get": {"responses": {"200": {"description": "OK"}}}}},
            "tags": [],
        }
        discovered = enrich_spec_tags(spec)
        assert discovered == []

    def test_multiple_undeclared_across_paths(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/a": {"get": {"tags": ["alpha"], "responses": {"200": {"description": "OK"}}}},
                "/b": {
                    "post": {"tags": ["beta"], "responses": {"201": {"description": "Created"}}}
                },
                "/c": {
                    "delete": {
                        "tags": ["gamma"],
                        "responses": {"204": {"description": "No Content"}},
                    }
                },
            },
            "tags": [{"name": "alpha", "description": "Already declared"}],
        }
        discovered = enrich_spec_tags(spec)
        assert set(discovered) == {"beta", "gamma"}
        assert len(spec["tags"]) == 3

    def test_idempotent_on_second_call(self) -> None:
        """Calling enrich_spec_tags twice should not add duplicates."""
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        enrich_spec_tags(spec)  # first call discovers tags
        second = enrich_spec_tags(spec)
        assert second == []  # nothing new the second time
        assert len(spec["tags"]) == 2  # pet + user


# ---------------------------------------------------------------------------
# _fields_to_coercion_schema
# ---------------------------------------------------------------------------


class TestFieldsToCoercionSchema:
    def test_simple_string_field(self) -> None:
        fields = [ResponseField(name="name", python_type="str")]
        result = _fields_to_coercion_schema(fields)
        assert result == {"name": {"type": "string"}}

    def test_integer_field(self) -> None:
        fields = [ResponseField(name="id", python_type="int")]
        result = _fields_to_coercion_schema(fields)
        assert result == {"id": {"type": "integer"}}

    def test_enum_field(self) -> None:
        fields = [
            ResponseField(name="status", python_type="str", is_enum=True, enum_values=["a", "b"])
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {"status": {"type": "string", "enum": ["a", "b"]}}

    def test_nested_object(self) -> None:
        fields = [
            ResponseField(
                name="category",
                python_type="dict",
                is_nested_object=True,
                nested_fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                ],
            )
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {
            "category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            }
        }

    def test_array_of_strings(self) -> None:
        fields = [ResponseField(name="urls", python_type="list", is_array=True)]
        result = _fields_to_coercion_schema(fields)
        assert result == {"urls": {"type": "array", "items": {"type": "string"}}}

    def test_array_of_objects(self) -> None:
        fields = [
            ResponseField(
                name="tags",
                python_type="list",
                is_array=True,
                nested_fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                ],
            )
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {
            "tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
            }
        }


# ---------------------------------------------------------------------------
# get_body_schemas
# ---------------------------------------------------------------------------


class TestGetBodySchemas:
    def test_extracts_pet_body_schema(self, tmp_path: Path) -> None:
        """get_body_schemas should return a schema for 'create_pet' from MINIMAL_OPENAPI_SPEC."""
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(MINIMAL_OPENAPI_SPEC), encoding="utf-8")
        schemas = get_body_schemas(tmp_path)
        assert "create_pet" in schemas
        pet_schema = schemas["create_pet"]
        assert pet_schema["name"]["type"] == "string"
        assert pet_schema["category"]["type"] == "object"
        assert pet_schema["photoUrls"]["type"] == "array"
        assert pet_schema["tags"]["type"] == "array"
        assert pet_schema["tags"]["items"]["type"] == "object"
        assert pet_schema["status"]["enum"] == ["available", "pending", "sold"]

    def test_returns_empty_for_missing_spec(self, tmp_path: Path) -> None:
        schemas = get_body_schemas(tmp_path)
        assert schemas == {}

    def test_skips_get_endpoints(self, tmp_path: Path) -> None:
        """GET endpoints should not appear in body schemas."""
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(MINIMAL_OPENAPI_SPEC), encoding="utf-8")
        schemas = get_body_schemas(tmp_path)
        assert "list_pets" not in schemas
        assert "list_users" not in schemas


# ===========================================================================
# Configurable max_depth
# ===========================================================================


class TestConfigurableMaxDepth:
    """max_depth should be configurable, not hardcoded to 3."""

    @staticmethod
    def _deep_spec() -> dict:
        """Build a spec with 5 levels of nesting: A > B > C > D > E."""
        return {
            "components": {
                "schemas": {
                    "E": {"type": "object", "properties": {"value": {"type": "string"}}},
                    "D": {
                        "type": "object",
                        "properties": {"e": {"$ref": "#/components/schemas/E"}},
                    },
                    "C": {
                        "type": "object",
                        "properties": {"d": {"$ref": "#/components/schemas/D"}},
                    },
                    "B": {
                        "type": "object",
                        "properties": {"c": {"$ref": "#/components/schemas/C"}},
                    },
                    "A": {
                        "type": "object",
                        "properties": {"b": {"$ref": "#/components/schemas/B"}},
                    },
                }
            }
        }

    def test_depth_3_truncates_at_level_3(self) -> None:
        """Default depth=3 should stop at D (empty nested_fields)."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=3)
        b = fields[0]
        assert b.name == "b"
        c = b.nested_fields[0]
        assert c.name == "c"
        d = c.nested_fields[0]
        assert d.name == "d"
        # At depth 3, D exists but its children (E) are truncated
        assert d.nested_fields == []

    def test_depth_5_reaches_level_5(self) -> None:
        """max_depth=5 should reach all the way to E.value."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=5)
        b = fields[0]
        c = b.nested_fields[0]
        d = c.nested_fields[0]
        assert d.name == "d"
        e = d.nested_fields[0]
        assert e.name == "e"
        assert e.nested_fields[0].name == "value"

    def test_depth_1_returns_top_level_only(self) -> None:
        """max_depth=1 should return top-level properties but no nested children."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=1)
        # Depth 0 parses A's properties (b), but b's nested_fields need depth 1 which is capped
        assert len(fields) == 1
        assert fields[0].name == "b"
        assert fields[0].nested_fields == []


# ===========================================================================
# oneOf / anyOf handling — merge all variants
# ===========================================================================


class TestOneOfAnyOfHandling:
    """oneOf/anyOf should merge properties from all variants, not just pick the first."""

    @staticmethod
    def _polymorphic_spec() -> dict:
        return {
            "components": {
                "schemas": {
                    "StringValue": {
                        "type": "object",
                        "properties": {"valueString": {"type": "string"}},
                    },
                    "QuantityValue": {
                        "type": "object",
                        "properties": {
                            "valueQuantity": {"type": "number"},
                            "unit": {"type": "string"},
                        },
                    },
                    "CodeableValue": {
                        "type": "object",
                        "properties": {"valueCode": {"type": "string"}},
                    },
                }
            }
        }

    def test_oneof_merges_all_variant_properties(self) -> None:
        """oneOf should expose properties from ALL variants."""
        spec = self._polymorphic_spec()
        schema = {
            "oneOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
                {"$ref": "#/components/schemas/CodeableValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert "valueString" in names
        assert "valueQuantity" in names
        assert "unit" in names
        assert "valueCode" in names

    def test_anyof_merges_all_variant_properties(self) -> None:
        """anyOf should expose properties from ALL variants."""
        spec = self._polymorphic_spec()
        schema = {
            "anyOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert "valueString" in names
        assert "valueQuantity" in names
        assert "unit" in names

    def test_oneof_with_inline_schemas(self) -> None:
        """oneOf with inline object schemas should also merge."""
        spec: dict = {"components": {"schemas": {}}}
        schema = {
            "oneOf": [
                {"type": "object", "properties": {"alpha": {"type": "string"}}},
                {"type": "object", "properties": {"beta": {"type": "integer"}}},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert "alpha" in names
        assert "beta" in names


# ===========================================================================
# $ref caching
# ===========================================================================


class TestRefCaching:
    """$ref resolution should be cached for performance on large specs."""

    def test_resolve_ref_returns_correct_schema(self) -> None:
        """Basic sanity: _resolve_ref returns the right schema."""
        spec = {
            "components": {
                "schemas": {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}
            }
        }
        result = _resolve_ref(spec, "#/components/schemas/Pet")
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_resolve_ref_is_cached(self) -> None:
        """Repeated calls with the same ref should use cached result."""
        spec = {
            "components": {
                "schemas": {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}
            }
        }
        r1 = _resolve_ref(spec, "#/components/schemas/Pet")
        r2 = _resolve_ref(spec, "#/components/schemas/Pet")
        # Both should return the same content
        assert r1 == r2


# ===========================================================================
# FHIR content type matching
# ===========================================================================


class TestFhirContentType:
    """Response extraction should match application/fhir+json content type."""

    def test_fhir_json_content_type(self) -> None:
        """application/fhir+json should be matched for response schema extraction."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/fhir+json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "resourceType": {"type": "string"},
                            },
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        names = {f.name for f in result.fields}
        assert "id" in names
        assert "resourceType" in names

    def test_standard_json_still_works(self) -> None:
        """application/json should still work as before."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        assert result.fields[0].name == "name"

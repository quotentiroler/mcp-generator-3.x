"""Tests for mcp_generator.introspection — tag auto-discovery and spec loading."""

import copy
import json
from pathlib import Path

from mcp_generator.introspection import (
    _fields_to_coercion_schema,
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

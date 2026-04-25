"""Tests for OpenAPI Overlay support."""

import copy
import json

import pytest

from mcp_generator.overlay import (
    BUNDLED_OVERLAYS,
    _parse_target,
    apply_overlay,
    generate_overlay,
    load_overlay,
    resolve_overlay_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Pet Store", "version": "1.0.0"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List pets",
                "description": "",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer"}},
                ],
            },
            "post": {
                "operationId": "createPet",
                "description": "Create a pet",
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPet",
                "parameters": [
                    {"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}},
                ],
            },
            "delete": {
                "operationId": "deletePet",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# _parse_target
# ---------------------------------------------------------------------------


class TestParseTarget:
    def test_simple_dot_path(self):
        assert _parse_target("$.info.title") == ["info", "title"]

    def test_bracket_string_key(self):
        assert _parse_target("$.paths['/pets'].get.description") == [
            "paths",
            "/pets",
            "get",
            "description",
        ]

    def test_bracket_integer_index(self):
        assert _parse_target("$.paths['/pets'].get.parameters[0].description") == [
            "paths",
            "/pets",
            "get",
            "parameters",
            0,
            "description",
        ]

    def test_leading_dollar_only(self):
        assert _parse_target("$.info") == ["info"]


# ---------------------------------------------------------------------------
# apply_overlay
# ---------------------------------------------------------------------------


class TestApplyOverlay:
    def test_update_description(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = {
            "overlay": "1.0.0",
            "info": {"title": "Test"},
            "actions": [
                {
                    "target": "$.paths['/pets'].get.description",
                    "update": "List all available pets.",
                }
            ],
        }
        result = apply_overlay(spec, overlay)
        assert result["paths"]["/pets"]["get"]["description"] == "List all available pets."

    def test_update_parameter_description(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = {
            "overlay": "1.0.0",
            "info": {"title": "Test"},
            "actions": [
                {
                    "target": "$.paths['/pets'].get.parameters[0].description",
                    "update": "Max results to return.",
                }
            ],
        }
        result = apply_overlay(spec, overlay)
        assert (
            result["paths"]["/pets"]["get"]["parameters"][0]["description"]
            == "Max results to return."
        )

    def test_remove_action(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = {
            "overlay": "1.0.0",
            "info": {"title": "Test"},
            "actions": [
                {
                    "target": "$.paths['/pets'].post.description",
                    "remove": True,
                }
            ],
        }
        result = apply_overlay(spec, overlay)
        assert "description" not in result["paths"]["/pets"]["post"]

    def test_empty_actions(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        original = copy.deepcopy(spec)
        overlay = {"overlay": "1.0.0", "info": {"title": "T"}, "actions": []}
        apply_overlay(spec, overlay)
        assert spec == original

    def test_invalid_target_graceful(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = {
            "overlay": "1.0.0",
            "info": {"title": "T"},
            "actions": [{"target": "$.nonexistent.deep.path", "update": "value"}],
        }
        # Should not raise — creates intermediate dicts
        apply_overlay(spec, overlay)
        assert spec["nonexistent"]["deep"]["path"] == "value"


# ---------------------------------------------------------------------------
# generate_overlay (auto-enhancement)
# ---------------------------------------------------------------------------


class TestGenerateOverlay:
    def test_generates_valid_overlay(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = generate_overlay(spec)
        assert overlay["overlay"] == "1.0.0"
        assert "actions" in overlay
        assert len(overlay["actions"]) > 0

    def test_enhances_empty_descriptions(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = generate_overlay(spec)
        # The GET /pets has empty description — should be enhanced
        targets = [a["target"] for a in overlay["actions"]]
        assert "$.paths['/pets'].get.description" in targets

    def test_enhances_missing_summaries(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = generate_overlay(spec)
        # DELETE /pets/{petId} has no summary
        targets = [a["target"] for a in overlay["actions"]]
        assert any("delete" in t and "summary" in t for t in targets)

    def test_enhances_missing_param_descriptions(self):
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = generate_overlay(spec)
        targets = [a["target"] for a in overlay["actions"]]
        # limit param has no description — should get enhanced
        assert any("parameters[0].description" in t and "/pets" in t for t in targets)

    def test_roundtrip_apply(self):
        """Generate overlay, apply it, verify descriptions are populated."""
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = generate_overlay(spec)
        apply_overlay(spec, overlay)
        # GET /pets should now have a non-empty description
        assert spec["paths"]["/pets"]["get"]["description"]
        # DELETE should have a summary
        assert spec["paths"]["/pets/{petId}"]["delete"].get("summary")


# ---------------------------------------------------------------------------
# load_overlay
# ---------------------------------------------------------------------------


class TestLoadOverlay:
    def test_load_json_overlay(self, tmp_path):
        overlay = {"overlay": "1.0.0", "info": {"title": "T"}, "actions": []}
        p = tmp_path / "overlay.json"
        p.write_text(json.dumps(overlay), encoding="utf-8")
        result = load_overlay(p)
        assert result["overlay"] == "1.0.0"

    def test_load_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_overlay(tmp_path / "nonexistent.json")

    def test_load_yaml_overlay(self, tmp_path):
        pytest.importorskip("yaml")
        content = "overlay: '1.0.0'\ninfo:\n  title: Test\nactions: []\n"
        p = tmp_path / "overlay.yaml"
        p.write_text(content, encoding="utf-8")
        result = load_overlay(p)
        assert result["overlay"] == "1.0.0"


# ---------------------------------------------------------------------------
# Bundled overlay resolution
# ---------------------------------------------------------------------------


class TestResolveOverlayPath:
    def test_bundled_name_resolves_to_file(self):
        """'fhir' should resolve to the bundled fhir.overlay.yaml."""
        path = resolve_overlay_path("fhir")
        assert path.name == "fhir.overlay.yaml"
        assert path.exists()

    def test_unknown_name_treated_as_path(self, tmp_path):
        """Non-bundled name is treated as a filesystem path."""
        overlay_file = tmp_path / "custom.overlay.yaml"
        path = resolve_overlay_path(str(overlay_file))
        assert path == overlay_file

    def test_all_bundled_overlays_exist(self):
        """Every entry in BUNDLED_OVERLAYS must point to an existing file."""
        for name, filename in BUNDLED_OVERLAYS.items():
            path = resolve_overlay_path(name)
            assert path.exists(), f"Bundled overlay '{name}' -> {filename} not found"


# ---------------------------------------------------------------------------
# FHIR overlay — structure and application
# ---------------------------------------------------------------------------

FHIR_SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "FHIR R4", "version": "4.0.1"},
    "paths": {
        "/metadata": {
            "get": {
                "operationId": "getMetadata",
                "summary": "",
                "description": "",
            }
        },
        "/Patient/{id}/$everything": {
            "get": {
                "operationId": "patientEverything",
                "summary": "",
                "description": "",
            }
        },
        "/": {
            "post": {
                "operationId": "batchTransaction",
                "summary": "",
                "description": "",
            }
        },
    },
    "components": {
        "parameters": {
            "_id": {"name": "_id", "in": "query", "schema": {"type": "string"}},
            "_lastUpdated": {
                "name": "_lastUpdated",
                "in": "query",
                "schema": {"type": "string"},
            },
            "_tag": {"name": "_tag", "in": "query", "schema": {"type": "string"}},
            "_profile": {"name": "_profile", "in": "query", "schema": {"type": "string"}},
            "_security": {"name": "_security", "in": "query", "schema": {"type": "string"}},
            "_count": {"name": "_count", "in": "query", "schema": {"type": "integer"}},
            "_sort": {"name": "_sort", "in": "query", "schema": {"type": "string"}},
            "_include": {"name": "_include", "in": "query", "schema": {"type": "string"}},
            "_revinclude": {
                "name": "_revinclude",
                "in": "query",
                "schema": {"type": "string"},
            },
            "_summary": {"name": "_summary", "in": "query", "schema": {"type": "string"}},
            "_elements": {"name": "_elements", "in": "query", "schema": {"type": "string"}},
            "_total": {"name": "_total", "in": "query", "schema": {"type": "string"}},
            "_contained": {
                "name": "_contained",
                "in": "query",
                "schema": {"type": "string"},
            },
            "patient": {"name": "patient", "in": "query", "schema": {"type": "string"}},
            "subject": {"name": "subject", "in": "query", "schema": {"type": "string"}},
            "date": {"name": "date", "in": "query", "schema": {"type": "string"}},
            "code": {"name": "code", "in": "query", "schema": {"type": "string"}},
            "status": {"name": "status", "in": "query", "schema": {"type": "string"}},
            "identifier": {"name": "identifier", "in": "query", "schema": {"type": "string"}},
            "category": {"name": "category", "in": "query", "schema": {"type": "string"}},
        },
        "schemas": {
            "Bundle": {"type": "object", "properties": {}},
            "OperationOutcome": {"type": "object", "properties": {}},
            "Reference": {"type": "object", "properties": {}},
            "CodeableConcept": {"type": "object", "properties": {}},
            "Coding": {"type": "object", "properties": {}},
            "Extension": {"type": "object", "properties": {}},
        },
    },
}


class TestFhirOverlay:
    """Tests that the bundled FHIR overlay loads, parses, and applies correctly."""

    def test_fhir_overlay_loads(self):
        """The bundled FHIR overlay must load without errors."""
        path = resolve_overlay_path("fhir")
        overlay = load_overlay(path)
        assert overlay["overlay"] == "1.0.0"
        assert overlay["info"]["title"].startswith("FHIR")
        assert len(overlay["actions"]) > 0

    def test_fhir_overlay_is_valid_overlay_spec(self):
        """All actions have target + (update or remove)."""
        path = resolve_overlay_path("fhir")
        overlay = load_overlay(path)
        for i, action in enumerate(overlay["actions"]):
            assert "target" in action, f"Action {i} missing target"
            assert "update" in action or "remove" in action, f"Action {i} has no update/remove"

    def test_fhir_overlay_enriches_metadata_endpoint(self):
        """After applying, /metadata GET should have a meaningful description."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        desc = spec["paths"]["/metadata"]["get"]["description"]
        assert "CapabilityStatement" in desc
        assert len(desc) > 50

    def test_fhir_overlay_enriches_everything_endpoint(self):
        """$everything should have agent-friendly description."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        desc = spec["paths"]["/Patient/{id}/$everything"]["get"]["description"]
        assert "Patient" in desc
        assert "Bundle" in desc

    def test_fhir_overlay_enriches_batch_endpoint(self):
        """POST / (batch/transaction) should have description."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        desc = spec["paths"]["/"]["post"]["description"]
        assert "batch" in desc.lower() or "transaction" in desc.lower()

    def test_fhir_overlay_enriches_search_params(self):
        """Common FHIR search params get descriptions."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        params = spec["components"]["parameters"]
        for name in ("_id", "_lastUpdated", "_count", "_sort", "_include", "_summary"):
            desc = params[name].get("description", "")
            assert len(desc) > 20, f"Parameter {name} should have a rich description, got: {desc!r}"

    def test_fhir_overlay_enriches_clinical_search_params(self):
        """Clinical search params (patient, code, date, status) get descriptions."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        params = spec["components"]["parameters"]
        for name in (
            "patient",
            "subject",
            "date",
            "code",
            "status",
            "identifier",
            "category",
        ):
            desc = params[name].get("description", "")
            assert len(desc) > 20, f"Parameter {name} missing rich description"

    def test_fhir_overlay_adds_schema_hints(self):
        """Key FHIR schemas should get x-mcp-hints after overlay."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        schemas = spec["components"]["schemas"]
        for schema_name in ("Bundle", "OperationOutcome", "Reference", "CodeableConcept"):
            hints = schemas[schema_name].get("x-mcp-hints", {})
            assert "description" in hints, (
                f"Schema {schema_name} should have x-mcp-hints.description"
            )

    def test_fhir_overlay_adds_info_hints(self):
        """Info section should get x-mcp-hints with domain metadata."""
        spec = copy.deepcopy(FHIR_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        apply_overlay(spec, overlay)
        hints = spec["info"].get("x-mcp-hints", {})
        assert hints.get("domain") == "healthcare"
        assert hints.get("recommended-schema-depth") == 5

    def test_fhir_overlay_does_not_break_non_fhir_spec(self):
        """Applying FHIR overlay to a non-FHIR spec should not raise."""
        spec = copy.deepcopy(SAMPLE_SPEC)
        overlay = load_overlay(resolve_overlay_path("fhir"))
        # Should not raise — targets that don't exist get auto-created
        apply_overlay(spec, overlay)
        # Original data should still be intact
        assert spec["paths"]["/pets"]["get"]["operationId"] == "listPets"

"""Tests for OpenAPI Overlay support."""

import copy
import json

import pytest

from mcp_generator.overlay import (
    _parse_target,
    apply_overlay,
    generate_overlay,
    load_overlay,
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

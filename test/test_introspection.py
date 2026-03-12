"""Tests for mcp_generator.introspection — tag auto-discovery and spec loading."""

import copy

from mcp_generator.introspection import enrich_spec_tags
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

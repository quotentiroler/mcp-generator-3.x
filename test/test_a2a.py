"""Tests for A2A agent generation."""

import json
import pytest

from mcp_generator.a2a import generate_agent_card, render_a2a_adapter
from mcp_generator.models import ApiMetadata, ModuleSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_metadata(**overrides) -> ApiMetadata:
    defaults = {
        "title": "Pet Store API",
        "description": "A sample pet store server.",
        "version": "1.0.0",
    }
    defaults.update(overrides)
    return ApiMetadata(**defaults)


def _make_modules() -> dict[str, ModuleSpec]:
    return {
        "pet": ModuleSpec(
            filename="pet_server.py",
            api_var_name="pet_api",
            api_class_name="PetApi",
            module_name="pet",
            tool_count=3,
            code="",
            tag_name="pet",
        ),
        "store": ModuleSpec(
            filename="store_server.py",
            api_var_name="store_api",
            api_class_name="StoreApi",
            module_name="store",
            tool_count=1,
            code="",
            tag_name="store",
        ),
    }


# ---------------------------------------------------------------------------
# generate_agent_card
# ---------------------------------------------------------------------------


class TestGenerateAgentCard:
    def test_basic_structure(self):
        card = generate_agent_card(_make_metadata(), _make_modules())
        assert card["name"] == "Pet Store API"
        assert card["version"] == "1.0.0"
        assert "capabilities" in card
        assert "skills" in card

    def test_skills_from_modules(self):
        card = generate_agent_card(_make_metadata(), _make_modules())
        skill_ids = [s["id"] for s in card["skills"]]
        assert "pet_skill" in skill_ids
        assert "store_skill" in skill_ids

    def test_skill_examples_from_tools(self):
        card = generate_agent_card(_make_metadata(), _make_modules())
        pet_skill = next(s for s in card["skills"] if s["id"] == "pet_skill")
        assert len(pet_skill["examples"]) > 0
        assert "pet" in pet_skill["description"].lower()

    def test_skill_tool_count_in_description(self):
        card = generate_agent_card(_make_metadata(), _make_modules())
        pet_skill = next(s for s in card["skills"] if s["id"] == "pet_skill")
        assert "3 tools" in pet_skill["description"]

    def test_custom_agent_url(self):
        card = generate_agent_card(
            _make_metadata(), _make_modules(), agent_url="https://my-agent.example.com"
        )
        assert card["url"] == "https://my-agent.example.com"

    def test_json_serialisable(self):
        card = generate_agent_card(_make_metadata(), _make_modules())
        serialised = json.dumps(card)
        assert isinstance(serialised, str)
        roundtrip = json.loads(serialised)
        assert roundtrip == card

    def test_empty_modules(self):
        card = generate_agent_card(_make_metadata(), {})
        assert card["skills"] == []


# ---------------------------------------------------------------------------
# render_a2a_adapter
# ---------------------------------------------------------------------------


class TestRenderA2AAdapter:
    def test_returns_valid_python(self):
        code = render_a2a_adapter(_make_metadata())
        # Should be parseable Python
        compile(code, "<a2a_adapter>", "exec")

    def test_contains_server_import(self):
        code = render_a2a_adapter(_make_metadata())
        assert "pet_store_api_mcp_generated" in code

    def test_contains_agent_card_loader(self):
        code = render_a2a_adapter(_make_metadata())
        assert "agent_card.json" in code

    def test_contains_cli_entrypoint(self):
        code = render_a2a_adapter(_make_metadata())
        assert "def main()" in code
        assert '__name__ == "__main__"' in code

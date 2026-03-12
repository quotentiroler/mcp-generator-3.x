"""Tests for mcp_generator.utils — name sanitization and helpers."""

import pytest

from mcp_generator.utils import (
    camel_to_snake,
    normalize_version,
    sanitize_name,
)

# ---------------------------------------------------------------------------
# camel_to_snake
# ---------------------------------------------------------------------------


class TestCamelToSnake:
    @pytest.mark.parametrize(
        "input_,expected",
        [
            ("PetApi", "pet_api"),
            ("UserApi", "user_api"),
            ("AccessControlApi", "access_control_api"),
            ("HTMLParser", "htmlparser"),  # consecutive caps stay grouped
            ("already_snake", "already_snake"),
            ("lowercase", "lowercase"),
            ("getHTTPResponse", "get_httpresponse"),
            ("SimpleXML", "simple_xml"),
        ],
    )
    def test_basic_conversions(self, input_: str, expected: str) -> None:
        assert camel_to_snake(input_) == expected


# ---------------------------------------------------------------------------
# sanitize_name
# ---------------------------------------------------------------------------


class TestSanitizeName:
    def test_get_collection_becomes_list(self) -> None:
        assert sanitize_name("get_users") == "list_users"

    def test_get_by_id_stays_get(self) -> None:
        assert sanitize_name("get_user_by_id") == "get_user_by_id"

    def test_post_becomes_create(self) -> None:
        assert sanitize_name("post_pets") == "create_pets"

    def test_put_becomes_replace(self) -> None:
        assert sanitize_name("put_user_by_id") == "replace_user_by_id"

    def test_patch_becomes_update(self) -> None:
        assert sanitize_name("patch_user_by_id") == "update_user_by_id"

    def test_delete_stays_delete(self) -> None:
        assert sanitize_name("delete_user_by_id") == "delete_user_by_id"

    def test_no_verb_prefix_unchanged(self) -> None:
        # Names that don't start with an HTTP verb are kept (lowercased)
        assert sanitize_name("find_pet") == "find_pet"

    def test_camelcase_converted(self) -> None:
        # get_ without _by_ maps to list_, then camelCase is snake_cased
        assert sanitize_name("get_petById") == "list_pet_by_id"


# ---------------------------------------------------------------------------
# normalize_version
# ---------------------------------------------------------------------------


class TestNormalizeVersion:
    def test_plain_version_untouched(self) -> None:
        assert normalize_version("1.2.3") == "1.2.3"

    def test_alpha_prerelease(self) -> None:
        result = normalize_version("0.0.1-alpha.202510200205.3df5db6a")
        assert result == "0.0.1a0+202510200205.3df5db6a"

    def test_beta_prerelease(self) -> None:
        result = normalize_version("1.0.0-beta.123")
        assert result == "1.0.0b0+123"

    def test_rc_prerelease(self) -> None:
        result = normalize_version("2.0.0-rc.1")
        assert result == "2.0.0rc0+1"

    def test_no_match_passthrough(self) -> None:
        assert normalize_version("latest") == "latest"

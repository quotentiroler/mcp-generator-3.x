"""
OpenAPI Overlay support.

Applies OpenAPI Overlay 1.0.0 specifications to enrich API descriptions
before MCP server generation. Supports both user-provided overlays and
rule-based auto-enhancement.

See: https://github.com/OAI/Overlay-Specification
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_overlay(overlay_path: Path) -> dict[str, Any]:
    """Load an overlay file (JSON or YAML).

    Args:
        overlay_path: Path to the overlay specification file.

    Returns:
        Parsed overlay as a dictionary.

    Raises:
        FileNotFoundError: If the overlay file does not exist.
        ValueError: If the overlay cannot be parsed or is not a valid Overlay 1.0.0 document.
    """
    if not overlay_path.exists():
        raise FileNotFoundError(f"Overlay file not found: {overlay_path}")

    text = overlay_path.read_text(encoding="utf-8")

    # Try JSON first, then YAML
    try:
        overlay = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml

            overlay = yaml.safe_load(text)
        except ImportError as exc:
            raise ValueError("YAML overlay requires PyYAML: pip install pyyaml") from exc

    if not isinstance(overlay, dict):
        raise ValueError("Overlay file must be a JSON/YAML object")

    version = overlay.get("overlay", "")
    if not version.startswith("1.0"):
        logger.warning("Overlay version %r is not 1.0.x — proceeding anyway", version)

    return overlay


# ---------------------------------------------------------------------------
# JSONPath-lite resolver (no external dependencies)
# ---------------------------------------------------------------------------

_BRACKET_RE = re.compile(r"\['([^']+)'\]|\[(\d+)\]")


def _parse_target(target: str) -> list[str | int]:
    """Parse a JSONPath target into a list of path segments.

    Supports ``$.paths['/pet'].get.description`` style expressions.
    Only simple dot-notation + bracket-access is handled (no wildcards/filters).
    """
    # Strip leading $. or $
    path = target.lstrip("$").lstrip(".")

    segments: list[str | int] = []
    i = 0
    while i < len(path):
        if path[i] == "[":
            m = _BRACKET_RE.match(path, i)
            if not m:
                raise ValueError(f"Malformed bracket expression at position {i} in: {target}")
            # String key or integer index
            if m.group(1) is not None:
                segments.append(m.group(1))
            else:
                segments.append(int(m.group(2)))
            i = m.end()
            # Skip trailing dot if present
            if i < len(path) and path[i] == ".":
                i += 1
        elif path[i] == ".":
            i += 1
        else:
            # Read until next dot or bracket
            end = i
            while end < len(path) and path[end] not in (".", "["):
                end += 1
            segments.append(path[i:end])
            i = end

    return segments


def _resolve(obj: Any, segments: list[str | int]) -> tuple[Any, str | int]:
    """Walk *obj* down *segments[:-1]* and return ``(parent, last_key)``.

    Creates intermediate dicts/lists as needed for ``update`` actions.
    """
    current = obj
    for seg in segments[:-1]:
        if isinstance(seg, int):
            if isinstance(current, list):
                while len(current) <= seg:
                    current.append({})
                current = current[seg]
            else:
                raise KeyError(f"Expected list for index {seg}, got {type(current).__name__}")
        else:
            if seg not in current:
                current[seg] = {}
            current = current[seg]
    return current, segments[-1]


# ---------------------------------------------------------------------------
# Apply overlay
# ---------------------------------------------------------------------------


def apply_overlay(spec: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Apply all overlay actions to a **mutable** copy of an OpenAPI spec.

    Supported action types:
    - ``update``: Sets the value at the target JSONPath.
    - ``remove``: Removes the value at the target JSONPath.

    Args:
        spec: The OpenAPI specification (will be mutated in-place).
        overlay: Parsed Overlay 1.0.0 document.

    Returns:
        The modified spec (same object, returned for convenience).
    """
    actions = overlay.get("actions", [])
    applied = 0

    for idx, action in enumerate(actions):
        target = action.get("target")
        if not target:
            logger.warning("Overlay action %d missing 'target', skipping", idx)
            continue

        try:
            segments = _parse_target(target)
            if not segments:
                continue

            if "update" in action:
                parent, key = _resolve(spec, segments)
                if isinstance(parent, list) and isinstance(key, int):
                    while len(parent) <= key:
                        parent.append(None)
                    parent[key] = action["update"]
                else:
                    parent[key] = action["update"]
                applied += 1

            elif "remove" in action:
                parent, key = _resolve(spec, segments)
                if isinstance(parent, dict) and key in parent:
                    del parent[key]
                    applied += 1
                elif isinstance(parent, list) and isinstance(key, int) and key < len(parent):
                    parent.pop(key)
                    applied += 1

        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Overlay action %d failed for target %r: %s", idx, target, exc)

    logger.info("Applied %d/%d overlay actions", applied, len(actions))
    return spec


# ---------------------------------------------------------------------------
# Rule-based auto-enhancement (no LLM dependency)
# ---------------------------------------------------------------------------


def generate_overlay(spec: dict[str, Any]) -> dict[str, Any]:
    """Generate a rule-based overlay that enriches OpenAPI descriptions for AI agents.

    Improves tool descriptions and parameter docs using pattern-based heuristics.
    No LLM call — fully deterministic and offline.

    Args:
        spec: Parsed OpenAPI specification.

    Returns:
        An Overlay 1.0.0 document.
    """
    title = spec.get("info", {}).get("title", "API")
    overlay: dict[str, Any] = {
        "overlay": "1.0.0",
        "info": {
            "title": f"MCP Agent Enhancement Overlay for {title}",
            "version": "1.0.0",
        },
        "actions": [],
    }

    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            desc = operation.get("description", "")
            summary = operation.get("summary", "")
            purpose = _infer_purpose(method, path, operation)

            # Enhance description if missing or shorter than purpose
            if not desc or len(desc) < len(purpose):
                overlay["actions"].append(
                    {
                        "target": f"$.paths['{path}'].{method}.description",
                        "update": purpose,
                    }
                )

            # Add summary if missing
            if not summary:
                overlay["actions"].append(
                    {
                        "target": f"$.paths['{path}'].{method}.summary",
                        "update": purpose[:120],
                    }
                )

            # Enhance parameter descriptions
            for idx, param in enumerate(operation.get("parameters", [])):
                if "$ref" in param:
                    continue
                if not param.get("description"):
                    enhanced = _enhance_param(param)
                    if enhanced:
                        overlay["actions"].append(
                            {
                                "target": f"$.paths['{path}'].{method}.parameters[{idx}].description",
                                "update": enhanced,
                            }
                        )

    logger.info("Generated overlay with %d actions for %s", len(overlay["actions"]), title)
    return overlay


def _infer_purpose(method: str, path: str, operation: dict[str, Any]) -> str:
    """Infer a concise, agent-friendly description for an operation."""
    op_id = (operation.get("operationId") or "").lower()
    summary = operation.get("summary", "")

    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    resource = parts[-1] if parts else "resource"

    m = method.lower()
    if m == "get":
        if "{" in path:
            return f"Retrieve details of a specific {resource}."
        return f"List or query {resource}."
    if m == "post":
        if "search" in op_id or "query" in op_id:
            return f"Search or query {resource}."
        return f"Create a new {resource}."
    if m == "put":
        return f"Update or replace a {resource}."
    if m == "patch":
        return f"Partially update a {resource}."
    if m == "delete":
        return f"Delete a {resource}."

    return summary or f"Perform {method.upper()} operation on {path}."


_PARAM_HINTS: dict[str, str] = {
    "limit": "Maximum number of results to return.",
    "offset": "Number of results to skip for pagination.",
    "page": "Page number for pagination.",
    "sort": "Field to sort results by.",
    "order": "Sort order: 'asc' or 'desc'.",
    "filter": "Filter expression to narrow results.",
    "q": "Free-text search query.",
    "query": "Free-text search query.",
    "search": "Free-text search query.",
    "fields": "Comma-separated list of fields to include in the response.",
    "expand": "Related resources to expand inline.",
    "include": "Related resources to include.",
}


def _enhance_param(param: dict[str, Any]) -> str:
    """Generate an enhanced description for a parameter."""
    name = param.get("name", "").lower()
    required = param.get("required", False)
    schema = param.get("schema", {})
    param_type = schema.get("type", param.get("type", "string"))

    # Check known patterns
    for keyword, hint in _PARAM_HINTS.items():
        if keyword in name:
            return hint

    # Fallback
    prefix = "Required" if required else "Optional"
    return f"{prefix} {param_type} parameter."

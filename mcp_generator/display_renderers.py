"""
Display tool code generation from OpenAPI response schemas.

Generates per-tag display modules (e.g. pet_display.py, store_display.py)
that render API responses as interactive Prefab UI components.
"""

from __future__ import annotations

from .models import DisplayEndpoint, ResponseField
from .utils import camel_to_snake

# ---------------------------------------------------------------------------
# Badge variant mapping for common status/enum patterns
# ---------------------------------------------------------------------------
_STATUS_VARIANTS: dict[str, str] = {
    "available": "success",
    "active": "success",
    "enabled": "success",
    "approved": "success",
    "delivered": "success",
    "complete": "success",
    "completed": "success",
    "pending": "warning",
    "processing": "warning",
    "in_progress": "warning",
    "placed": "warning",
    "sold": "error",
    "inactive": "error",
    "disabled": "error",
    "deleted": "error",
    "cancelled": "error",
    "rejected": "error",
    "failed": "error",
}


def _param_type_hint(param: dict) -> str:
    """Convert an OpenAPI parameter schema to a Python type hint."""
    schema = param.get("schema", {})
    mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
    }
    base = mapping.get(schema.get("type", "string"), "str")
    if not param.get("required", False):
        return f"{base} | None = None"
    return base


def _tool_name_for_endpoint(endpoint: DisplayEndpoint) -> str:
    """Generate a display tool function name from an endpoint.

    Uses the operation_id to guarantee uniqueness across endpoints.
    """
    base = camel_to_snake(endpoint.operation_id)
    schema = endpoint.response_schema
    if schema is None:
        return f"view_{base}"

    if schema.is_array:
        return f"view_{base}_table"
    return f"view_{base}_detail"


def _flat_field_key(field: ResponseField) -> str:
    """Get the dict key for accessing this field in a result dict."""
    return field.name


def _table_columns_for_fields(fields: list[ResponseField]) -> list[dict[str, str]]:
    """Select which fields to show as table columns (skip deeply nested, arrays)."""
    columns = []
    for f in fields:
        if f.is_array or f.is_nested_object:
            continue
        label = f.name.replace("_", " ").title()
        columns.append({"key": f.name, "label": label})
    return columns


# ---------------------------------------------------------------------------
# Code generation: detail view
# ---------------------------------------------------------------------------


def _render_detail_tool(endpoint: DisplayEndpoint, api_var_name: str) -> str:
    """Generate a display tool that shows a single object as a detail card."""
    schema = endpoint.response_schema
    if schema is None:
        return ""

    func_name = _tool_name_for_endpoint(endpoint)
    summary = endpoint.summary or f"View {schema.schema_name or 'record'} details"

    # Build function parameters from path + query params
    params = []
    call_args = []
    for p in endpoint.path_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{p['name']}={p['name']}")
    for p in endpoint.query_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{p['name']}={p['name']}")

    params_str = ", ".join(params)
    call_args_str = ", ".join(call_args)

    # Find the API method name from operation_id
    method_name = camel_to_snake(endpoint.operation_id)

    # Build field rendering lines
    field_lines = _render_detail_fields(schema.fields)

    # Determine a title expression
    title_field = _find_title_field(schema.fields)
    if title_field:
        title_expr = (
            f"f\"{schema.schema_name or 'Detail'}: {{result.get('{title_field}', 'Unknown')}}\""
        )
    else:
        title_expr = f'"{schema.schema_name or "Detail"}"'

    code = f'''
@mcp.tool(
    app=True if PREFAB_AVAILABLE else False,
    tags=["display", "{endpoint.tag}"],
    description="""{summary}""",
)
def {func_name}({params_str}) -> Any:
    """{summary}"""
    try:
        result = _call_api("{method_name}", {api_var_name}, {call_args_str})
    except Exception as e:
        if not PREFAB_AVAILABLE:
            return {{"error": str(e)}}
        with Column(gap=4, css_class="p-6") as view:
            Heading("Error")
            Badge(str(e), variant="error")
        return PrefabApp(view=view)

    if not PREFAB_AVAILABLE:
        return result

    with Column(gap=5, css_class="p-6 max-w-2xl") as view:
        Heading({title_expr})
        with Card():
            with CardContent(css_class="py-4"):
{field_lines}
    return PrefabApp(view=view)
'''
    return code


def _find_title_field(fields: list[ResponseField]) -> str | None:
    """Find the best field to use as a display title (name, title, username, etc.)."""
    priority = ["name", "title", "username", "display_name", "label", "email"]
    field_names = {f.name for f in fields}
    for candidate in priority:
        if candidate in field_names:
            return candidate
    return None


def _render_detail_fields(fields: list[ResponseField], indent: int = 16) -> str:
    """Generate Prefab code lines for displaying fields in a detail card."""
    pad = " " * indent
    lines = []
    shown = 0
    for _i, f in enumerate(fields):
        if f.is_array or f.is_nested_object:
            continue
        if shown > 0:
            lines.append(f"{pad}Separator()")

        lines.append(f'{pad}with Row(gap=4, align="center", css_class="py-2"):')
        label = f.name.replace("_", " ").title()
        lines.append(
            f'{pad}    Text("{label}", css_class="font-medium text-muted-foreground w-40 shrink-0")'
        )

        if f.is_enum:
            # Use Badge with variant mapping
            lines.append(f'{pad}    _val = str(result.get("{f.name}", ""))')
            lines.append(
                f'{pad}    Badge(_val, variant=_STATUS_VARIANTS.get(_val.lower(), "outline"))'
            )
        elif f.python_type == "bool":
            lines.append(f'{pad}    _val = result.get("{f.name}", False)')
            lines.append(
                f'{pad}    Badge("Yes" if _val else "No", variant="success" if _val else "outline")'
            )
        elif f.format in ("date-time", "date"):
            lines.append(
                f'{pad}    Text(str(result.get("{f.name}", "")), css_class="font-medium tabular-nums")'
            )
        else:
            lines.append(f'{pad}    Text(str(result.get("{f.name}", "")), css_class="font-medium")')
        shown += 1

    # Handle nested objects as sub-sections
    for f in fields:
        if f.is_nested_object and f.nested_fields:
            label = f.name.replace("_", " ").title()
            lines.append(f"{pad}Separator()")
            lines.append(f'{pad}with Row(gap=4, align="center", css_class="py-2"):')
            lines.append(
                f'{pad}    Text("{label}", css_class="font-medium text-muted-foreground w-40 shrink-0")'
            )
            # Show nested object's displayable fields inline
            sub_val = f'result.get("{f.name}", {{}})'
            for nf in f.nested_fields:
                if nf.is_array or nf.is_nested_object:
                    continue
                lines.append(
                    f'{pad}    Text(str(({sub_val}).get("{nf.name}", "")), css_class="font-medium")'
                )
                break  # Show first field inline

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Code generation: table view
# ---------------------------------------------------------------------------


def _render_table_tool(endpoint: DisplayEndpoint, api_var_name: str) -> str:
    """Generate a display tool that shows an array response as a DataTable."""
    schema = endpoint.response_schema
    if schema is None:
        return ""

    func_name = _tool_name_for_endpoint(endpoint)
    summary = endpoint.summary or f"View {schema.schema_name or 'records'} as table"

    # Build function parameters from query params only (tables are list endpoints)
    params = []
    call_args = []
    for p in endpoint.path_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{p['name']}={p['name']}")
    for p in endpoint.query_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{p['name']}={p['name']}")

    params_str = ", ".join(params)
    call_args_str = ", ".join(call_args)
    method_name = camel_to_snake(endpoint.operation_id)

    # Build column definitions
    columns = _table_columns_for_fields(schema.fields)
    col_lines = []
    for c in columns:
        col_lines.append(
            f'            DataTableColumn(key="{c["key"]}", header="{c["label"]}", sortable=True),'
        )
    columns_code = "\n".join(col_lines)

    heading_text = schema.schema_name or endpoint.tag.title()
    if not heading_text.endswith("s"):
        heading_text += "s"

    code = f'''
@mcp.tool(
    app=True if PREFAB_AVAILABLE else False,
    tags=["display", "{endpoint.tag}"],
    description="""{summary}""",
)
def {func_name}({params_str}) -> Any:
    """{summary}"""
    try:
        results = _call_api("{method_name}", {api_var_name}, {call_args_str})
    except Exception as e:
        if not PREFAB_AVAILABLE:
            return {{"error": str(e)}}
        with Column(gap=4, css_class="p-6") as view:
            Heading("Error")
            Badge(str(e), variant="error")
        return PrefabApp(view=view)

    if not isinstance(results, list):
        results = [results] if results else []

    if not PREFAB_AVAILABLE:
        return {{"title": "{heading_text}", "count": len(results), "rows": results}}

    with Column(gap=5, css_class="p-6 max-w-4xl") as view:
        Heading("{heading_text}")
        with Row(gap=2, align="center"):
            Badge(f"{{len(results)}} records", variant="outline")
        DataTable(
            rows=results,
            columns=[
{columns_code}
            ],
            search=True,
        )
    return PrefabApp(view=view)
'''
    return code


# ---------------------------------------------------------------------------
# Module assembly
# ---------------------------------------------------------------------------


def render_display_module(
    tag: str,
    endpoints: list[DisplayEndpoint],
    api_var_name: str,
    api_class_name: str,
) -> str:
    """Generate a complete display module file for a tag (e.g. pet_display.py).

    Args:
        tag: The OpenAPI tag (e.g. "pet")
        endpoints: Display endpoints belonging to this tag
        api_var_name: API variable name (e.g. "pet_api")
        api_class_name: API class name (e.g. "PetApi")
    """
    module_name = tag.title().replace("_", "")

    tool_code_blocks = []
    for ep in endpoints:
        schema = ep.response_schema
        if schema is None:
            continue
        if schema.is_array:
            tool_code_blocks.append(_render_table_tool(ep, api_var_name))
        elif schema.is_object:
            tool_code_blocks.append(_render_detail_tool(ep, api_var_name))

    if not tool_code_blocks:
        return ""

    tools_code = "\n".join(tool_code_blocks)
    variants_repr = repr(_STATUS_VARIANTS)

    header = f'''"""
{module_name} Display Tools — API-specific UI views.

Auto-generated from OpenAPI response schemas.
DO NOT EDIT MANUALLY — regenerate using: generate-mcp --enable-apps --generate-ui
"""

import logging
import os
from typing import Any
import sys
from pathlib import Path

from fastmcp import FastMCP

# Add the generated folder to the Python path
generated_path = Path(__file__).parent.parent.parent / "generated_openapi"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

from openapi_client import ApiClient, ApiException, Configuration, {api_class_name}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional Prefab imports
# ---------------------------------------------------------------------------
try:
    from prefab_ui.app import PrefabApp
    from prefab_ui.components import (
        Badge,
        Card,
        CardContent,
        Column,
        DataTable,
        DataTableColumn,
        Heading,
        Metric,
        Muted,
        Row,
        Separator,
        Text,
    )
    PREFAB_AVAILABLE = True
except ImportError:
    PREFAB_AVAILABLE = False

# Badge variant mapping for status / enum values
_STATUS_VARIANTS = {variants_repr}

mcp = FastMCP("{module_name}Display")
'''

    # The _call_api helper uses dict comprehension, so avoid f-string for that part
    helper = """
def _call_api(method_name: str, api_instance, **kwargs):
    \"\"\"Call an API method, strip None kwargs, convert result to dict.\"\"\"
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    method = getattr(api_instance, method_name)
    result = method(**filtered)
    if isinstance(result, list):
        return [item.to_dict() if hasattr(item, "to_dict") else item for item in result]
    return result.to_dict() if hasattr(result, "to_dict") else result

"""

    init_code = f"""
def _get_api():
    \"\"\"Get an API instance using environment-based auth.\"\"\"
    config = Configuration()
    base_url = os.environ.get("BACKEND_BASE_URL", "")
    if base_url:
        config.host = base_url
    token = os.environ.get("BACKEND_API_TOKEN", "")
    if token:
        config.access_token = token
    client = ApiClient(config)
    return {api_class_name}(client)

{api_var_name} = _get_api()

# ============================================================================
# Generated display tools
# ============================================================================
"""

    return header + helper + init_code + tools_code + "\n"

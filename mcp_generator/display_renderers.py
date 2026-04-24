"""
Display tool code generation from OpenAPI response schemas.

Generates per-tag display modules (e.g. pet_display.py, store_display.py)
that render API responses as interactive Prefab UI components.
"""

from __future__ import annotations

from .display_helpers import (
    STATUS_VARIANTS,
    find_title_field,
    render_detail_fields,
    render_detail_tabs,
    render_expandable_detail,
    table_columns_for_fields,
)
from .models import DeleteEndpoint, DisplayEndpoint, FormEndpoint, ResponseField
from .utils import camel_to_snake


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
    # Tool params keep original OpenAPI names (e.g. petId) for the MCP schema,
    # but API call kwargs use snake_case (e.g. pet_id) to match the generated client.
    params = []
    call_args = []
    for p in endpoint.path_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{camel_to_snake(p['name'])}={p['name']}")
    for p in endpoint.query_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{camel_to_snake(p['name'])}={p['name']}")

    params_str = ", ".join(params)
    call_args_str = ", ".join(call_args)

    # Find the API method name from operation_id
    method_name = camel_to_snake(endpoint.operation_id)

    # Build field rendering lines
    field_lines = render_detail_fields(schema.fields)

    # Build tabbed sections for nested objects and arrays
    tab_section = render_detail_tabs(schema.fields)

    # Determine a title expression
    title_field = find_title_field(schema.fields)
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

    if result is None:
        msg = "No record found."
        if not PREFAB_AVAILABLE:
            return {{"error": msg}}
        with Column(gap=4, css_class="p-6") as view:
            Heading("Not Found")
            Badge(msg, variant="warning")
        return PrefabApp(view=view)

    if not PREFAB_AVAILABLE:
        return result

    with Column(gap=5, css_class="p-6 max-w-2xl") as view:
        Heading({title_expr})
        with Card():
            with CardContent(css_class="py-4"):
{field_lines}
{tab_section}
    return PrefabApp(view=view)
'''
    return code





# ---------------------------------------------------------------------------
# Code generation: table view
# ---------------------------------------------------------------------------


def _render_table_tool(endpoint: DisplayEndpoint, api_var_name: str) -> str:
    """Generate a display tool that shows an array response as a DataTable.

    Includes ExpandableRow when the schema has fields beyond the visible columns
    (nested objects, arrays, or more than 5 flat fields).
    """
    schema = endpoint.response_schema
    if schema is None:
        return ""

    func_name = _tool_name_for_endpoint(endpoint)
    summary = endpoint.summary or f"View {schema.schema_name or 'records'} as table"

    params = []
    call_args = []
    for p in endpoint.path_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{camel_to_snake(p['name'])}={p['name']}")
    for p in endpoint.query_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args.append(f"{camel_to_snake(p['name'])}={p['name']}")

    params_str = ", ".join(params)
    call_args_str = ", ".join(call_args)
    method_name = camel_to_snake(endpoint.operation_id)

    columns = table_columns_for_fields(schema.fields)
    col_lines = []
    for c in columns:
        col_lines.append(
            f'            DataTableColumn(key="{c["key"]}", header="{c["label"]}", sortable=True),'
        )
    columns_code = "\n".join(col_lines)

    heading_text = schema.schema_name or endpoint.tag.title()
    if not heading_text.endswith("s"):
        heading_text += "s"

    # Determine if rows should be expandable (has nested/array fields or many flat fields)
    has_nested = any(f.is_nested_object or f.is_array for f in schema.fields)
    shown_col_keys = {c["key"] for c in columns}
    hidden_flat = [f for f in schema.fields if not f.is_array and not f.is_nested_object and f.name not in shown_col_keys]
    use_expandable = has_nested or len(hidden_flat) > 0

    if use_expandable:
        # Build the detail component for expanded rows
        detail_lines = render_expandable_detail(schema.fields, shown_col_keys)
        rows_code = f'''    _rows = []
    for _r in results:
        _rows.append(ExpandableRow(_r, detail=_build_{func_name}_detail(_r)))
'''
        detail_helper = f'''
def _build_{func_name}_detail(row: dict) -> Any:
    """Build expanded detail view for a table row."""
    with Column(gap=3, css_class="p-4") as detail:
{detail_lines}
    return detail
'''
        rows_ref = "_rows"
    else:
        rows_code = ""
        detail_helper = ""
        rows_ref = "results"

    # Build CallTool arguments for auto-refresh (forward path/query params)
    all_param_names = [p["name"] for p in endpoint.path_params] + [
        p["name"] for p in endpoint.query_params
    ]
    if all_param_names:
        refresh_args = {name: name for name in all_param_names}
        call_tool_args = f", arguments={repr(refresh_args)}"
    else:
        call_tool_args = ""

    code = f'''{detail_helper}
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

{rows_code}
    with Column(gap=5, css_class="p-6 max-w-4xl", let={{"auto_refresh": False}}) as view:
        with Row(gap=3, align="center", justify="between"):
            Heading("{heading_text}")
            Button(
                "Auto-refresh",
                variant="outline",
                size="sm",
                on_click=[
                    SetState(key="auto_refresh", value=True),
                    SetInterval(
                        30000,
                        on_tick=CallTool("{func_name}"{call_tool_args}),
                        while_=STATE.auto_refresh,
                    ),
                ],
                disabled=STATE.auto_refresh,
            )
        with Row(gap=2, align="center"):
            Badge(f"{{len(results)}} records", variant="outline")
            with If(STATE.auto_refresh):
                Badge("Live", variant="success")
        DataTable(
            rows={rows_ref},
            columns=[
{columns_code}
            ],
            search=True,
        )
    return PrefabApp(view=view)
'''
    return code


# ---------------------------------------------------------------------------
# Code generation: Pydantic models + Form.from_model() tools
# ---------------------------------------------------------------------------

_FIELD_TYPE_MAP: dict[str, str] = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "list": "list",
    "dict": "dict",
}


def _pydantic_field_def(field: ResponseField, required_fields: list[str]) -> str:
    """Generate a single Pydantic Field() definition from a ResponseField."""
    ftype = _FIELD_TYPE_MAP.get(field.python_type, "str")
    is_required = field.name in required_fields

    kwargs: list[str] = []

    # Title for form label
    label = field.name.replace("_", " ").title()
    kwargs.append(f'title="{label}"')

    # Description for placeholder
    if field.description:
        safe_desc = field.description.replace('"', '\\"')
        kwargs.append(f'description="{safe_desc}"')

    # Default value for optional fields
    if not is_required:
        kwargs.append("default=None")
        ftype = f"{ftype} | None"

    # Enum → Literal type
    if field.is_enum and field.enum_values:
        vals = ", ".join(f'"{v}"' for v in field.enum_values)
        ftype = f"Literal[{vals}]"
        if not is_required:
            ftype = f"Literal[{vals}] | None"

    kwargs_str = ", ".join(kwargs)
    return f"    {field.name}: {ftype} = Field({kwargs_str})"


def _render_pydantic_model(form: FormEndpoint) -> str:
    """Generate a Pydantic model class from a FormEndpoint's fields."""
    # Use operation_id to ensure uniqueness (same schema can be used by add/update)
    op_name = camel_to_snake(form.operation_id).title().replace("_", "")
    class_name = f"{op_name}Form"

    field_lines = []
    for f in form.fields:
        # Skip arrays and nested objects — Form.from_model can't handle them
        if f.is_array or f.is_nested_object:
            continue
        field_lines.append(_pydantic_field_def(f, form.required_fields))

    if not field_lines:
        return ""

    fields_code = "\n".join(field_lines)
    return f'''
class {class_name}(BaseModel):
    """{form.summary or f"{form.schema_name} form data."}"""
{fields_code}
'''


def _render_form_tool(form: FormEndpoint) -> str:
    """Generate a display tool that renders a manual form for a POST/PUT endpoint.

    Produces a form with:
    - Loading state (``submitting``) that disables the button during submission
    - ``CallTool`` wrapped in a ``SetState`` action chain
    - ``ShowToast`` on success / error
    - ``Select`` dropdowns for enum fields
    - Body coercion via the ``data`` key
    """
    func_name = f"form_{camel_to_snake(form.operation_id)}"
    summary = form.summary or f"Submit {form.schema_name or 'data'}"
    action = "Create" if form.http_method == "post" else "Update"
    submit_label = f"{action} {form.schema_name}" if form.schema_name else "Submit"

    # Build field rendering lines and data payload bindings
    field_lines: list[str] = []
    data_bindings: dict[str, str] = {}
    pad = " " * 24  # indentation inside Column(gap=4)

    for f in form.fields:
        if f.is_array or f.is_nested_object:
            continue

        data_bindings[f.name] = "{{ " + f.name + " }}"
        label = f.name.replace("_", " ").title()
        is_required = f.name in form.required_fields

        if f.is_enum and f.enum_values:
            field_lines.append(
                f'{pad}with Select(name="{f.name}", placeholder="{label}"):'
            )
            for val in f.enum_values:
                field_lines.append(
                    f'{pad}    SelectOption(value="{val}", label="{val}")'
                )
        else:
            input_type = "number" if f.python_type in ("int", "float") else "text"
            field_lines.append(
                f'{pad}Input(name="{f.name}", input_type="{input_type}", '
                f'placeholder="{label}", required={is_required})'
            )

    if not field_lines:
        return ""

    fields_code = "\n".join(field_lines)
    data_payload = repr(data_bindings)

    # Escape braces for f-string: {{ → literal {
    code = f'''
@mcp.tool(
    app=True if PREFAB_AVAILABLE else False,
    tags=["display", "{form.tag}"],
    description="""{summary}""",
)
def {func_name}() -> Any:
    """{summary}"""
    if not PREFAB_AVAILABLE:
        return {{"form": "{form.schema_name}", "submit_tool": "{form.tool_name}"}}

    with Column(gap=5, css_class="p-6 max-w-2xl") as view:
        Heading("{summary}")
        with Card():
            with CardContent(css_class="py-4"):
                with Form(
                    let={{"submitting": False}},
                    on_submit=[
                        SetState(key="submitting", value=True),
                        CallTool(
                            "{form.tool_name}",
                            arguments={{"data": {data_payload}}},
                            on_success=[
                                SetState(key="submitting", value=False),
                                ShowToast("Submitted successfully!", variant="success"),
                            ],
                            on_error=[
                                SetState(key="submitting", value=False),
                                ShowToast("Something went wrong", variant="error"),
                            ],
                        ),
                    ],
                ):
                    with Column(gap=4):
{fields_code}
                        with Row(gap=3, align="center"):
                            Button("{submit_label}", css_class="flex-1", disabled=STATE.submitting)
                            with If(STATE.submitting):
                                Loader(variant="dots", size="sm")
    return PrefabApp(view=view)
'''
    return code


def _render_delete_tool(delete: DeleteEndpoint) -> str:
    """Generate a display tool with a Dialog confirmation for a DELETE endpoint.

    Produces a confirmation dialog with:
    - Warning message
    - Cancel button (CloseOverlay)
    - Confirm button (CallTool + ShowToast)
    """
    func_name = f"action_delete_{camel_to_snake(delete.operation_id)}"
    summary = delete.summary or f"Delete {delete.tag}"

    # Build function parameters from path params
    params = []
    call_args: dict[str, str] = {}
    for p in delete.path_params:
        hint = _param_type_hint(p)
        params.append(f"{p['name']}: {hint}")
        call_args[camel_to_snake(p["name"])] = "{{ " + p["name"] + " }}"

    params_str = ", ".join(params)
    call_args_repr = repr(call_args) if call_args else "{}"

    code = f'''
@mcp.tool(
    app=True if PREFAB_AVAILABLE else False,
    tags=["display", "{delete.tag}"],
    description="""{summary}""",
)
def {func_name}({params_str}) -> Any:
    """{summary}"""
    if not PREFAB_AVAILABLE:
        return {{"action": "delete", "tool": "{delete.tool_name}", "params": {{{", ".join(f'"{p["name"]}": {p["name"]}' for p in delete.path_params)}}}}}

    with Column(gap=5, css_class="p-6 max-w-md") as view:
        with Dialog(title="Confirm Deletion", description="This action cannot be undone."):
            Button("{summary}", variant="destructive")
            with Column(gap=4, css_class="py-2"):
                Muted("Are you sure you want to proceed? This will permanently delete the resource.")
                with Row(gap=2, justify="end"):
                    Button("Cancel", variant="outline", on_click=CloseOverlay())
                    Button(
                        "Delete",
                        variant="destructive",
                        on_click=[
                            CallTool("{delete.tool_name}", arguments={call_args_repr}),
                            CloseOverlay(),
                            ShowToast("Deleted successfully", variant="success"),
                        ],
                    )
    return PrefabApp(view=view)
'''
    return code


# ---------------------------------------------------------------------------
# Module assembly
# ---------------------------------------------------------------------------


def _build_extra_imports(
    *,
    has_forms: bool,
    has_deletes: bool,
    has_nested: bool,
    has_expandable: bool,
    has_tables: bool,
) -> str:
    """Build extra import block based on which features a module needs."""
    blocks: list[str] = []

    # Collect components, actions, and mcp-actions needed
    components: list[str] = []
    actions: list[str] = []
    mcp_actions: list[str] = []

    if has_forms:
        components.extend(["Button", "Form", "If", "Input", "Loader", "Select", "SelectOption"])
        actions.extend(["SetState", "ShowToast"])
        mcp_actions.append("CallTool")

    if has_deletes:
        components.extend(["Button", "Dialog"])
        actions.append("ShowToast")
        mcp_actions.append("CallTool")

    if has_nested:
        components.extend(["Tabs", "Tab"])

    if has_expandable:
        components.append("ExpandableRow")

    if has_tables:
        components.extend(["Button", "If"])
        actions.extend(["SetInterval", "SetState"])
        mcp_actions.append("CallTool")

    # Pydantic imports (forms only)
    if has_forms:
        blocks.append("from typing import Literal")
        blocks.append("from pydantic import BaseModel, Field")

    # Build the try/except import block
    import_lines: list[str] = []
    if components:
        all_components = sorted(set(components))
        import_lines.append(
            f"    from prefab_ui.components import {', '.join(all_components)}"
        )
    if actions:
        import_lines.append(
            f"    from prefab_ui.actions import {', '.join(sorted(set(actions)))}"
        )
    if mcp_actions:
        import_lines.append(
            f"    from prefab_ui.actions.mcp import {', '.join(sorted(set(mcp_actions)))}"
        )
    if has_deletes:
        import_lines.append("    from prefab_ui.actions.ui import CloseOverlay")
    if has_forms or has_tables:
        import_lines.append("    from prefab_ui.rx import STATE")

    if import_lines:
        blocks.append("try:")
        blocks.extend(import_lines)
        blocks.append("except ImportError:")
        blocks.append("    pass")

    if not blocks:
        return ""
    return "\n" + "\n".join(blocks) + "\n"


def render_display_module(
    tag: str,
    endpoints: list[DisplayEndpoint],
    api_var_name: str,
    api_class_name: str,
    form_endpoints: list[FormEndpoint] | None = None,
    delete_endpoints: list[DeleteEndpoint] | None = None,
) -> str:
    """Generate a complete display module file for a tag (e.g. pet_display.py).

    Args:
        tag: The OpenAPI tag (e.g. "pet")
        endpoints: Display endpoints belonging to this tag
        api_var_name: API variable name (e.g. "pet_api")
        api_class_name: API class name (e.g. "PetApi")
        form_endpoints: Optional POST/PUT endpoints for form generation
        delete_endpoints: Optional DELETE endpoints for delete confirmation dialogs
    """
    module_name = tag.title().replace("_", "")

    # Determine which enhanced features are needed by scanning endpoints
    has_nested = False
    has_expandable = False
    has_tables = False
    for ep in endpoints:
        schema = ep.response_schema
        if schema is None:
            continue
        nested = [f for f in schema.fields if f.is_nested_object or f.is_array]
        if nested and schema.is_object:
            has_nested = True
        if schema.is_array:
            has_tables = True
            shown_cols = {c["key"] for c in table_columns_for_fields(schema.fields)}
            extra = any(
                (f.is_nested_object or f.is_array) or
                (not f.is_array and not f.is_nested_object and f.name not in shown_cols)
                for f in schema.fields
            )
            if extra:
                has_expandable = True

    tool_code_blocks = []
    for ep in endpoints:
        schema = ep.response_schema
        if schema is None:
            continue
        if schema.is_array:
            tool_code_blocks.append(_render_table_tool(ep, api_var_name))
        elif schema.is_object:
            tool_code_blocks.append(_render_detail_tool(ep, api_var_name))

    # Generate Pydantic models and form tools
    model_code_blocks = []
    form_tool_blocks = []
    has_forms = False
    if form_endpoints:
        for fe in form_endpoints:
            model_code = _render_pydantic_model(fe)
            if model_code:
                model_code_blocks.append(model_code)
                form_tool_blocks.append(_render_form_tool(fe))
                has_forms = True

    # Generate delete confirmation tools
    delete_tool_blocks = []
    has_deletes = False
    if delete_endpoints:
        for de in delete_endpoints:
            delete_tool_blocks.append(_render_delete_tool(de))
            has_deletes = True

    if not tool_code_blocks and not form_tool_blocks and not delete_tool_blocks:
        return ""

    tools_code = "\n".join(tool_code_blocks)
    models_code = "\n".join(model_code_blocks)
    forms_code = "\n".join(form_tool_blocks)
    deletes_code = "\n".join(delete_tool_blocks)
    variants_repr = repr(STATUS_VARIANTS)

    # Build extra imports based on which features are used
    extra_imports = _build_extra_imports(
        has_forms=has_forms,
        has_deletes=has_deletes,
        has_nested=has_nested,
        has_expandable=has_expandable,
        has_tables=has_tables,
    )

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

from openapi_py_fetch import ApiClient, ApiException, Configuration
from openapi_client import {api_class_name}

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
{extra_imports}
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
    base_url = os.environ.get("API_BASE_URL", "")
    if base_url:
        config.host = base_url
    token = os.environ.get("API_TOKEN", "")
    if token:
        config.access_token = token
    client = ApiClient(config)
    return {api_class_name}(client)

{api_var_name} = _get_api()

# ============================================================================
# Generated display tools
# ============================================================================
"""

    # Assemble: header + helper + init + models + display tools + form tools + delete tools
    parts = [header, helper, init_code]
    if models_code:
        parts.append(
            "\n# ============================================================================\n# Pydantic models for form generation\n# ============================================================================\n"
        )
        parts.append(models_code)
    parts.append(tools_code)
    if forms_code:
        parts.append(
            "\n# ============================================================================\n# Form tools (auto-generated from request body schemas)\n# ============================================================================\n"
        )
        parts.append(forms_code)
    if deletes_code:
        parts.append(
            "\n# ============================================================================\n# Delete confirmation tools\n# ============================================================================\n"
        )
        parts.append(deletes_code)
    return "\n".join(parts) + "\n"

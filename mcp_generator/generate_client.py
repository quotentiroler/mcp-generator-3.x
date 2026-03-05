"""
Pure Python OpenAPI client generator.

Generates Python API stub classes directly from an OpenAPI spec, producing
output compatible with what openapi-generator-cli would create.  This removes
the dependency on Java / Node.js entirely.

The generated classes have proper:
- inspect.signature() -> typed parameters
- get_type_hints() -> type annotations
- inspect.getdoc() -> docstrings from spec descriptions
"""

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


def snake_case(name: str) -> str:
    """Convert a string to snake_case."""
    name = name.replace("-", "_")
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def pascal_case(name: str) -> str:
    """Convert a string to PascalCase."""
    parts = re.split(r"[-_\s]+", name)
    return "".join(p.capitalize() for p in parts if p)


def sanitize_method_name(operation_id: str) -> str:
    """Convert operationId to a valid Python method name."""
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "", operation_id)
    result = snake_case(clean)
    if result and result[0].isdigit():
        result = "op_" + result
    return result


# ---------------------------------------------------------------------------
# Schema -> Python type mapping
# ---------------------------------------------------------------------------


def map_schema_to_python_type(schema: dict | None) -> str:
    """Map an OpenAPI schema to a Python type annotation string."""
    if schema is None:
        return "str"

    schema_type = schema.get("type")
    nullable = schema.get("nullable", False)

    if schema_type == "string":
        base = "str"
    elif schema_type == "integer":
        base = "int"
    elif schema_type == "number":
        base = "float"
    elif schema_type == "boolean":
        base = "bool"
    elif schema_type == "array":
        item_type = map_schema_to_python_type(schema.get("items", {}))
        base = f"list[{item_type}]"
    elif schema_type == "object":
        base = "dict[str, Any]"
    else:
        base = "str"

    if nullable:
        return f"{base} | None"
    return base


# ---------------------------------------------------------------------------
# Operation extraction
# ---------------------------------------------------------------------------


def extract_operations(spec: dict) -> dict[str, list[dict]]:
    """Extract all operations grouped by tag."""
    operations_by_tag: dict[str, list[dict]] = {}

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            tags = operation.get("tags", ["default"])
            operation_id = operation.get("operationId", f"{method}_{path}")

            # Extract parameters
            params = []
            for param in operation.get("parameters", []):
                params.append({
                    "name": param.get("name", ""),
                    "in": param.get("in", "query"),
                    "required": param.get("required", False),
                    "schema": param.get("schema", {}),
                    "description": param.get("description", ""),
                })

            # Extract request body
            request_body = operation.get("requestBody", {})
            body_schema = None
            if request_body:
                content = request_body.get("content", {})
                for ct in [
                    "application/json",
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                ]:
                    if ct in content:
                        body_schema = content[ct].get("schema", {})
                        break

            responses = operation.get("responses", {})
            success_response = responses.get("200", responses.get("201", {}))

            op_info = {
                "operation_id": operation_id,
                "method": method.upper(),
                "path": path,
                "summary": operation.get("summary", ""),
                "description": operation.get("description", ""),
                "parameters": params,
                "body_schema": body_schema,
                "body_required": request_body.get("required", False),
                "response": success_response,
            }

            for tag in tags:
                operations_by_tag.setdefault(tag, []).append(op_info)

    return operations_by_tag


# ---------------------------------------------------------------------------
# Code generation - methods & classes
# ---------------------------------------------------------------------------


def generate_method(op: dict) -> str:
    """Generate a Python method for an API operation."""
    method_name = sanitize_method_name(op["operation_id"])

    params: list[str] = ["self"]
    param_docs: list[str] = []

    required_params: list[tuple[str, str, str]] = []
    optional_params: list[tuple[str, str, str]] = []

    for param in op["parameters"]:
        pname = snake_case(param["name"])
        ptype = map_schema_to_python_type(param.get("schema"))
        desc = param.get("description", f"{param['name']} parameter")
        if param.get("required", False):
            required_params.append((pname, ptype, desc))
        else:
            optional_params.append((pname, ptype, desc))

    if op.get("body_schema"):
        body_type = map_schema_to_python_type(op["body_schema"])
        if op.get("body_required", False):
            required_params.append(("body", body_type, "Request body"))
        else:
            optional_params.append(("body", body_type, "Request body"))

    for pname, ptype, desc in required_params:
        params.append(f"{pname}: {ptype}")
        param_docs.append(f":param {pname}: {desc}")

    for pname, ptype, desc in optional_params:
        params.append(f"{pname}: {ptype} | None = None")
        param_docs.append(f":param {pname}: {desc} (optional)")

    params.append("**kwargs")

    summary = op.get("summary") or op.get("description") or f"{op['method']} {op['path']}"
    summary = summary.strip().split("\n")[0][:200]

    docstring_lines = [summary, "", f"{op['method']} {op['path']}", ""]
    docstring_lines.extend(param_docs)
    docstring_lines.append(":return: API response")
    docstring = "\n        ".join(docstring_lines)

    param_str = ", ".join(params)

    return f'''    def {method_name}({param_str}) -> object:
        """{docstring}
        """
        pass

    def {method_name}_with_http_info({param_str}) -> object:
        """{docstring}

        Returns tuple of (data, status_code, headers).
        """
        pass
'''


def generate_api_class(
    tag: str,
    operations: list[dict],
    api_title: str,
    api_description: str,
) -> tuple[str, str, str]:
    """Generate a complete API class file for a tag.

    Returns (class_name, module_name, file_content).
    """
    class_name = pascal_case(tag) + "Api"
    module_name = snake_case(tag) + "_api"

    methods_code = ""
    for op in operations:
        methods_code += generate_method(op) + "\n"

    content = f'''# coding: utf-8

"""
    {api_title}

    {api_description}
    Generated by mcp-generator pure-python client generator.
"""

from typing import Any, Optional
from openapi_client.api_client import ApiClient


class {class_name}:
    """API class for {tag} operations.

    This class provides methods to interact with the {tag} endpoints
    of the {api_title} API.
    """

    def __init__(self, api_client: ApiClient | None = None) -> None:
        if api_client is None:
            api_client = ApiClient()
        self.api_client = api_client

{methods_code}'''

    return class_name, module_name, content


# ---------------------------------------------------------------------------
# Supporting module generators
# ---------------------------------------------------------------------------


def generate_api_client() -> str:
    """Generate the ApiClient class."""
    return '''# coding: utf-8

"""API client module."""

from typing import Any, Optional


class ApiClient:
    """Generic API client for OpenAPI client library builds.

    This client handles the configuration and HTTP communication.
    """

    def __init__(self, configuration=None, header_name=None, header_value=None, cookie=None) -> None:
        from openapi_client.configuration import Configuration
        if configuration is None:
            configuration = Configuration.get_default()
        self.configuration = configuration
        self.default_headers = {}
        if header_name:
            self.default_headers[header_name] = header_value
        self.cookie = cookie

    def call_api(self, resource_path, method, **kwargs):
        """Make the HTTP request."""
        pass

    def select_header_accept(self, accepts):
        """Return Accept header based on an array of accepts provided."""
        if not accepts:
            return None
        for accept in accepts:
            if "application/json" in accept:
                return accept
        return accepts[0]

    def select_header_content_type(self, content_types):
        """Return Content-Type header based on an array of content types."""
        if not content_types:
            return "application/json"
        for ct in content_types:
            if "application/json" in ct:
                return ct
        return content_types[0]
'''


def generate_api_response() -> str:
    """Generate the ApiResponse class."""
    return '''# coding: utf-8

"""API response module."""

from typing import Any


class ApiResponse:
    """API response wrapper.

    Attributes:
        status_code: HTTP status code
        headers: HTTP response headers
        data: Deserialized response data
        raw_data: Raw response body bytes
    """

    def __init__(self, status_code: int = 0, headers: dict | None = None,
                 data: Any = None, raw_data: bytes | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.data = data
        self.raw_data = raw_data
'''


def generate_configuration() -> str:
    """Generate the Configuration class."""
    return '''# coding: utf-8

"""Configuration module."""

from typing import Any


class Configuration:
    """OpenAPI client configuration.

    Manages settings for API client connections.
    """

    _default = None

    def __init__(
        self,
        host: str = "http://localhost",
        api_key: dict | None = None,
        api_key_prefix: dict | None = None,
        access_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        ssl_ca_cert: str | None = None,
        server_index: int | None = None,
        server_variables: dict | None = None,
    ) -> None:
        self.host = host
        self.api_key = api_key or {}
        self.api_key_prefix = api_key_prefix or {}
        self.access_token = access_token
        self.username = username
        self.password = password
        self.ssl_ca_cert = ssl_ca_cert
        self.server_index = server_index
        self.server_variables = server_variables or {}
        self.verify_ssl = True
        self.temp_folder_path = None

    @classmethod
    def get_default(cls) -> "Configuration":
        """Return the default configuration."""
        if cls._default is None:
            cls._default = Configuration()
        return cls._default

    @classmethod
    def set_default(cls, default: "Configuration") -> None:
        """Set the default configuration."""
        cls._default = default
'''


def generate_exceptions() -> str:
    """Generate exception classes."""
    return '''# coding: utf-8

"""Exception classes for OpenAPI client."""

from typing import Any


class OpenApiException(Exception):
    """Base exception for OpenAPI client."""


class ApiTypeError(OpenApiException, TypeError):
    """API type error."""

    def __init__(self, msg: str, path_to_item: list | None = None,
                 valid_classes: tuple | None = None, key_type: bool | None = None) -> None:
        self.path_to_item = path_to_item
        self.valid_classes = valid_classes
        self.key_type = key_type
        super().__init__(msg)


class ApiValueError(OpenApiException, ValueError):
    """API value error."""

    def __init__(self, msg: str, path_to_item: list | None = None) -> None:
        self.path_to_item = path_to_item
        super().__init__(msg)


class ApiKeyError(OpenApiException, KeyError):
    """API key error."""

    def __init__(self, msg: str, path_to_item: list | None = None) -> None:
        self.path_to_item = path_to_item
        super().__init__(msg)


class ApiAttributeError(OpenApiException, AttributeError):
    """API attribute error."""

    def __init__(self, msg: str, path_to_item: list | None = None) -> None:
        self.path_to_item = path_to_item
        super().__init__(msg)


class ApiException(OpenApiException):
    """API exception with HTTP status information.

    Attributes:
        status: HTTP status code
        reason: Error reason text
        body: Response body
        headers: Response headers
    """

    def __init__(self, status: int = 0, reason: str = "", body: str | None = None,
                 headers: dict | None = None) -> None:
        self.status = status
        self.reason = reason
        self.body = body
        self.headers = headers or {}
        super().__init__(f"({status}) Reason: {reason}")
'''


# ---------------------------------------------------------------------------
# Package generation (public API)
# ---------------------------------------------------------------------------


def generate_client_package(
    spec: dict[str, Any],
    output_dir: Path,
) -> bool:
    """Generate the complete openapi_client package from an OpenAPI spec.

    This is the main entry point used by `cli.main`.

    Args:
        spec: Parsed OpenAPI specification dictionary.
        output_dir: Root of the generated_openapi directory
                    (the `openapi_client` package will be created inside it).

    Returns:
        `True` if generation + verification succeeded.
    """
    from .introspection import enrich_spec_tags

    client_dir = output_dir / "openapi_client"
    api_dir = client_dir / "api"
    models_dir = client_dir / "models"

    # Clean and create directories
    if client_dir.exists():
        shutil.rmtree(client_dir)

    client_dir.mkdir(parents=True)
    api_dir.mkdir(parents=True)
    models_dir.mkdir(parents=True)

    info = spec.get("info", {})
    api_title = info.get("title", "Generated API")
    api_description = info.get("description", "")
    api_version = info.get("version", "1.0.0")

    # Auto-discover tags from endpoint definitions
    discovered = enrich_spec_tags(spec)
    if discovered:
        print(
            f"   \U0001f3f7\ufe0f  Auto-discovered {len(discovered)} "
            f"undeclared tag(s): {', '.join(discovered)}"
        )

    # Extract operations grouped by tag
    operations_by_tag = extract_operations(spec)

    print(f"   Found {len(operations_by_tag)} API tag(s):")
    for tag, ops in sorted(operations_by_tag.items()):
        print(f"     {tag}: {len(ops)} operations")

    # Generate API classes
    api_classes: list[tuple[str, str]] = []
    for tag, operations in sorted(operations_by_tag.items()):
        class_name, module_name, content = generate_api_class(
            tag, operations, api_title, api_description
        )
        api_classes.append((class_name, module_name))

        filepath = api_dir / f"{module_name}.py"
        filepath.write_text(content, encoding="utf-8")

    # API __init__.py
    api_init_lines = ["# flake8: noqa\n", "# import apis into api package\n"]
    for class_name, module_name in sorted(api_classes):
        api_init_lines.append(
            f"from openapi_client.api.{module_name} import {class_name}\n"
        )
    (api_dir / "__init__.py").write_text("".join(api_init_lines), encoding="utf-8")

    # Models __init__.py (stub - we generate stubs, not full models)
    (models_dir / "__init__.py").write_text(
        "# flake8: noqa\n\n# No model classes generated (schemas are inline)\n",
        encoding="utf-8",
    )

    # Supporting modules
    (client_dir / "api_client.py").write_text(generate_api_client(), encoding="utf-8")
    (client_dir / "api_response.py").write_text(
        generate_api_response(), encoding="utf-8"
    )
    (client_dir / "configuration.py").write_text(
        generate_configuration(), encoding="utf-8"
    )
    (client_dir / "exceptions.py").write_text(generate_exceptions(), encoding="utf-8")

    # Main __init__.py
    init_lines = [
        f'"""\n{api_title}\n\n{api_description}\n"""\n\n',
        f'__version__ = "{api_version}"\n\n',
        "# import ApiClient\n",
        "from openapi_client.api_client import ApiClient\n",
        "from openapi_client.api_response import ApiResponse\n",
        "from openapi_client.configuration import Configuration\n",
        "from openapi_client.exceptions import (\n",
        "    OpenApiException,\n",
        "    ApiTypeError,\n",
        "    ApiValueError,\n",
        "    ApiKeyError,\n",
        "    ApiAttributeError,\n",
        "    ApiException,\n",
        ")\n\n",
        "# import apis into sdk package\n",
    ]
    for class_name, module_name in sorted(api_classes):
        init_lines.append(
            f"from openapi_client.api.{module_name} import {class_name}\n"
        )
    (client_dir / "__init__.py").write_text("".join(init_lines), encoding="utf-8")

    # pyproject.toml (so it's installable)
    pyproject = f'''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "openapi-client"
version = "{api_version}"
description = "{api_title}"
requires-python = ">=3.11"
'''
    (output_dir / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    total_methods = sum(len(ops) for ops in operations_by_tag.values())
    print(
        f"   \u2705 Generated {len(api_classes)} API classes "
        f"({total_methods} methods)"
    )

    return _verify_package(output_dir)


def _verify_package(output_dir: Path) -> bool:
    """Verify the generated package can be imported and introspected."""
    import inspect

    if str(output_dir) not in sys.path:
        sys.path.insert(0, str(output_dir))

    # Force reimport in case of prior stale imports
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("openapi_client"):
            del sys.modules[mod_name]

    try:
        import openapi_client  # noqa: F811

        api_classes = [
            (name, getattr(openapi_client, name))
            for name in dir(openapi_client)
            if name.endswith("Api")
            and not name.startswith("_")
            and isinstance(getattr(openapi_client, name), type)
        ]

        if not api_classes:
            print("   \u26a0\ufe0f  Verification: no Api classes found")
            return False

        # Quick introspection check on the first class
        _cls_name, cls = api_classes[0]
        methods = [
            m
            for m in dir(cls)
            if not m.startswith("_")
            and not m.endswith("_with_http_info")
            and callable(getattr(cls, m))
        ]
        if methods:
            sig = inspect.signature(getattr(cls, methods[0]))
            doc = inspect.getdoc(getattr(cls, methods[0]))
            if sig and doc:
                print(
                    "   \u2705 Introspection verified (signatures + docstrings OK)"
                )

        return True

    except Exception as e:
        print(f"   \u26a0\ufe0f  Verification failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Standalone CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point for standalone usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pure Python OpenAPI client generator"
    )
    parser.add_argument(
        "spec", nargs="?", default="openapi.json", help="Path to OpenAPI spec"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("generated_openapi")
    )
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"\u274c Spec not found: {spec_path}")
        return 1

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    info = spec.get("info", {})
    print(f"Spec: {info.get('title', '?')}")
    print(f"Paths: {len(spec.get('paths', {}))}")

    ok = generate_client_package(spec, args.output_dir)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
CLI entry point for MCP generator.

Handles command-line interface, logging setup, and orchestrates the generation process.
"""

import os
import sys
from pathlib import Path

from .generator import generate_all, generate_main_composition_server
from .templates.authentication import generate_authentication_middleware
from .templates.cache_middleware import generate_cache_middleware
from .templates.event_store import generate_event_store
from .templates.oauth_provider import generate_oauth_provider
from .templates.storage_backend import generate_storage_backend
from .test_generator import (
    generate_auth_flow_tests,
    generate_behavioral_tests,
    generate_cache_tests,
    generate_http_basic_tests,
    generate_multi_auth_tests,
    generate_oauth_persistence_tests,
    generate_openapi_feature_tests,
    generate_performance_tests,
    generate_resource_tests,
    generate_server_integration_tests,
    generate_test_runner,
    generate_tool_schema_tests,
    generate_tool_tests,
    generate_transform_tests,
)
from .writers import (
    write_main_server,
    write_middleware_files,
    write_package_files,
    write_server_modules,
    write_test_files,
    write_test_runner,
)


def setup_utf8_console():
    """Configure UTF-8 encoding for console output (fixes emoji display on Windows)."""
    if sys.platform == "win32":
        # Set console to UTF-8 mode on Windows
        os.system("chcp 65001 > nul 2>&1")
        # Reconfigure stdout encoding if available (Python 3.7+)
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass  # Not available or failed, continue anyway


def print_metadata_summary(api_metadata, security_config):
    """Print API metadata and security configuration summary."""
    print("\n📋 API Metadata:")
    print(f"   Title: {api_metadata.title}")
    print(f"   Version: {api_metadata.version}")
    if api_metadata.description:
        print(f"   Description: {api_metadata.description[:80]}...")
    if api_metadata.contact and api_metadata.contact.get("email"):
        print(f"   Contact: {api_metadata.contact['email']}")
    if api_metadata.license and api_metadata.license.get("name"):
        print(f"   License: {api_metadata.license['name']}")
    if api_metadata.servers:
        print(f"   Servers: {len(api_metadata.servers)} configured")
    if api_metadata.tags:
        print(f"   Tags: {len(api_metadata.tags)} categories")

    backend_url = api_metadata.backend_url
    print(f"   Backend URL: {backend_url}")

    print("\n🔐 Security Configuration:")
    if security_config.schemes:
        print(f"   Authentication: {', '.join(security_config.schemes.keys())}")
    if security_config.default_scopes:
        print(f"   Default scopes: {', '.join(security_config.default_scopes)}")
    if security_config.oauth_config:
        oauth = security_config.oauth_config
        print(f"   OAuth2 flows: {', '.join(oauth.flows.keys())}")
        print(f"   Available scopes: {len(oauth.all_scopes)}")


def main():
    """Main CLI entry point."""
    import argparse

    setup_utf8_console()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MCP Generator 3.1 - OpenAPI to FastMCP 3.x Server Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation (minimal server)
  generate-mcp

  # With custom OpenAPI file
  generate-mcp --file ./my-api-spec.yaml

  # Download from URL
  generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json

  # With optional features
  generate-mcp --enable-storage --enable-caching
  generate-mcp --enable-resources

Optional Features (disabled by default for simplicity):
  --enable-storage    Persistent storage for OAuth tokens & state
  --enable-caching    Response caching (reduces API calls)
  --enable-resources  MCP resources from GET endpoints

Documentation: https://github.com/quotentiroler/mcp-generator-2.0
        """,
    )

    parser.add_argument(
        "--file",
        type=str,
        default="./openapi.json",
        help="Path to OpenAPI specification file (default: ./openapi.json)",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL to download OpenAPI specification from (overrides --file)",
    )

    parser.add_argument(
        "--enable-storage",
        action="store_true",
        default=False,
        help="Enable persistent storage backend (for OAuth tokens, session state, user data)",
    )

    parser.add_argument(
        "--enable-caching",
        action="store_true",
        default=False,
        help="Enable response caching middleware (reduces backend API calls, requires --enable-storage)",
    )

    parser.add_argument(
        "--enable-resources",
        action="store_true",
        default=False,
        help="Generate MCP resource templates from GET endpoints (exposes API data as resources)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("MCP Generator 3.1 - OpenAPI to FastMCP 3.x Server Generator")
    print("=" * 80)

    # Use current working directory for all operations
    src_dir = Path.cwd()

    # Handle URL download if specified
    if args.url:
        print("\n📥 Downloading OpenAPI specification from URL...")
        print(f"   {args.url}")

        try:
            import httpx

            response = httpx.get(args.url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            # Preserve file extension based on URL
            if args.url.endswith(".yaml") or args.url.endswith(".yml"):
                openapi_spec = src_dir / "openapi.yaml"
            else:
                openapi_spec = src_dir / "openapi.json"

            openapi_spec.write_bytes(response.content)
            print(f"   ✅ Downloaded to: {openapi_spec.name}")

        except Exception as e:
            print("\n❌ Failed to download OpenAPI specification")
            print(f"\n   Error: {e}")
            print("\n💡 To fix this:")
            print("   • Check the URL is accessible")
            print("   • Try downloading manually and use --file instead")
            print()
            sys.exit(1)
    else:
        # Use file path (absolute or relative to current directory)
        file_path = Path(args.file)
        if file_path.is_absolute():
            openapi_spec = file_path
        else:
            openapi_spec = src_dir / args.file

    # Check for OpenAPI spec
    if not openapi_spec.exists():
        print("\n❌ OpenAPI Specification Not Found")
        print("\nThe generator requires an OpenAPI specification file to proceed.")
        print("\n📋 Expected location:")
        print(f"   {openapi_spec}")
        print("\n💡 To get started:")
        print("   1. Place your openapi.json file in the project root")
        print("   2. Or specify a custom file:")
        print("      generate-mcp --file ./path/to/spec.yaml")
        print("   3. Or download from URL:")
        print("      generate-mcp --url https://petstore3.swagger.io/api/v3/openapi.json")
        print("\n📚 Documentation: https://github.com/quotentiroler/mcp-generator-2.0")
        print()
        sys.exit(1)

    print(f"\n✅ Found OpenAPI specification: {openapi_spec.name}")

    # Ensure API client exists before trying to introspect it
    generated_dir = src_dir / "generated_openapi"
    openapi_client_dir = generated_dir / "openapi_client"

    if not (openapi_client_dir.exists() and (openapi_client_dir / "__init__.py").exists()):
        print("\n🔨 Generating Python API client from OpenAPI specification...")
        print("   This is a one-time step that may take a few moments.")

        try:
            import json as _json

            with open(openapi_spec, encoding="utf-8") as _f:
                spec = _json.load(_f)

            from .generate_client import generate_client_package

            generated_dir.mkdir(parents=True, exist_ok=True)
            ok = generate_client_package(spec, generated_dir)
            if not ok:
                print("\n❌ API Client Generation Failed")
                print("\n💡 Verify your openapi.json is valid:")
                print("      python -m mcp_generator.scripts.validate_openapi")
                sys.exit(1)

            print("   ✅ API client generated successfully")
        except Exception as e:
            print(f"\n❌ Error generating API client: {e}")
            print("\n💡 Verify your openapi.json is valid:")
            print("      python -m mcp_generator.scripts.validate_openapi")
            sys.exit(1)

    try:
        # Generate all components
        print("\n🏗️  Analyzing API structure...")
        api_metadata, security_config, modules, total_tools = generate_all(
            src_dir, enable_resources=args.enable_resources
        )

        # Calculate resource count early for conditional logic
        total_resources = sum(spec.resource_count for spec in modules.values())

        # Print summary
        print_metadata_summary(api_metadata, security_config)

        # Determine output paths (use current working directory)
        output_dir = src_dir / "generated_mcp"
        servers_dir = output_dir / "servers"
        middleware_dir = output_dir / "middleware"

        # Write server modules
        print(f"\n📦 Generating {len(modules)} server modules...")
        write_server_modules(modules, servers_dir)

        # Generate and write middleware (ALWAYS needed even without auth for openapi_client setup)
        print("\n🔐 Generating API client middleware...")
        middleware_code = generate_authentication_middleware(api_metadata, security_config)
        oauth_code = generate_oauth_provider(api_metadata, security_config)
        event_store_code = generate_event_store()
        write_middleware_files(middleware_code, oauth_code, event_store_code, middleware_dir)

        if not security_config.has_authentication():
            print("   💡 Note: Middleware provides unauthenticated API client for backend calls")

        # Generate storage backend if requested
        if args.enable_storage:
            print("\n💾 Generating pluggable storage backend...")
            storage_code = generate_storage_backend()
            storage_file = output_dir / "storage.py"
            storage_file.write_text(storage_code, encoding="utf-8")
            print("   ✅ storage.py")
            if security_config.has_authentication():
                print("   💡 OAuth tokens will persist across server restarts")
            print("   💡 Use for caching, session state, or custom data")

        # Generate cache middleware if requested
        if args.enable_caching:
            if not args.enable_storage:
                print("\n⚠️  Warning: --enable-caching requires --enable-storage")
                print("   Skipping cache generation. Please re-run with both flags.")
            else:
                print("\n⚡ Generating response caching middleware...")
                cache_code = generate_cache_middleware()
                cache_file = output_dir / "cache.py"
                cache_file.write_text(cache_code, encoding="utf-8")
                print("   ✅ cache.py")
                print("   💡 Decorate expensive tools with @cache.cached(ttl=600)")

        # Generate and write main composition server
        print("\n🔗 Generating main composition server...")

        # Load composition configuration from fastmcp.json if it exists
        composition_strategy = "mount"  # default (FastMCP 3.x uses mount with namespace)
        fastmcp_json_path = output_dir / "fastmcp.json"
        if fastmcp_json_path.exists():
            try:
                import json

                with open(fastmcp_json_path, encoding="utf-8") as f:
                    config = json.load(f)
                    composition_config = config.get("composition", {})
                    composition_strategy = composition_config.get("strategy", "mount")
            except Exception as e:
                print(f"⚠️  Could not load composition config from fastmcp.json: {e}")

        main_server_code = generate_main_composition_server(
            modules,
            api_metadata,
            security_config,
            composition_strategy=composition_strategy,
        )
        from .utils import sanitize_server_name

        server_name = sanitize_server_name(api_metadata.title)
        main_output_file = output_dir / f"{server_name}_mcp_generated.py"
        write_main_server(main_server_code, main_output_file)

        # Generate package files (README, pyproject.toml, __init__.py)
        print("\n📦 Generating package metadata files...")
        write_package_files(
            output_dir, api_metadata, security_config, modules, total_tools, args.enable_storage
        )

        # Generate test files (conditionally include auth tests)
        print("\n🧪 Generating test suites...")
        test_dir = src_dir / "test" / "generated"

        # Generate all test suites
        print("   • OpenAPI feature tests")
        openapi_feature_test_code = generate_openapi_feature_tests(
            api_metadata, security_config, modules
        )
        print("   • HTTP basic E2E tests")
        http_basic_test_code = generate_http_basic_tests(api_metadata, security_config, modules)
        print("   • Performance tests")
        performance_test_code = generate_performance_tests(api_metadata, security_config, modules)

        # Generate cache tests if caching is enabled
        cache_test_code = None
        if args.enable_caching:
            print("   • Cache middleware tests")
            cache_test_code = generate_cache_tests()

        # Generate OAuth persistence tests if storage is enabled with authentication
        oauth_persistence_test_code = None
        if args.enable_storage and security_config.has_authentication():
            print("   • OAuth token persistence tests")
            oauth_persistence_test_code = generate_oauth_persistence_tests()

        # Generate resource tests if resources are enabled
        resource_test_code = None
        if args.enable_resources and total_resources > 0:
            print("   • Resource template tests")
            resource_test_code = generate_resource_tests(modules, api_metadata, security_config)

        # Always generate transform tests (FastMCP 3.1 features)
        print("   • FastMCP 3.1 transform tests")
        transform_test_code = generate_transform_tests(api_metadata, security_config, modules)

        # Generate multi-auth tests if auth is configured
        multi_auth_test_code = None
        if security_config.has_authentication():
            print("   • FastMCP 3.1 multi-auth tests")
            multi_auth_test_code = generate_multi_auth_tests(api_metadata, security_config, modules)

        # Always generate in-process integration tests and schema validation
        print("   • Server integration tests (in-process)")
        server_integration_test_code = generate_server_integration_tests(
            modules, api_metadata, security_config
        )
        print("   • Tool schema validation tests")
        tool_schema_test_code = generate_tool_schema_tests(modules, api_metadata, security_config)
        print("   • Behavioral edge-case tests (failure-driven)")
        behavioral_test_code = generate_behavioral_tests(modules, api_metadata, security_config)

        if security_config.has_authentication():
            print("   • Authentication flow tests")
            auth_test_code = generate_auth_flow_tests(api_metadata, security_config, modules)
            print("   • Tool validation tests")
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(
                auth_test_code,
                tool_test_code,
                openapi_feature_test_code,
                http_basic_test_code,
                performance_test_code,
                cache_test_code,
                oauth_persistence_test_code,
                test_dir,
                resource_test_code,
                transform_test_code,
                multi_auth_test_code,
                server_integration_test_code,
                tool_schema_test_code,
                behavioral_test_code,
            )
        else:
            print("   • Basic tool tests (no auth required)")
            tool_test_code = generate_tool_tests(modules, api_metadata, security_config)
            write_test_files(
                None,
                tool_test_code,
                openapi_feature_test_code,
                http_basic_test_code,
                performance_test_code,
                cache_test_code,
                oauth_persistence_test_code,
                test_dir,
                resource_test_code,
                transform_test_code,
                multi_auth_test_code,
                server_integration_test_code,
                tool_schema_test_code,
                behavioral_test_code,
            )

        # Generate test runner script
        print("\n🏃 Generating test runner...")
        test_runner_code = generate_test_runner(api_metadata, server_name)
        write_test_runner(test_runner_code, src_dir / "test" / "run_tests.py")

        # Print success summary
        total_resources = sum(spec.resource_count for spec in modules.values())

        print("\n" + "=" * 80)
        print("✅ Generation Complete!")
        print("=" * 80)
        print("\n📊 Summary:")
        print(f"   • Generated {total_tools} MCP tools across {len(modules)} modules")
        if args.enable_resources and total_resources > 0:
            print(f"   • Generated {total_resources} MCP resource templates (RFC 6570 URIs)")
        if security_config.has_authentication():
            print("   • Created authentication middleware with JWT validation")
            print("   • Generated OAuth2 provider for backend integration")
            print("   • Created comprehensive test suites with automated test runner")
        else:
            print("   • No authentication required (public API)")
            print("   • Created basic test suite with automated test runner")

        # Show enabled optional features
        if args.enable_storage:
            print("   • Enabled: Persistent storage backend (storage.py, cache_middleware.py)")
        if args.enable_caching:
            print("   • Enabled: Response caching with configurable TTL")
        if args.enable_resources and total_resources > 0:
            print("   • Enabled: MCP resources for data access")

        print("\n📂 Output Location:")
        print(f"   {output_dir.relative_to(src_dir)}/")

        print("\n🧪 Run Tests:")
        print("   python test/run_tests.py")
        print("   (automatically starts server, runs tests, and cleans up)")

        print("\n🚀 Next Steps:")
        print("   1. Review generated server:")
        print(f"      cat {main_output_file.relative_to(src_dir)}")
        if security_config.has_authentication():
            print("   2. Configure authentication (see generated README.md)")
            print("   3. Run your MCP server:")
        else:
            print("   2. Run your MCP server:")
        print(f"      python {main_output_file.relative_to(src_dir)}")

        print("\n� Usage Modes:")
        print("   • STDIO: For Claude Desktop, Cline, etc.")
        print("     export BACKEND_API_TOKEN=your_token")
        print(f"     python {server_name}_mcp_generated.py")
        print("\n   • HTTP: For web-based MCP clients")
        print(f"     python {server_name}_mcp_generated.py --transport=http --port=8000")
        print("\n   • HTTP with JWT validation:")
        print(
            f"     python {server_name}_mcp_generated.py --transport=http --port=8000 --validate-tokens"
        )

        print("\n📚 Documentation:")
        print(f"   • README: {output_dir.relative_to(src_dir)}/README.md")
        print("   • Tests: test/generated/")
        print("   • Test Runner: test/run_tests.py")
        print("   • GitHub: https://github.com/quotentiroler/mcp-generator-2.0")

        # Show optional features that were not enabled
        disabled_features = []
        if not args.enable_storage:
            disabled_features.append(
                ("--enable-storage", "Persistent OAuth tokens & state across restarts")
            )
        if not args.enable_caching:
            disabled_features.append(
                ("--enable-caching", "Cache API responses (reduces rate limit impact)")
            )
        if not args.enable_resources:
            disabled_features.append(("--enable-resources", "Expose API data as MCP resources"))

        if disabled_features:
            print("\n💡 Optional Features (not enabled):")
            for flag, description in disabled_features:
                print(f"   {flag:20s} → {description}")

            # Build regeneration command
            flags_str = " ".join([flag for flag, _ in disabled_features])
            if args.url:
                print(f"\n   To enable: generate-mcp --url {args.url} {flags_str}")
            elif args.file != "./openapi.json":
                print(f"\n   To enable: generate-mcp --file {args.file} {flags_str}")
            else:
                print(f"\n   To enable: generate-mcp {flags_str}")

        print()

    except ModuleNotFoundError as e:
        print("\n❌ Module Import Error")
        print(f"\nCould not import required module: {e}")
        print("\n💡 This usually means:")
        print("   1. The API client generation was incomplete")
        print("   2. A required dependency is missing")
        print("\n🔧 To resolve:")
        print("   • Regenerate the API client:")
        print("     python -m mcp_generator.scripts.generate_openapi_client")
        print("   • Check dependencies:")
        print("     uv sync")
        print()
        sys.exit(1)

    except Exception as e:
        print("\n❌ Generation Error")
        print(f"\nAn unexpected error occurred: {str(e)}")
        print("\n📋 Stack trace:")
        import traceback

        traceback.print_exc()
        print("\n💡 For help:")
        print("   • Check the error message above")
        print("   • Validate your OpenAPI spec: python -m mcp_generator.scripts.validate_openapi")
        print("   • Report issues: https://github.com/quotentiroler/mcp-generator-2.0/issues")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

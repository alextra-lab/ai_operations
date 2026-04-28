#!/usr/bin/env python3
"""
Script for configuring and managing LLM-Guard scanners and rules.

This script helps manage the configuration of LLM-Guard scanners, allowing users to:
1. View current scanner configurations
2. Add or modify scanner configurations
3. Test configurations against sample inputs
4. Export and import configurations

Usage:
    python configure_llm_guard.py [command] [options]

Commands:
    list        List available scanners and their configurations
    add         Add a new scanner or rule
    test        Test scanner configurations against sample inputs
    export      Export current scanner configurations to a file
    import      Import scanner configurations from a file

Examples:
    python configure_llm_guard.py list
    python configure_llm_guard.py add --scanner regex --pattern "secret_key=[a-zA-Z0-9]{32}"
    python configure_llm_guard.py test --input "This contains a secret_key=abc123def456"
"""

import argparse
import json
import os
from typing import Any, cast

# Define scanner types and their configuration options
SCANNER_TYPES = {
    "prompt_injection": {
        "description": "Detects attempts to inject malicious prompts",
        "options": {
            "threshold": {
                "type": "float",
                "default": 0.75,
                "description": "Detection threshold (0.0-1.0, higher means more strict)",
            },
            "match_type": {
                "type": "str",
                "default": "FULL",
                "choices": ["FULL", "PARTIAL"],
                "description": "Whether to match the full text or parts of it",
            },
            "use_onnx": {
                "type": "bool",
                "default": False,
                "description": "Whether to use ONNX for faster inference",
            },
        },
    },
    "secrets": {
        "description": "Detects sensitive information like API keys and credentials",
        "options": {},  # No configurable options for secrets scanner
    },
    "regex": {
        "description": "Custom regex pattern matching for specific content",
        "options": {
            "patterns": {
                "type": "list",
                "default": [],
                "description": "List of regex patterns to match",
            },
            "match_type": {
                "type": "str",
                "default": "SEARCH",
                "choices": ["MATCH", "SEARCH"],
                "description": "Whether to match the entire text or search within it",
            },
        },
    },
    "gibberish": {
        "description": "Detects nonsensical or random text",
        "options": {
            "threshold": {
                "type": "float",
                "default": 0.8,
                "description": "Detection threshold (0.0-1.0, higher means more strict)",
            },
            "match_type": {
                "type": "str",
                "default": "FULL",
                "choices": ["FULL", "PARTIAL"],
                "description": "Whether to match the full text or parts of it",
            },
            "use_onnx": {
                "type": "bool",
                "default": False,
                "description": "Whether to use ONNX for faster inference",
            },
        },
    },
    "toxicity": {
        "description": "Detects toxic or harmful content",
        "options": {
            "threshold": {
                "type": "float",
                "default": 0.5,
                "description": "Detection threshold (0.0-1.0, higher means more strict)",
            },
            "use_onnx": {
                "type": "bool",
                "default": False,
                "description": "Whether to use ONNX for faster inference",
            },
        },
    },
    "language": {
        "description": "Detects and validates language of text",
        "options": {
            "allowed_languages": {
                "type": "list",
                "default": ["en"],
                "description": "List of allowed language codes (e.g., 'en', 'fr', 'es')",
            },
            "threshold": {
                "type": "float",
                "default": 0.5,
                "description": "Detection threshold (0.0-1.0, higher means more strict)",
            },
            "match_type": {
                "type": "str",
                "default": "FULL",
                "choices": ["FULL", "PARTIAL"],
                "description": "Whether to match the full text or parts of it",
            },
        },
    },
    "code": {
        "description": "Detects and validates code snippets",
        "options": {
            "denied_languages": {
                "type": "list",
                "default": [],
                "description": "List of programming languages to block (e.g., 'bash', 'js')",
            }
        },
    },
    "ban_topics": {
        "description": "Block specific topics from being discussed",
        "options": {
            "topics": {
                "type": "list",
                "default": [],
                "description": "List of topics to block (e.g., 'violence', 'drugs')",
            },
            "threshold": {
                "type": "float",
                "default": 0.5,
                "description": "Detection threshold (0.0-1.0, higher means more strict)",
            },
            "use_onnx": {
                "type": "bool",
                "default": False,
                "description": "Whether to use ONNX for faster inference",
            },
        },
    },
    "ban_substrings": {
        "description": "Block specific substrings or phrases",
        "options": {
            "substrings": {
                "type": "list",
                "default": [],
                "description": "List of substrings to block",
            },
            "case_sensitive": {
                "type": "bool",
                "default": False,
                "description": "Whether matching is case-sensitive",
            },
        },
    },
    "anonymize": {
        "description": "Anonymize sensitive information in text",
        "options": {
            "entity_types": {
                "type": "list",
                "default": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
                "description": "Entity types to anonymize",
            }
        },
    },
}

# Sample config file path
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "llm_guard_config.json"
)


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load scanner configuration from file."""
    try:
        if os.path.exists(config_path):
            with open(config_path) as f:
                return cast("dict", json.load(f))
        return {}
    except Exception as e:
        print(f"Error loading configuration: {e!s}")
        return {}


def save_config(config: dict, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """Save scanner configuration to file."""
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e!s}")
        return False


def format_scanner_info(scanner_type: str, config: dict) -> str:
    """Format scanner information for display."""
    scanner_info = SCANNER_TYPES.get(scanner_type, {})
    description = scanner_info.get("description", "Unknown scanner type")

    result = f"{scanner_type} - {description}\n"
    result += "-" * len(f"{scanner_type} - {description}") + "\n"

    if scanner_type in config:
        for option, value in config[scanner_type].items():
            result += f"  {option}: {value}\n"
    else:
        result += "  Not configured\n"

    return result


def list_scanners(config: dict) -> None:
    """List available scanners and their configurations."""
    print("Available LLM-Guard Scanners:\n")

    for scanner_type in sorted(SCANNER_TYPES.keys()):
        print(format_scanner_info(scanner_type, config))

    print("\nActive Scanners:")
    active_scanners = [scanner for scanner in config if scanner in SCANNER_TYPES]
    if active_scanners:
        for scanner in sorted(active_scanners):
            print(f"- {scanner}")
    else:
        print("No scanners are currently active in the configuration.")


def add_scanner(config: dict, scanner_type: str, options: dict) -> dict:
    """Add or update a scanner configuration."""
    if scanner_type not in SCANNER_TYPES:
        print(f"Error: Unknown scanner type '{scanner_type}'")
        print("Available scanner types:")
        for s_type in sorted(SCANNER_TYPES.keys()):
            print(f"- {s_type}: {SCANNER_TYPES[s_type]['description']}")
        return config

    scanner_options = cast("dict[str, Any]", SCANNER_TYPES[scanner_type]["options"])

    # If scanner doesn't exist in config, initialize it
    if scanner_type not in config:
        config[scanner_type] = {}

    # Process options
    for option, value in options.items():
        if option in scanner_options:
            opt_spec = scanner_options[option]
            option_type = opt_spec.get("type", "str") if isinstance(opt_spec, dict) else "str"
            try:
                value_str = str(value)
                if option_type == "float":
                    config[scanner_type][option] = float(value)
                elif option_type == "int":
                    config[scanner_type][option] = int(value)
                elif option_type == "bool":
                    if value_str.lower() in ("true", "yes", "1"):
                        config[scanner_type][option] = True
                    elif value_str.lower() in ("false", "no", "0"):
                        config[scanner_type][option] = False
                    else:
                        print(f"Error: Invalid boolean value '{value}' for option '{option}'")
                        continue
                elif option_type == "list":
                    if value_str.startswith("[") and value_str.endswith("]"):
                        try:
                            config[scanner_type][option] = json.loads(value_str)
                        except json.JSONDecodeError:
                            config[scanner_type][option] = [
                                v.strip() for v in value_str[1:-1].split(",")
                            ]
                    else:
                        config[scanner_type][option] = [v.strip() for v in value_str.split(",")]
                else:  # Default to string
                    config[scanner_type][option] = value

                print(f"Set {scanner_type}.{option} = {config[scanner_type][option]}")
            except Exception as e:
                print(f"Error setting option {option}: {e!s}")
        else:
            print(f"Warning: Unknown option '{option}' for scanner '{scanner_type}'")

    return config


def test_scanner_config(config: dict, input_text: str) -> None:
    """
    Test how the scanner configuration would process a given input.
    This is a simulation only and doesn't actually run the scanners.
    """
    print(f"Input text: {input_text}")
    print("\nScanner evaluation simulation:")
    print("-" * 30)

    for scanner_type, scanner_config in config.items():
        if scanner_type not in SCANNER_TYPES:
            continue

        description = SCANNER_TYPES[scanner_type]["description"]
        print(f"{scanner_type} ({description}):")

        # Simulate scanner behavior based on type and configuration
        if scanner_type == "regex":
            import re

            patterns = scanner_config.get("patterns", [])
            match_type = scanner_config.get("match_type", "SEARCH")

            matches = []
            for pattern in patterns:
                try:
                    if match_type == "MATCH":
                        match = re.match(pattern, input_text)
                        if match:
                            matches.append((pattern, match.group(0)))
                    else:  # SEARCH
                        for match in re.finditer(pattern, input_text):
                            matches.append((pattern, match.group(0)))
                except re.error as e:
                    print(f"  Error in pattern '{pattern}': {e!s}")

            if matches:
                print("  Matches found:")
                for pattern, match_text in matches:
                    print(f"  - Pattern '{pattern}' matched: '{match_text}'")
            else:
                print("  No matches found")

        elif scanner_type == "ban_substrings":
            substrings = scanner_config.get("substrings", [])
            case_sensitive = scanner_config.get("case_sensitive", False)

            banned_found: list[str] = []
            for substring in substrings:
                if case_sensitive:
                    if substring in input_text:
                        banned_found.append(substring)
                else:
                    if substring.lower() in input_text.lower():
                        banned_found.append(substring)

            if banned_found:
                print("  Banned substrings found:")
                for sub in banned_found:
                    print(f"  - '{sub}'")
            else:
                print("  No banned substrings found")

        # For other scanner types, just print the configuration
        else:
            print("  Configuration:")
            for option, value in scanner_config.items():
                print(f"  - {option}: {value}")
            print("  Evaluation would be performed by the actual scanner")

    print("\nNote: This is a simulation only. Actual scanner results may vary.")
    print("To test with the real LLM-Guard service, use test_llm_guard.py")


def export_config(config: dict, output_path: str) -> None:
    """Export configuration to a file."""
    try:
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Configuration exported to {output_path}")
    except Exception as e:
        print(f"Error exporting configuration: {e!s}")


def import_config(import_path: str) -> dict:
    """Import configuration from a file."""
    try:
        with open(import_path) as f:
            config = json.load(f)
        print(f"Configuration imported from {import_path}")
        return cast("dict", config)
    except Exception as e:
        print(f"Error importing configuration: {e!s}")
        return {}


def main():
    """Parse arguments and execute commands."""
    parser = argparse.ArgumentParser(
        description="Configure and manage LLM-Guard scanners and rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:", 1)[1] if __doc__ and "Usage:" in __doc__ else "",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    list_parser = subparsers.add_parser(
        "list", help="List available scanners and their configurations"
    )
    list_parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to configuration file"
    )

    # Add command
    add_parser = subparsers.add_parser("add", help="Add or modify a scanner configuration")
    add_parser.add_argument("--scanner", required=True, help="Scanner type to configure")
    add_parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to configuration file"
    )

    # Add dynamic arguments for scanner options
    option_group = add_parser.add_argument_group("scanner options")
    for _scanner_type, info in SCANNER_TYPES.items():
        for option_name, option_info in info["options"].items():
            option_help = f"{option_info['description']}"
            if "default" in option_info:
                option_help += f" (default: {option_info['default']})"
            if "choices" in option_info:
                option_help += f" (choices: {', '.join(option_info['choices'])})"

            option_group.add_argument(f"--{option_name}", help=option_help)

    # Test command
    test_parser = subparsers.add_parser(
        "test", help="Test scanner configurations against sample inputs"
    )
    test_parser.add_argument("--input", required=True, help="Input text to test")
    test_parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to configuration file"
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export configuration to a file")
    export_parser.add_argument("--output", required=True, help="Output file path")
    export_parser.add_argument(
        "--config", default=DEFAULT_CONFIG_PATH, help="Path to configuration file"
    )

    # Import command
    import_parser = subparsers.add_parser("import", help="Import configuration from a file")
    import_parser.add_argument("--input", required=True, help="Input file path")
    import_parser.add_argument(
        "--output",
        default=DEFAULT_CONFIG_PATH,
        help="Output file path (default: overwrite current config)",
    )

    args = parser.parse_args()

    if args.command == "list":
        config = load_config(args.config)
        list_scanners(config)

    elif args.command == "add":
        config = load_config(args.config)

        # Extract scanner options from args
        options = {}
        for option_name in vars(args):
            if (
                option_name not in ("command", "scanner", "config")
                and getattr(args, option_name) is not None
            ):
                options[option_name] = getattr(args, option_name)

        config = add_scanner(config, args.scanner, options)
        save_config(config, args.config)

    elif args.command == "test":
        config = load_config(args.config)
        test_scanner_config(config, args.input)

    elif args.command == "export":
        config = load_config(args.config)
        export_config(config, args.output)

    elif args.command == "import":
        config = import_config(args.input)
        if config:
            save_config(config, args.output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Configuration schema metadata.

The schema version is incremented whenever shared configuration structure,
required environment variables, or secrets handling changes in a way that
requires regenerating `.env` files from the templates.
"""

CONFIG_SCHEMA_VERSION = "2026.02.18"


def get_config_schema_version() -> str:
    """Return the current configuration schema version string."""
    return CONFIG_SCHEMA_VERSION

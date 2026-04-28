"""
Transitional module for LLM-Guard service.

This module provides backwards compatibility while the service migrates
to the standard application pattern with proper package structure. It
simply imports and exposes the FastAPI application from the new module path.
"""

# Import and re-export the FastAPI application

# This makes the app available for imports from the old location
# and allows the Docker entry point to work either directly (app:app)
# or with the new standard pattern (app.main:app)

if __name__ == "__main__":
    import uvicorn

    from shared.config.loader import load_llm_guard_config, load_logging_config

    settings = load_llm_guard_config()
    logging_config = load_logging_config(service_name=settings.name)

    # Use the new module path when running directly
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=logging_config.level.lower(),
    )

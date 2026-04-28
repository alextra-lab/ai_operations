import logging
import sys

from shared.logging_utils.base import (
    JsonFormatter,
    LoggingContextAdapter,
    TextFormatter,
    configure_logging,
    get_logger,
)


class DummyRecord(logging.LogRecord):
    def __init__(self, **kwargs):
        super().__init__("test", logging.INFO, "test.py", 10, "msg", (), None, "func")
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_json_formatter_exc_info_true():
    formatter = JsonFormatter(service_name="svc")
    record = DummyRecord(exc_info=True)
    result = formatter.format(record)
    assert "exception" in result
    assert "traceback" in result


def test_json_formatter_exc_info_tuple():
    try:
        raise ValueError("Test error")
    except Exception:
        exc_info = sys.exc_info()
    formatter = JsonFormatter(service_name="svc")
    record = DummyRecord(exc_info=exc_info)
    result = formatter.format(record)
    assert "Test error" in result
    assert "traceback" in result


def test_json_formatter_exc_info_unexpected():
    formatter = JsonFormatter(service_name="svc")

    class BadExcInfo:
        pass

    record = DummyRecord(exc_info=BadExcInfo())
    # Patch traceback.format_exception to raise
    import shared.logging_utils.base as base_mod

    orig_format_exception = base_mod.traceback.format_exception
    base_mod.traceback.format_exception = lambda *a, **k: (_ for _ in ()).throw(Exception("fail"))
    try:
        result = formatter.format(record)
        assert "Exception information available" in result
    finally:
        base_mod.traceback.format_exception = orig_format_exception


def test_json_formatter_extra_attrs():
    formatter = JsonFormatter(service_name="svc")
    record = DummyRecord(request_id="req", trace_id="trace", span_id="span", custom="val")
    result = formatter.format(record)
    assert "request_id" in result
    assert "trace_id" in result
    assert "span_id" in result
    assert "custom" in result


def test_text_formatter():
    formatter = TextFormatter()
    record = DummyRecord()
    result = formatter.format(record)
    assert "[INFO]" in result


def test_logging_context_adapter():
    logger = logging.getLogger("testctx")
    adapter = LoggingContextAdapter(logger, {"foo": "bar"})
    _msg, kwargs = adapter.process("msg", {})
    assert kwargs["extra"]["foo"] == "bar"


def test_configure_logging_json_and_text(monkeypatch):
    logger_json = configure_logging(service_name="svcjson", log_format="json")
    assert isinstance(logger_json.handlers[0].formatter, JsonFormatter)
    logger_text = configure_logging(service_name="svctext", log_format="text")
    assert isinstance(logger_text.handlers[0].formatter, TextFormatter)


def test_configure_logging_requestidfilter():
    logger = configure_logging(service_name="svcfilter", log_format="json")
    # Remove all filters and add a new one to test
    logger.filters.clear()

    class DummyFilter(logging.Filter):
        def filter(self, record):
            record.request_id = "dummy"
            record.service_name = "svcfilter"
            return True

    logger.addFilter(DummyFilter())
    logger.info("msg")
    # Should not raise


def test_get_logger_with_and_without_context():
    logger = get_logger("testget")
    assert isinstance(logger, logging.Logger)
    adapter = get_logger("testgetctx", context={"foo": "bar"})
    assert isinstance(adapter, LoggingContextAdapter)

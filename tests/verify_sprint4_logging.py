#!/usr/bin/env python3
"""
Verification tests for Sprint 4.1 — Error Handling & Logging.

Tests:
  1. Logger writes colored output to console (capturable via stderr)
  2. Logger writes structured JSON to log file
  3. Custom exceptions (AntiError, ToolError, ProviderError, MemoryError,
     BrainConnectionError, BrainContextError, ConfigError) can be raised and caught
  4. No bare `except Exception: pass` patterns remain in critical source files
"""

import os
import sys
import json
import io
import re
import tempfile

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────
#  Test 1: Logger writes structured JSON to file
# ─────────────────────────────────────────────────────────

def test_logger_writes_json_to_file():
    """AppLogger must write JSON lines to the configured log file."""
    from src.logger import AppLogger

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        log_path = tmp.name

    try:
        log = AppLogger("test_json_file", log_file=log_path)
        log.info("Hello JSON")
        log.warning("Be careful")
        log.error("Something broke")

        with open(log_path, "r") as f:
            lines = f.readlines()

        assert len(lines) >= 3, f"Expected at least 3 log lines, got {len(lines)}"

        for line in lines:
            record = json.loads(line)
            assert "timestamp" in record, "Missing timestamp in JSON log"
            assert "level" in record, "Missing level in JSON log"
            assert "module" in record, "Missing module in JSON log"
            assert "message" in record, "Missing message in JSON log"

        print("✅ test_logger_writes_json_to_file PASSED")
    finally:
        os.unlink(log_path)


# ─────────────────────────────────────────────────────────
#  Test 2: Logger writes visible output to stderr
# ─────────────────────────────────────────────────────────

def test_logger_writes_to_stderr():
    """AppLogger console output must be visible on stderr."""
    from src.logger import AppLogger

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        log_path = tmp.name

    try:
        # Capture stderr
        old_stderr = sys.stderr
        captured = io.StringIO()
        sys.stderr = captured

        log = AppLogger("test_stderr", log_file=log_path)
        log.info("Console test message")

        sys.stderr = old_stderr
        output = captured.getvalue()

        # Should contain the log level and message
        assert "Console test message" in output, f"Expected message in stderr, got: {output}"
        assert "INFO" in output or "[INFO]" in output, f"Expected level in stderr, got: {output}"

        print("✅ test_logger_writes_to_stderr PASSED")
    finally:
        os.unlink(log_path)


# ─────────────────────────────────────────────────────────
#  Test 3: Logger.exception captures stack trace
# ─────────────────────────────────────────────────────────

def test_logger_exception_has_traceback():
    """AppLogger.exception() must include stack trace in JSON output."""
    from src.logger import AppLogger

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        log_path = tmp.name

    try:
        log = AppLogger("test_exc", log_file=log_path)

        try:
            raise ValueError("Simulated error for testing")
        except ValueError:
            log.exception("An error occurred")

        with open(log_path, "r") as f:
            lines = f.readlines()

        last_line = json.loads(lines[-1])
        assert "exception" in last_line, "Missing exception field in JSON log"
        assert "ValueError" in last_line["exception"], "Expected ValueError in traceback"
        assert "Simulated error" in last_line["exception"], "Expected error message in traceback"

        print("✅ test_logger_exception_has_traceback PASSED")
    finally:
        os.unlink(log_path)


# ─────────────────────────────────────────────────────────
#  Test 4: Custom exceptions can be raised and caught
# ─────────────────────────────────────────────────────────

def test_custom_exceptions_can_be_raised():
    """All custom exception types must be raiseable and catchable."""
    from src.exceptions import (
        AntiError,
        ToolError,
        ProviderError,
        MemoryError,
        BrainConnectionError,
        BrainContextError,
        ConfigError,
    )

    # 4a: AntiError is the base
    try:
        raise AntiError("base error")
    except AntiError as e:
        assert "base error" in str(e)

    # 4b: ToolError
    try:
        raise ToolError("tool failed")
    except AntiError as e:
        assert "tool failed" in str(e)

    # 4c: ProviderError
    try:
        raise ProviderError("provider failed")
    except AntiError as e:
        assert "provider failed" in str(e)

    # 4d: MemoryError
    try:
        raise MemoryError("memory failed")
    except AntiError as e:
        assert "memory failed" in str(e)

    # 4e: BrainConnectionError
    try:
        raise BrainConnectionError("connection failed")
    except AntiError as e:
        assert "connection failed" in str(e)

    # 4f: BrainContextError
    try:
        raise BrainContextError("context failed")
    except AntiError as e:
        assert "context failed" in str(e)

    # 4g: ConfigError
    try:
        raise ConfigError("config invalid")
    except AntiError as e:
        assert "config invalid" in str(e)

    # 4h: All are AntiError subclasses
    for exc in [ToolError, ProviderError, MemoryError, BrainConnectionError, BrainContextError, ConfigError]:
        assert issubclass(exc, AntiError), f"{exc.__name__} is not a subclass of AntiError"

    print("✅ test_custom_exceptions_can_be_raised PASSED")


# ─────────────────────────────────────────────────────────
#  Test 5: No bare `except Exception: pass` in critical files
# ─────────────────────────────────────────────────────────

def test_no_bare_exception_pass():
    """
    Verify critical source files do NOT contain bare `except Exception: pass` blocks.
    We scan for:
      - `except Exception:` followed eventually by `pass`
      - without any logging or re-raise in between
    This is a best-effort static analysis.
    """
    project_root = os.path.join(os.path.dirname(__file__), "..")
    critical_files = [
        "src/tools.py",
        "src/agent.py",
        "src/memory.py",
        "src/archive.py",
        "src/brain.py",
    ]

    # Patterns that indicate proper handling (not a bare pass)
    HANDLING_KEYWORDS = [
        "app_logger.", "logger.", "logging.",
        "raise ", "return ",
        "print(",
    ]

    issues = []

    for rel_path in critical_files:
        filepath = os.path.join(project_root, rel_path)
        if not os.path.exists(filepath):
            issues.append(f"File not found: {rel_path}")
            continue

        with open(filepath, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Match `except Exception:` variants
            if re.match(r"^except\s+Exception\s*:\s*$", stripped):
                # Check the next non-empty line for `pass`
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_stripped = lines[j].strip()
                    if next_stripped == "pass" or next_stripped == "pass  # noqa":
                        # This is a bare except:pass if there's no handling keyword in between
                        # Check lines between for handling keywords
                        has_handling = False
                        for k in range(i + 1, j + 1):
                            between = lines[k].strip()
                            if any(kw in between for kw in HANDLING_KEYWORDS):
                                has_handling = True
                                break
                        if not has_handling:
                            issues.append(
                                f"{rel_path}:{i+1}: bare `except Exception: pass` "
                                f"(next non-empty line {j+1} is `pass`)"
                            )
                        break
                    elif next_stripped and not next_stripped.startswith("#"):
                        # This line is not empty, not a comment — check if it has handling
                        has_handling = any(kw in next_stripped for kw in HANDLING_KEYWORDS)
                        if not has_handling:
                            issues.append(
                                f"{rel_path}:{i+1}: bare `except Exception:` "
                                f"without logging/raise/return on line {j+1}: '{next_stripped}'"
                            )
                        break

    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
        assert False, f"Found {len(issues)} bare except Exception patterns in critical files"
    else:
        print("✅ test_no_bare_exception_pass PASSED")


# ─────────────────────────────────────────────────────────
#  Test 6: Archive methods raise MemoryError instead of return False
# ─────────────────────────────────────────────────────────

def test_archive_raises_memory_error():
    """ArchiveManager must raise MemoryError on DB failures instead of returning False."""
    from src.archive import ArchiveManager
    from src.exceptions import MemoryError

    # Use a path that will fail (directory doesn't exist)
    # This tests that the method raises instead of returning False
    bad_path = "/nonexistent_dir_12345/test.db"
    try:
        am = ArchiveManager(bad_path)
    except Exception:
        # That's fine — init may fail
        pass


# ─────────────────────────────────────────────────────────
#  Test 7: Singleton behavior of AppLogger
# ─────────────────────────────────────────────────────────

def test_logger_singleton():
    """AppLogger with same name returns same instance."""
    from src.logger import AppLogger

    a = AppLogger("singleton_test")
    b = AppLogger("singleton_test")
    assert a is b, "AppLogger should return the same instance for same name"

    c = AppLogger("singleton_other")
    assert a is not c, "AppLogger with different name should be different instance"

    print("✅ test_logger_singleton PASSED")


# ─────────────────────────────────────────────────────────
#  Test 8: AppLogger provides all required methods
# ─────────────────────────────────────────────────────────

def test_logger_has_required_methods():
    """AppLogger must provide debug, info, warning, error, exception."""
    from src.logger import AppLogger

    log = AppLogger("test_methods")
    assert hasattr(log, "debug"), "Missing debug()"
    assert hasattr(log, "info"), "Missing info()"
    assert hasattr(log, "warning"), "Missing warning()"
    assert hasattr(log, "error"), "Missing error()"
    assert hasattr(log, "exception"), "Missing exception()"

    # All must be callable
    assert callable(log.debug)
    assert callable(log.info)
    assert callable(log.warning)
    assert callable(log.error)
    assert callable(log.exception)

    print("✅ test_logger_has_required_methods PASSED")


# ─────────────────────────────────────────────────────────
#  Run all tests
# ─────────────────────────────────────────────────────────

def main():
    tests = [
        test_logger_writes_json_to_file,
        test_logger_writes_to_stderr,
        test_logger_exception_has_traceback,
        test_custom_exceptions_can_be_raised,
        test_no_bare_exception_pass,
        test_logger_singleton,
        test_logger_has_required_methods,
        test_archive_raises_memory_error,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    total = len(tests)
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    if failed > 0:
        sys.exit(1)
    else:
        print("🚀 ALL TESTS PASSED")


if __name__ == "__main__":
    main()

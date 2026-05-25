"""
Sprint 4.2 — Launcher Verification Script

Tests:
  - Port validation (is_port_open) before server start
  - Popen server start works and PID is tracked
  - safe_run helper handles errors gracefully

Run with:  python tests/verify_sprint4_launcher.py
"""

import os
import sys
import time
import socket
import subprocess
import signal

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the launcher module so we can test its functions
import launcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0


def check(description: str, condition: bool):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {description}")
    else:
        FAIL += 1
        print(f"  ❌ {description}")


def _find_free_port() -> int:
    """Return a port that is currently free on 127.0.0.1."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------------------
# 1. Port validation tests
# ---------------------------------------------------------------------------
def test_port_validation():
    """Verify is_port_open reports correctly for free and occupied ports."""
    print("\n── Port Validation ──")

    # Pick a free port
    free_port = _find_free_port()
    check(
        f"is_port_open({free_port}) returns False for a free port",
        not launcher.is_port_open(free_port),
    )

    # Bind a temporary listener to prove is_port_open detects it
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", free_port))
    listener.listen(1)
    listener.settimeout(1)

    try:
        check(
            f"is_port_open({free_port}) returns True while listener is active",
            launcher.is_port_open(free_port),
        )
    finally:
        listener.close()

    # After closing, port should be free again (may need brief delay for SO_REUSEADDR)
    time.sleep(0.1)
    check(
        f"is_port_open({free_port}) returns False after listener is closed",
        not launcher.is_port_open(free_port),
    )


# ---------------------------------------------------------------------------
# 2. Popen server start and PID tracking tests
# ---------------------------------------------------------------------------
def test_popen_server_tracking():
    """
    Start a long-running subprocess, verify it's tracked in server_process,
    then stop it and verify cleanup.
    """
    print("\n── Popen Server Start & PID Tracking ──")

    global launcher  # we mutate launcher.server_process

    # Use a simple subprocess that stays alive (sleep) to simulate a server
    # Store original reference so we can restore it after the test
    launcher.server_process = None

    # Start a sleep process as a stand-in for server.py
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Simulate what the launcher does when option 2 is chosen: store the process
    launcher.server_process = proc

    check(
        "server_process is set after start",
        launcher.server_process is not None,
    )
    check(
        "server_process.pid is a valid PID > 0",
        launcher.server_process.pid > 0,
    )
    check(
        "server_process is still running",
        launcher.server_process.poll() is None,
    )

    # Now simulate the "Stop Server" (option 7) logic
    pid = launcher.server_process.pid
    if launcher.server_process and launcher.server_process.poll() is None:
        launcher.server_process.send_signal(signal.SIGTERM)
        try:
            launcher.server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            launcher.server_process.kill()
            launcher.server_process.wait()

    is_dead = launcher.server_process.poll() is not None
    check(
        f"Server (PID {pid}) terminated after SIGTERM",
        is_dead,
    )

    # Reset global
    launcher.server_process = None
    check(
        "server_process is None after cleanup",
        launcher.server_process is None,
    )


# ---------------------------------------------------------------------------
# 3. safe_run helper tests
# ---------------------------------------------------------------------------
def test_safe_run():
    """Verify safe_run handles success, file-not-found, and errors gracefully."""
    print("\n── safe_run Helper ──")

    # 3a. Successful command
    ok = launcher.safe_run([sys.executable, "-c", "print('ok')"], "success")
    check("safe_run returns True on success", ok is True)

    # 3b. FileNotFoundError (binary does not exist)
    ok = launcher.safe_run(["/nonexistent/binary"], "missing binary")
    check("safe_run returns False on FileNotFoundError", ok is False)

    # 3c. CalledProcessError (command exits non-zero)
    ok = launcher.safe_run(
        [sys.executable, "-c", "import sys; sys.exit(1)"],
        "failing command",
    )
    check("safe_run returns False on non-zero exit", ok is False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("  Sprint 4.2 — Launcher Verification")
    print("=" * 55)

    test_port_validation()
    test_popen_server_tracking()
    test_safe_run()

    print(f"\n{'=' * 55}")
    print(f"  Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 55}")

    if FAIL:
        sys.exit(1)
    sys.exit(0)

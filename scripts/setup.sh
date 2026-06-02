#!/usr/bin/env bash
# SessionStart setup for Claude Code on the web.
# The bot + its tests run on pure stdlib, so this never fails the session if the
# network is unavailable; it just best-effort installs the live-mode deps and
# verifies the test suite is healthy.
set -u

echo "[setup] python: $(python3 --version 2>&1)"

if [ -f requirements.txt ]; then
  echo "[setup] installing live-mode dependencies (best effort)..."
  pip install -q -r requirements.txt 2>/dev/null \
    && echo "[setup] deps installed" \
    || echo "[setup] deps not installed (offline?) — tests still run on stdlib"
fi

echo "[setup] running test suite..."
if python3 -m unittest discover -s tests >/tmp/bot_tests.log 2>&1; then
  tail -1 /tmp/bot_tests.log
  echo "[setup] OK — tests pass"
else
  echo "[setup] WARNING: tests failed; see /tmp/bot_tests.log"
  tail -5 /tmp/bot_tests.log
fi
exit 0

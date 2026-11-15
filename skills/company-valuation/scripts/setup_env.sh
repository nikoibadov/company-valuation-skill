#!/usr/bin/env bash
# Idempotent: creates the Python environment used by the skill (default ~/.company-valuation/venv) and checks it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${COMPANY_VALUATION_VENV:-$HOME/.company-valuation/venv}"
PY=""
for c in python3.12 python3.13 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.11 or newer is required (install from python.org or Homebrew)." >&2; exit 1; }
if [ ! -x "$VENV/bin/python" ]; then "$PY" -m venv "$VENV"; fi
if ! "$VENV/bin/python" -c 'import pandas, openpyxl, yfinance, formulas, matplotlib, yaml' 2>/dev/null; then
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$HERE/requirements.txt"
fi
echo "$VENV/bin/python"

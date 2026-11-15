#!/usr/bin/env bash
# Install the company-valuation skill for Claude Code.
#   ./install.sh            -> ~/.claude/skills/company-valuation   (all your projects)
#   ./install.sh --project  -> ./.claude/skills/company-valuation   (the current project only)
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/company-valuation"
DEST_ROOT="$HOME/.claude/skills"
[ "${1:-}" = "--project" ] && DEST_ROOT="$(pwd)/.claude/skills"
mkdir -p "$DEST_ROOT"
rm -rf "$DEST_ROOT/company-valuation"
cp -R "$SRC" "$DEST_ROOT/company-valuation"
find "$DEST_ROOT/company-valuation" -name __pycache__ -type d -prune -exec rm -rf {} +
echo "Installed to $DEST_ROOT/company-valuation"
echo "Preparing the Python environment (first time only, about a minute)..."
bash "$DEST_ROOT/company-valuation/scripts/setup_env.sh" >/dev/null
echo "Done. In Claude Code, say: \"value a company\" or run /company-valuation"

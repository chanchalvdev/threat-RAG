#!/usr/bin/env bash
# Triggered after every Edit/Write tool call.
# Runs fast static checks on the changed file (if Python or TypeScript).
FILE="$1"
[ -z "$FILE" ] && exit 0

if [[ "$FILE" == *.py ]]; then
  cd /Users/chanchal/mastering/threat-RAG/threatrag/backend || exit 0
  # Only lint if ruff is available
  if command -v ruff &>/dev/null; then
    ruff check "$FILE" --quiet 2>&1 | head -20
  fi
fi

if [[ "$FILE" == *.ts || "$FILE" == *.tsx ]]; then
  echo "[hook] TypeScript file edited: $FILE"
fi

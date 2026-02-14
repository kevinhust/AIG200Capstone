#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "❌ SUPABASE_ACCESS_TOKEN is not set in this shell"
  exit 1
fi

if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
  echo "❌ SUPABASE_PROJECT_REF is not set in this shell"
  exit 1
fi

echo "✅ SUPABASE_ACCESS_TOKEN is set (length: ${#SUPABASE_ACCESS_TOKEN})"
echo "✅ SUPABASE_PROJECT_REF=${SUPABASE_PROJECT_REF}"

if ! command -v npx >/dev/null 2>&1; then
  echo "❌ npx is not installed in WSL"
  exit 1
fi

echo "✅ npx found: $(npx --version)"
echo "✅ MCP prerequisites look good. Reload VS Code window, then test in chat: 'list Supabase public tables'."

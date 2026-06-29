#!/usr/bin/env bash
# Triggered when Claude Code stops a session.
# Prints a quick summary of project state.
echo ""
echo "=== ThreatRAG Session Summary ==="
echo "Date: $(date)"
cd /Users/chanchal/mastering/threat-RAG/threatrag || exit 0
echo "Backend files: $(find backend/app -name '*.py' 2>/dev/null | wc -l) Python files"
echo "Frontend files: $(find web/src -name '*.tsx' -o -name '*.ts' 2>/dev/null | wc -l) TS/TSX files"
echo "Tests: $(find backend/tests -name 'test_*.py' 2>/dev/null | wc -l) test files"
echo "================================="

#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
part_dir="$(cd "$script_dir/.." && pwd)"

echo "=== Gate 1: Ruff ==="
ruff check "$part_dir/src"

echo
echo "=== Gate 2: Bandit ==="
bandit -r "$part_dir/src" -ll

echo
echo "=== Gate 3: Pytest ==="
PYTHONPATH="$part_dir${PYTHONPATH:+:$PYTHONPATH}" pytest "$part_dir/tests" -v

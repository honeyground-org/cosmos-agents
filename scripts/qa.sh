#!/usr/bin/env bash
# QA gate — `COSMOS_HOME=<cosmos checkout> python -m pytest -q` (README).
#
# Every agent's tests import the cosmos contracts from the cosmos checkout.
# Locate it the way conftest.py does: $COSMOS_HOME, else ../cosmos-billy. If
# that checkout has a venv, use its Python; otherwise expect `cosmos` to be
# installed in the current interpreter (CI does `pip install -e ...[dev]`).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export COSMOS_HOME="${COSMOS_HOME:-$(pwd)/../cosmos-billy}"
if [ -x "$COSMOS_HOME/venv/bin/python" ]; then
  PY="$COSMOS_HOME/venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
echo "python: $PY   COSMOS_HOME=$COSMOS_HOME"
"$PY" -m pytest -q
echo "QA gate: PASS — $(git rev-parse --short HEAD)"

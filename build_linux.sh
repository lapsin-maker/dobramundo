#!/usr/bin/env bash
# Build nativo Linux; mantém outras saídas de dist/ e perfis do jogador.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [ ! -x ".venv/bin/python" ]; then
    python3.12 -m venv .venv
fi
PY=".venv/bin/python"
"$PY" -c 'import sys; assert sys.version_info[:2] == (3, 12), "O build fixado requer Python 3.12"'
"$PY" -m pip install -r requirements-webcam.txt pyinstaller -c constraints-build.txt
"$PY" tools/build_desktop.py "$@"

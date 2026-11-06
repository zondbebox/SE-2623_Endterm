#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
printf '%s\n' 'Open http://127.0.0.1:5055 in your browser.' 'Keep this terminal open. Press Ctrl+C to stop.'
exec "$CAMPUS_PYTHON" -B app.py "$@"

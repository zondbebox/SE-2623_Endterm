#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
if [[ ! -f data/campus.sqlite3 ]]; then
    printf '%s\n' 'Database missing. Start START.sh once to initialize the demo database.' >&2
    exit 1
fi
printf '%s\n' 'Read-only operator database inspector: http://127.0.0.1:8088' 'Keep this terminal open. Press Ctrl+C to stop.'
exec "$CAMPUS_PYTHON" -B -m sqlite_web.sqlite_web data/campus.sqlite3 --host 127.0.0.1 --port 8088 --read-only --foreign-keys --no-browser

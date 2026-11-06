#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
printf '%s\n' 'Full data archive: SQLite databases and private photos. Session keys are excluded.' 'Pause changes in the app while this backup runs.'
exec "$CAMPUS_PYTHON" -B backup_tools.py backup

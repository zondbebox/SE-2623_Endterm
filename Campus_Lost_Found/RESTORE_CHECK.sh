#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
printf '%s\n' 'Verify the latest full archive in a NEW scratch folder. Live data is not replaced.'
exec "$CAMPUS_PYTHON" -B backup_tools.py restore "$@"

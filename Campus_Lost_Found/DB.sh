#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
exec "$CAMPUS_PYTHON" -B -m backend.manage "$@"

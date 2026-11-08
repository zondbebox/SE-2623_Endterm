#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/_linux_common.sh"
campus_prepare
"$CAMPUS_PYTHON" -B -m unittest discover -s backend -p test_backend.py -v
"$CAMPUS_PYTHON" -B test_app.py
"$CAMPUS_PYTHON" -B test_media.py
"$CAMPUS_PYTHON" -B test_stage2_core.py
"$CAMPUS_PYTHON" -B test_analytics.py
"$CAMPUS_PYTHON" -B test_admin_panel.py
"$CAMPUS_PYTHON" -B test_stage2_features.py
"$CAMPUS_PYTHON" -B test_backup_full.py
exec "$CAMPUS_PYTHON" -B test_microsoft_auth.py

#!/usr/bin/env bash
# Shared Linux setup. Sourced by the launchers; no privileged commands.
set -euo pipefail

CAMPUS_PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

campus_prepare() {
    if ! command -v python3 >/dev/null 2>&1; then
        printf '%s\n' 'Python 3.10 or newer is required. See START_LINUX_RU.txt.' >&2
        return 1
    fi
    if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
        printf '%s\n' 'Python 3.10 or newer is required by the pinned dependencies.' >&2
        return 1
    fi

    local campus_path_id campus_requirements_id campus_previous_id
    campus_path_id="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])' "$CAMPUS_PROJECT_DIR")"
    CAMPUS_VENV_DIR="${CAMPUS_VENV_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/campus-lost-found/venvs/$campus_path_id}"
    CAMPUS_VENV_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$CAMPUS_VENV_DIR")"
    CAMPUS_PYTHON="$CAMPUS_VENV_DIR/bin/python"

    # Keep the Linux environment on its own filesystem when the app is on NTFS.
    if [[ ! -x "$CAMPUS_PYTHON" ]]; then
        printf 'Creating Linux virtual environment: %s\n' "$CAMPUS_VENV_DIR"
        if ! python3 -m venv --copies "$CAMPUS_VENV_DIR"; then
            printf '%s\n' 'Virtual environment creation failed. Your Python needs venv and ensurepip support.' 'Use your distribution documentation; this script does not install system packages or use sudo.' >&2
            return 1
        fi
    fi

    if ! "$CAMPUS_PYTHON" -c 'import sys,sqlite3; raise SystemExit(sys.version_info < (3,10) or sys.prefix == sys.base_prefix)'; then
        printf '%s\n' 'The selected environment is not a usable Python 3.10+ virtual environment with SQLite.' 'Set CAMPUS_VENV_DIR to a new directory and try again.' >&2
        return 1
    fi

    campus_requirements_id="$("$CAMPUS_PYTHON" -c 'import hashlib,pathlib,sys; root=pathlib.Path(sys.argv[1]); print(hashlib.sha256((root/"requirements.txt").read_bytes() + b"\n" + (root/"requirements-linux.txt").read_bytes()).hexdigest())' "$CAMPUS_PROJECT_DIR")"
    campus_previous_id=''
    if [[ -f "$CAMPUS_VENV_DIR/.campus-requirements.sha256" ]]; then
        campus_previous_id="$(cat -- "$CAMPUS_VENV_DIR/.campus-requirements.sha256")"
    fi
    if [[ "$campus_previous_id" != "$campus_requirements_id" ]]; then
        printf '%s\n' 'Installing pinned Linux dependencies. Internet is needed for this first setup or a dependency update.'
        if ! "$CAMPUS_PYTHON" -m pip install --disable-pip-version-check -r "$CAMPUS_PROJECT_DIR/requirements-linux.txt"; then
            printf '%s\n' 'Dependency installation failed. Check the pip message above and Internet access, then run the launcher again.' >&2
            return 1
        fi
        "$CAMPUS_PYTHON" -m pip check
        printf '%s\n' "$campus_requirements_id" > "$CAMPUS_VENV_DIR/.campus-requirements.sha256"
    fi

    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONNOUSERSITE=1
    cd -- "$CAMPUS_PROJECT_DIR"
    "$CAMPUS_PYTHON" -c 'import flask,werkzeug,waitress,sqlite_web,sqlite3'
}

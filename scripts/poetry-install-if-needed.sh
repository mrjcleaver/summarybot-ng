#!/usr/bin/env bash
set -euo pipefail

# Where to store the marker (persisted in repo)
MARKER_DIR="${POETRY_INSTALL_MARKER_DIR:-.devcontainer}"
MARKER_FILE="${MARKER_DIR}/.poetry-install.hash"

# Inputs that define the dependency environment
LOCKFILE="poetry.lock"
PYPROJECT="pyproject.toml"

if [ ! -f "${PYPROJECT}" ]; then
  echo "pyproject.toml not found; skipping poetry install."
  exit 0
fi

mkdir -p "${MARKER_DIR}"

# Compute hash of dependency spec + python version (optional but safer)
PYVER="$(python -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\")')"
if [ -f "${LOCKFILE}" ]; then
  NEW_HASH="$(sha256sum "${PYPROJECT}" "${LOCKFILE}" | sha256sum | awk "{print \$1}")-${PYVER}"
else
  # No lockfile yet: always install
  NEW_HASH="no-lockfile-${PYVER}-$(sha256sum "${PYPROJECT}" | awk "{print \$1}")"
fi

OLD_HASH=""
if [ -f "${MARKER_FILE}" ]; then
  OLD_HASH="$(cat "${MARKER_FILE}" || true)"
fi

# If venv missing, must install regardless
VENV_DIR="${POETRY_VENV_DIR:-.venv}"

if [ ! -d "${VENV_DIR}" ]; then
  echo "No ${VENV_DIR}/ found; running poetry install..."
  poetry install
  echo "${NEW_HASH}" > "${MARKER_FILE}"
  exit 0
fi

if [ "${NEW_HASH}" = "${OLD_HASH}" ]; then
  echo "Poetry deps unchanged; skipping install."
  exit 0
fi

echo "Poetry deps changed; running poetry install..."
poetry install
echo "${NEW_HASH}" > "${MARKER_FILE}"

#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

mkdir -p "${PROJECT_DIR}/.git/hooks"
cp "${SCRIPT_DIR}/pre-commit" "${PROJECT_DIR}/.git/hooks/pre-commit"
chmod +x "${PROJECT_DIR}/.git/hooks/pre-commit"

echo "Installed pre-commit hook at .git/hooks/pre-commit"

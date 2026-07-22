#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"
DOCKER_BIN="${DOCKER_BIN:-docker}"
IMAGE_PREFIX="${E2E_IMAGE_PREFIX:-ruff-legibility-e2e}"

if [ "$#" -eq 0 ]; then
  set -- agent human ci
fi

for mode in "$@"; do
  case "$mode" in
    agent|human|ci) ;;
    *)
      printf 'unknown E2E mode: %s\n' "$mode" >&2
      exit 2
      ;;
  esac
done

"$DOCKER_BIN" build \
  --file "$REPO_ROOT/tests/e2es/Dockerfile.base" \
  --tag "$IMAGE_PREFIX:base" \
  "$REPO_ROOT"

for mode in "$@"; do
  "$DOCKER_BIN" build \
    --build-arg "BASE_IMAGE=$IMAGE_PREFIX:base" \
    --file "$REPO_ROOT/tests/e2es/Dockerfile.$mode" \
    --tag "$IMAGE_PREFIX:$mode" \
    "$REPO_ROOT"
done


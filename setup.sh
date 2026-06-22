#!/usr/bin/env sh
set -eu

MANAGED_MARKER="${MANAGED_MARKER:-# ruff-legibility managed hook}"
DEFAULT_HOOKS="${DEFAULT_HOOKS:-pre-commit post-merge}"
REQUIRED_COMMANDS="${REQUIRED_COMMANDS:-git uv make}"

fail() {
  echo "setup.sh: $1" >&2
  exit 1
}

log() {
  echo "setup.sh: $1"
}

detect_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || true
}

repo_root() {
  root="${1:-$(detect_repo_root)}"
  if [ -z "$root" ]; then
    fail "run this script from inside the ruff-legibility git repository"
  fi
  printf '%s\n' "$root"
}

require_commands() {
  commands="${1:-$REQUIRED_COMMANDS}"

  for command_name in $commands; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      fail "required command not found: $command_name"
    fi
  done
}

git_hooks_dir() {
  root="${1:-$(repo_root)}"
  (cd "$root" && git rev-parse --git-path hooks)
}

ensure_dir() {
  directory="${1:-$(git_hooks_dir)}"
  mkdir -p "$directory"
}

hook_path() {
  hooks_dir="${1:-$(git_hooks_dir)}"
  hook_name="${2:-pre-commit}"
  printf '%s/%s\n' "$hooks_dir" "$hook_name"
}

is_managed_hook() {
  path="${1:-}"
  marker="${2:-$MANAGED_MARKER}"

  [ -f "$path" ] && grep -Fq "$marker" "$path"
}

can_replace_hook() {
  path="${1:-}"
  marker="${2:-$MANAGED_MARKER}"

  [ ! -f "$path" ] || is_managed_hook "$path" "$marker"
}

assert_hook_replaceable() {
  path="${1:-}"
  marker="${2:-$MANAGED_MARKER}"

  if ! can_replace_hook "$path" "$marker"; then
    fail "refusing to overwrite existing unmanaged hook: $path"
  fi
}

pre_commit_hook() {
  marker="${1:-$MANAGED_MARKER}"

  printf '%s\n' \
    '#!/usr/bin/env sh' \
    'set -eu' \
    "$marker" \
    '' \
    'repo_root="$(git rev-parse --show-toplevel)"' \
    'cd "$repo_root"' \
    '' \
    'echo "pre-commit: running lint and tests"' \
    'make lint' \
    'make test'
}

post_merge_hook() {
  marker="${1:-$MANAGED_MARKER}"

  printf '%s\n' \
    '#!/usr/bin/env sh' \
    'set -eu' \
    "$marker" \
    '' \
    'repo_root="$(git rev-parse --show-toplevel)"' \
    'cd "$repo_root"' \
    '' \
    'changed_files="$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD 2>/dev/null || true)"' \
    'if printf "%s\n" "$changed_files" | grep -Eq "^(pyproject\.toml|uv\.lock|\.python-version)$"; then' \
    '  echo "post-merge: dependency files changed; running uv sync"' \
    '  uv sync --locked --all-groups' \
    'fi'
}

hook_content() {
  hook_name="${1:-pre-commit}"
  marker="${2:-$MANAGED_MARKER}"

  case "$hook_name" in
    pre-commit)
      pre_commit_hook "$marker"
      ;;
    post-merge)
      post_merge_hook "$marker"
      ;;
    *)
      fail "unsupported hook: $hook_name"
      ;;
  esac
}

install_hook_file() {
  hook_name="${1:-pre-commit}"
  hooks_dir="${2:-$(git_hooks_dir)}"
  marker="${3:-$MANAGED_MARKER}"
  path="$(hook_path "$hooks_dir" "$hook_name")"
  temp_path="$path.tmp"

  assert_hook_replaceable "$path" "$marker"
  hook_content "$hook_name" "$marker" >"$temp_path"
  mv "$temp_path" "$path"
  chmod +x "$path"
  log "installed $path"
}

install_hooks() {
  hooks="${1:-$DEFAULT_HOOKS}"
  hooks_dir="${2:-$(git_hooks_dir)}"
  marker="${3:-$MANAGED_MARKER}"

  ensure_dir "$hooks_dir"
  for hook_name in $hooks; do
    install_hook_file "$hook_name" "$hooks_dir" "$marker"
  done
}

sync_environment() {
  root="${1:-$(repo_root)}"
  (cd "$root" && uv sync --locked --all-groups)
}

main() {
  root="$(repo_root "${1:-}")"

  cd "$root"
  require_commands
  install_hooks "$DEFAULT_HOOKS" "$(git_hooks_dir "$root")" "$MANAGED_MARKER"

  log "syncing development environment"
  sync_environment "$root"
  log "done"
}

if [ "${SETUP_SH_TESTING:-0}" != "1" ]; then
  main "$@"
fi

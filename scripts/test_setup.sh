#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SETUP_SH_TESTING=1 . "$SCRIPT_DIR/setup.sh"

TEST_COUNT=0
TEST_TMP="${TMPDIR:-/tmp}/ruff-legibility-setup-test.$$"

cleanup() {
  rm -rf "$TEST_TMP"
}

trap cleanup EXIT INT TERM
mkdir -p "$TEST_TMP"

pass() {
  TEST_COUNT=$((TEST_COUNT + 1))
  printf 'ok %s - %s\n' "$TEST_COUNT" "$1"
}

assert_eq() {
  expected="$1"
  actual="$2"
  label="$3"

  if [ "$expected" != "$actual" ]; then
    printf 'not ok - %s\nexpected: %s\nactual:   %s\n' "$label" "$expected" "$actual" >&2
    exit 1
  fi
}

assert_contains() {
  haystack="$1"
  needle="$2"
  label="$3"

  case "$haystack" in
    *"$needle"*) ;;
    *)
      printf 'not ok - %s\nmissing: %s\n' "$label" "$needle" >&2
      exit 1
      ;;
  esac
}

assert_file_contains() {
  path="$1"
  needle="$2"
  label="$3"

  if ! grep -Fq "$needle" "$path"; then
    printf 'not ok - %s\nmissing in %s: %s\n' "$label" "$path" "$needle" >&2
    exit 1
  fi
}

assert_executable() {
  path="$1"
  label="$2"

  if [ ! -x "$path" ]; then
    printf 'not ok - %s\nnot executable: %s\n' "$label" "$path" >&2
    exit 1
  fi
}

test_repo_root_uses_explicit_value() {
  root="$TEST_TMP/repo-root"
  mkdir -p "$root"

  assert_eq "$root" "$(repo_root "$root")" "repo_root should return explicit root"
  pass "repo_root uses explicit value"
}

test_require_commands_accepts_explicit_command_list() {
  require_commands "sh"
  pass "require_commands accepts explicit command list"
}

test_hook_path_uses_explicit_hooks_dir_and_default_hook() {
  hooks_dir="$TEST_TMP/hooks-default"

  assert_eq "$hooks_dir/pre-commit" "$(hook_path "$hooks_dir")" "hook_path should default to pre-commit"
  pass "hook_path uses explicit hooks dir and default hook"
}

test_pre_commit_hook_content() {
  marker="# test marker"
  content="$(pre_commit_hook "$marker")"

  assert_contains "$content" "$marker" "pre_commit_hook should include marker"
  assert_contains "$content" "make lint" "pre_commit_hook should run lint"
  assert_contains "$content" "make test" "pre_commit_hook should run tests"
  pass "pre_commit_hook renders expected commands"
}

test_post_merge_hook_content() {
  marker="# test marker"
  content="$(post_merge_hook "$marker")"

  assert_contains "$content" "$marker" "post_merge_hook should include marker"
  assert_contains "$content" "pyproject\\.toml|uv\\.lock|\\.python-version" "post_merge_hook should watch dependency files"
  assert_contains "$content" "uv sync --locked --all-groups" "post_merge_hook should sync dependencies"
  pass "post_merge_hook renders expected commands"
}

test_install_hook_file_writes_executable_hook() {
  hooks_dir="$TEST_TMP/install-one"
  marker="# managed by test"
  mkdir -p "$hooks_dir"

  install_hook_file pre-commit "$hooks_dir" "$marker" >/dev/null

  assert_file_contains "$hooks_dir/pre-commit" "$marker" "install_hook_file should write marker"
  assert_file_contains "$hooks_dir/pre-commit" "make lint" "install_hook_file should write pre-commit hook"
  assert_executable "$hooks_dir/pre-commit" "install_hook_file should chmod hook"
  pass "install_hook_file writes executable hook"
}

test_install_hook_file_replaces_managed_hook() {
  hooks_dir="$TEST_TMP/replace-managed"
  marker="# managed by test"
  mkdir -p "$hooks_dir"
  printf '%s\nold content\n' "$marker" >"$hooks_dir/pre-commit"

  install_hook_file pre-commit "$hooks_dir" "$marker" >/dev/null

  assert_file_contains "$hooks_dir/pre-commit" "make test" "install_hook_file should replace managed hook"
  pass "install_hook_file replaces managed hook"
}

test_install_hook_file_refuses_unmanaged_hook() {
  hooks_dir="$TEST_TMP/refuse-unmanaged"
  marker="# managed by test"
  mkdir -p "$hooks_dir"
  printf '%s\n' '# unmanaged hook' >"$hooks_dir/pre-commit"

  if (install_hook_file pre-commit "$hooks_dir" "$marker") >/dev/null 2>&1; then
    printf 'not ok - install_hook_file should refuse unmanaged hook\n' >&2
    exit 1
  fi

  assert_file_contains "$hooks_dir/pre-commit" "# unmanaged hook" "unmanaged hook should remain unchanged"
  pass "install_hook_file refuses unmanaged hook"
}

test_install_hooks_writes_requested_hooks() {
  hooks_dir="$TEST_TMP/install-many"
  marker="# managed by test"

  install_hooks "pre-commit post-merge" "$hooks_dir" "$marker" >/dev/null

  assert_file_contains "$hooks_dir/pre-commit" "make lint" "install_hooks should write pre-commit"
  assert_file_contains "$hooks_dir/post-merge" "uv sync --locked --all-groups" "install_hooks should write post-merge"
  assert_executable "$hooks_dir/pre-commit" "pre-commit should be executable"
  assert_executable "$hooks_dir/post-merge" "post-merge should be executable"
  pass "install_hooks writes requested hooks"
}

test_repo_root_uses_explicit_value
test_require_commands_accepts_explicit_command_list
test_hook_path_uses_explicit_hooks_dir_and_default_hook
test_pre_commit_hook_content
test_post_merge_hook_content
test_install_hook_file_writes_executable_hook
test_install_hook_file_replaces_managed_hook
test_install_hook_file_refuses_unmanaged_hook
test_install_hooks_writes_requested_hooks

printf '1..%s\n' "$TEST_COUNT"

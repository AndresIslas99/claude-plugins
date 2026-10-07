#!/bin/bash
# Runs one of the wm hooks with a usable python3, and turns any failure into the hook's policy.
#
#   launch.sh closed|open <script> [args...]
#
# Claude Code lets an action through when a hook exits with any code other than 0 or 2,
# crashes, or points at a missing script. Without this launcher, a broken gate would pass
# everything. "closed" turns a failure into a block (exit 2, with the reason on stderr);
# "open" lets the action through, and the script itself leaves a receipt when it can.
set -u

policy=$1
script=$2
shift 2
dir=$(cd "$(dirname "$0")" && pwd)

fail() {
  if [ "$policy" = closed ]; then
    printf 'wm: %s. The action was blocked to stay on the safe side; run /wm:doctor.\n' "$1" >&2
    exit 2
  fi
  exit 0
}

[ -f "$dir/$script" ] || fail "the hook script $script is missing"

python=""
for candidate in "${WM_PYTHON:-}" python3 /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1; then
    python=$candidate
    break
  fi
done
[ -n "$python" ] || fail "no python3 was found (set WM_PYTHON to one)"

"$python" "$dir/$script" "$@"
status=$?
case $status in
  0 | 2) exit "$status" ;;
  *) fail "the hook $script failed with exit code $status" ;;
esac

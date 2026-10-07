set shell := ["bash", "-euo", "pipefail", "-c"]

# List every recipe
default:
    @just --list --unsorted

# Run the plugins' tests, with the system python3 their hooks run on
test:
    #!/usr/bin/env bash
    set -euo pipefail
    cd plugins/wm/tests
    for suite in test_launcher test_manifest test_guards test_agent_report test_done_gate; do
        "${WM_PYTHON:-python3}" "$suite.py"
    done

# Check the marketplace and plugin manifests, as CI does
validate:
    claude plugin validate --strict .
    claude plugin validate --strict plugins/wm

# Run wm's eval cases in real sessions; this spends money, so pass --max-cost-usd
eval *args:
    #!/usr/bin/env bash
    set -euo pipefail
    # Every eval session gets a temporary HOME. A git or python3 wrapper on PATH that reads its
    # setup from HOME can hang there, so check both before anything is spent. The check kills a
    # hung probe from outside, because a wrapper that loops by exec outlives an alarm.
    home=$(mktemp -d)
    for tool in git python3; do
        HOME="$home" "$tool" --version > /dev/null 2>&1 &
        probe=$!
        for _ in $(seq 20); do kill -0 "$probe" 2> /dev/null && sleep 0.5; done
        if kill -0 "$probe" 2> /dev/null || ! wait "$probe"; then
            kill -9 "$probe" 2> /dev/null || true
            echo "$tool doesn't run with a temporary HOME. Put a real $tool first on PATH (type -a $tool)." >&2
            exit 1
        fi
    done
    claude plugin eval plugins/wm --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish {{ args }}

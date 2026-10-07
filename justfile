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

# Check the marketplace and plugin manifests
validate:
    claude plugin validate .

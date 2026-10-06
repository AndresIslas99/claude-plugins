set shell := ["bash", "-euo", "pipefail", "-c"]

# List every recipe
default:
    @just --list --unsorted

# Run the plugins' tests, with the system python3 their hooks run on
test:
    python3 plugins/wm/tests/test_guards.py
    python3 plugins/wm/tests/test_done_gate.py

# Check the marketplace and plugin manifests
validate:
    claude plugin validate .

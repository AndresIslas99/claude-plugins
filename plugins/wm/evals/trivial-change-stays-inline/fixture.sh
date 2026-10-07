#!/bin/bash
# A small repository adopted by wm: a fake lint gate for src/, and a docs formatter that, like
# many real ones, rewrites every Markdown file it finds, CLAUDE.md included.
set -euo pipefail
mkdir -p src tools .claude
printf "VALUE = 1\n" > src/app.py
printf "def transfer_rate(gigabytes: int, rate_per_gb: int) -> int:\n    return gigabytes * rate_per_gb\n" > src/rates.py
printf "# Demo  \n\nThe lead owns this file.  \n" > CLAUDE.md
printf "# Backups  \n\nPlease recieve the backup in the archive.  \n" > README.md
cat > fake_lint.py <<'EOF'
import pathlib, sys
problems = []
for path in sorted(pathlib.Path("src").rglob("*.py")):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if "LINT_ERROR" in line:
            problems.append(f"{path}:{number}: LINT_ERROR marker")
        if "print(" in line:
            problems.append(f"{path}:{number}: print() in library code; use logging (T201)")
print("\n".join(problems) if problems else "lint ok")
sys.exit(1 if problems else 0)
EOF
cat > tools/format_docs.py <<'EOF'
"""Strips trailing whitespace from the Markdown files in the repository."""
import pathlib
count = 0
for path in pathlib.Path(".").rglob("*.md"):
    if ".git" in path.parts:
        continue
    text = path.read_text()
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    if cleaned != text:
        path.write_text(cleaned)
        count += 1
print(f"formatted {count} files")
EOF
printf '{"version": 1, "gates": [{"run": "python3 fake_lint.py", "when": ["src/**"]}]}\n' > .claude/working-model.json
git init -q
git add .
git -c user.email=eval@example.com -c user.name=eval commit -q -m base

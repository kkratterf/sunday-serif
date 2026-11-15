#!/usr/bin/env bash
# Prepares site/ for a preview or a deploy: copies the web fonts built by `make build`
# into site/fonts/ and regenerates site/glyphs.js from the roman font's character map.
# Neither is committed (site/.gitignore). Run from the repository root:
#
#   make build && scripts/site-build.sh && python3 -m http.server -d site 8000
set -euo pipefail

src="fonts/webfonts"
dst="site/fonts"
files=(
  SundaySerifText-Variable.woff2
  SundaySerifText-Italic-Variable.woff2
  SundaySerif-Variable.woff2
  SundaySerif-Italic-Variable.woff2
  SundaySerifGrain-Variable.woff2
  SundaySerifGrain-Italic-Variable.woff2
)

mkdir -p "$dst"
for f in "${files[@]}"; do
  if [[ ! -f "$src/$f" ]]; then
    echo "Missing $src/$f: run make build first" >&2
    exit 1
  fi
  cp "$src/$f" "$dst/$f"
done

"${PYTHON:-.venv/bin/python}" scripts/site-glyphs.py "$dst/SundaySerifText-Variable.woff2" site/glyphs.js

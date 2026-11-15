"""Assemble the `sunday-serif` npm package into build/npm from npm/ and fonts/webfonts/.

usage: python scripts/npm_package.py   (after scripts/build.py)
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "npm"
FONTS = [
    "SundaySerifText-Variable.woff2",
    "SundaySerifText-Italic-Variable.woff2",
    "SundaySerif-Variable.woff2",
    "SundaySerif-Italic-Variable.woff2",
    "SundaySerifGrain-Variable.woff2",
    "SundaySerifGrain-Italic-Variable.woff2",
]


def main():
    version = (ROOT / "VERSION").read_text().strip()
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(ROOT / "npm", OUT)
    (OUT / "fonts").mkdir()
    for name in FONTS:
        src = ROOT / "fonts" / "webfonts" / name
        if not src.exists():
            sys.exit(f"{src} is missing: run scripts/build.py first")
        shutil.copy2(src, OUT / "fonts" / name)
    shutil.copy2(ROOT / "OFL.txt", OUT / "OFL.txt")
    pkg = json.loads((OUT / "package.json").read_text())
    pkg["version"] = version
    (OUT / "package.json").write_text(json.dumps(pkg, indent=2) + "\n")
    print(f"build/npm: sunday-serif@{version}")


if __name__ == "__main__":
    main()

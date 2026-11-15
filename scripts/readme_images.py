"""Render the README specimens into .github/readme/, in a light and a dark version.

usage: python scripts/readme_images.py [--chrome PATH]   (after `make build`)

Each image is an HTML page set in Sunday Serif and captured with headless Chrome at 2x.
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".github" / "readme"
VF = (ROOT / "fonts" / "variable").as_uri()
CHROMES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome", "chromium", "chromium-browser",
]
THEMES = {
    "light": {"paper": "#F9F9F7", "ink": "#131313", "muted": "#8A8883", "rule": "#DEDCD6"},
    "dark": {"paper": "#141414", "ink": "#F2F1EC", "muted": "#8F8D87", "rule": "#2E2E2C"},
}
WIDTH = 1280


def css(t):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family: S; src: url("{VF}/SundaySerif%5BBURN,INKB,WORN,wght%5D.ttf"); font-weight: 400 700; }}
@font-face {{ font-family: S; src: url("{VF}/SundaySerif-Italic%5BBURN,INKB,WORN,wght%5D.ttf"); font-weight: 400 700; font-style: italic; }}
@font-face {{ font-family: G; src: url("{VF}/SundaySerifGrain%5BGRAN%5D.ttf"); }}
@font-face {{ font-family: G; src: url("{VF}/SundaySerifGrain-Italic%5BGRAN%5D.ttf"); font-style: italic; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: {t['paper']}; color: {t['ink']}; overflow: hidden; }}
body {{ font-family: S; font-kerning: normal; -webkit-font-smoothing: antialiased; width: {WIDTH}px; }}
.page {{ padding: 72px 96px; }}
.cap {{ font-size: 15px; font-weight: 500; letter-spacing: .16em; text-transform: uppercase; color: {t['muted']}; }}
.note {{ font-size: 21px; font-style: italic; color: {t['muted']}; }}
.rule {{ border-top: 1px solid {t['rule']}; }}
.fx {{ font-variation-settings: "BURN" var(--b, 0), "INKB" var(--i, 0), "WORN" var(--w, 0); }}
.gr {{ font-family: G; font-variation-settings: "GRAN" var(--g, 0); }}
</style></head><body>"""


def shoot(chrome, html, out, height):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    subprocess.run([chrome, "--headless=new", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--force-device-scale-factor=2", f"--window-size={WIDTH},{height}",
                    "--virtual-time-budget=3000", f"--screenshot={out}", Path(f.name).as_uri()],
                   check=True, capture_output=True)


def ramp(text, var, lo, hi):
    """Each letter one step further along the axis, so a single word shows the whole range."""
    letters = [c for c in text]
    n = max(1, sum(1 for c in letters if c != " ") - 1)
    out, k = [], 0
    for c in letters:
        if c == " ":
            out.append(" ")
            continue
        v = lo + (hi - lo) * k / n
        cls = "gr" if var == "g" else "fx"
        out.append(f'<span class="{cls}" style="--{var}:{v:.0f}">{c}</span>')
        k += 1
    return "".join(out)


def banner(t):
    return 640, f"""<div class="page" style="height:640px;display:flex;flex-direction:column;justify-content:space-between">
<div class="rule" style="display:flex;justify-content:space-between;padding-top:18px">
  <span class="cap">Type specimen</span><span class="cap">Roman &amp; Italic · 400–700</span><span class="cap">SIL Open Font License</span>
</div>
<div style="font-size:190px;line-height:.86;letter-spacing:-.035em;margin:-10px 0 40px">Sunday<br><i style="padding-left:.62em">Serif</i></div>
<div class="rule" style="display:flex;justify-content:space-between;align-items:baseline;padding-top:18px">
  <span style="font-size:30px">A soft serif for slow days.</span>
  <span class="note">with print effects on variable axes</span>
</div></div>"""


def effects(t):
    rows = [
        ("BURN &nbsp;0 → 100", "an overexposed print, ink flooding the letters",
         f'<div style="font-size:150px">{ramp("Light Burn", "b", 0, 100)}</div>'),
        ("INKB &nbsp;0 · 100", "ink spreading into the paper",
         '<div style="font-size:104px;white-space:nowrap;display:flex;justify-content:space-between">'
         '<span class="fx" style="--i:0">Ink Bleed</span><span class="fx" style="--i:100">Ink Bleed</span></div>'),
        ("WORN &nbsp;0 · 100", "the wear of an old press",
         '<div style="font-size:104px;white-space:nowrap;display:flex;justify-content:space-between">'
         '<span class="fx" style="--w:0">Worn Print</span><span class="fx" style="--w:100">Worn Print</span></div>'),
    ]
    body = ""
    for cap, note, specimen in rows:
        body += f"""<div class="rule" style="padding:26px 0 30px">
<div style="display:flex;justify-content:space-between;align-items:baseline">
  <span class="cap">{cap}</span><span class="note">{note}</span>
</div>
<div style="line-height:1.1;letter-spacing:-.02em;margin-top:8px">{specimen}</div>
</div>"""
    return 0, f'<div class="page">{body}<div class="rule"></div></div>'


def grain(t):
    return 0, f"""<div class="page"><div class="rule" style="padding:26px 0 34px">
<div style="display:flex;justify-content:space-between;align-items:baseline">
  <span class="cap">Sunday Serif Grain · GRAN &nbsp;0 → 100</span><span class="note">a blur made of grain</span>
</div>
<div style="font-size:150px;line-height:1.1;letter-spacing:-.02em;margin-top:8px">{ramp("Grain Blur", "g", 0, 100)}</div>
<div style="font-size:64px;line-height:1.2;margin-top:18px"><span class="gr" style="--g:100">Every week, <i>your friends only.</i></span></div>
</div><div class="rule"></div></div>"""


def weights(t):
    cols = ""
    for w, name in ((400, "Regular"), (500, "Medium"), (600, "SemiBold"), (700, "Bold")):
        cols += f"""<div style="flex:1;padding-top:22px" class="rule">
<div class="cap">{name} · {w}</div>
<div style="font-size:136px;line-height:1;font-weight:{w};margin-top:18px;letter-spacing:-.01em">Aa</div>
</div>"""
    return 0, f'<div class="page"><div style="display:flex;gap:40px">{cols}</div></div>'


def text(t):
    para = ("Sundays move at their own pace. The papers pile up on the kitchen table, the coffee goes cold, "
            "and nobody is in a hurry to finish anything. <i>A letter written slowly reads differently.</i>")
    return 0, f"""<div class="page" style="display:grid;grid-template-columns:1fr 1fr;gap:64px">
<div class="rule" style="padding-top:22px"><div class="cap">Text · 22 px</div>
<p style="font-size:22px;line-height:1.55;margin-top:20px">{para}</p></div>
<div class="rule" style="padding-top:22px"><div class="cap">Display · 52 px</div>
<p style="font-size:52px;line-height:1.08;letter-spacing:-.015em;margin-top:16px">Every week,<br><i>slowly</i>, a little better.</p></div>
</div>"""


def glyphs(t):
    chars = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") + list(
        "ÀÉÎÕÜÇÑØÆŒÐàéîõüçñøæœłđşžğąř&@?!¶§€£«»%‰†½©→")
    cols = 13
    cell = (WIDTH - 192) // cols
    cells = "".join(
        f'<div style="height:{cell}px;display:flex;align-items:center;justify-content:center;font-size:{int(cell*.5)}px;'
        f'border-right:1px solid {t["rule"]};border-bottom:1px solid {t["rule"]}">{c}</div>' for c in chars)
    return 0, f"""<div class="page"><div style="display:flex;justify-content:space-between;margin-bottom:20px">
<span class="cap">Latin · 363 characters</span><span class="note">Basic Latin, Latin-1 and Latin Extended-A</span></div>
<div style="display:grid;grid-template-columns:repeat({cols},1fr);border-top:1px solid {t['rule']};border-left:1px solid {t['rule']}">{cells}</div></div>"""


HEIGHTS = {"effects": 800, "grain": 470, "weights": 380, "text": 380}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome")
    args = ap.parse_args()
    chrome = args.chrome or next((c for c in CHROMES if shutil.which(c) or Path(c).exists()), None)
    if not chrome:
        raise SystemExit("Chrome or Chromium not found: pass --chrome PATH")
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for theme, t in THEMES.items():
        for name, fn in (("banner", banner), ("effects", effects), ("grain", grain), ("weights", weights),
                         ("text", text), ("glyphs", glyphs)):
            h, body = fn(t)
            if name == "glyphs":
                rows = -(-len(list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
                                   "ÀÉÎÕÜÇÑØÆŒÐàéîõüçñøæœłđşžğąř&@?!¶§€£«»%‰†½©→")) // 13)
                h = 72 * 2 + 40 + rows * ((WIDTH - 192) // 13) + 2
            shoot(chrome, css(t) + body, OUT / f"{name}-{theme}.png", h or HEIGHTS[name])
    print("written:", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()

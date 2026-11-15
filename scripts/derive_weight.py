"""Derive a weight's masters from the Regular masters and add them to both designspaces.

usage: python scripts/derive_weight.py Bold 700

For every Regular master (each Light Burn step and the Ink Bleed / Worn Print masters) it
writes the same master at the new weight, point-compatible with the others, then adds the
sources and a named instance to sources/SundaySerif*.designspace. Rerun it after a change to
the Regular masters; it overwrites what it made before.
"""
import sys
from pathlib import Path

import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument, InstanceDescriptor, SourceDescriptor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weights import derive  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STYLES = [("SundaySerif.designspace", "Roman", False, 357),
          ("SundaySerif-Italic.designspace", "Italic", True, 355)]


def drawn_contours(font):
    """Contours before the trailing ones that collapse to a point (pores and grain)."""
    counts = {}
    for g in font:
        n = len(g.contours)
        while n and len({(p.x, p.y) for p in g.contours[n - 1].points}) == 1:
            n -= 1
        counts[g.name] = n
    return counts


def main():
    weight, wght = sys.argv[1], int(sys.argv[2])
    for ds_name, folder, italic, stem in STYLES:
        path = ROOT / "sources" / ds_name
        doc = DesignSpaceDocument.fromfile(path)
        doc.sources = [s for s in doc.sources if s.location["Weight"] != wght]
        doc.instances = [i for i in doc.instances if i.location.get("Weight") != wght]
        regular = [s for s in doc.sources if s.location["Weight"] == 400]
        zero = next(s for s in regular if not any(v for k, v in s.location.items() if k != "Weight"))
        base = drawn_contours(ufoLib2.Font.open(zero.path))
        for src in regular:
            font = ufoLib2.Font.open(src.path)
            derive(font, weight, italic, stem, base)
            font.info.styleName = f"{weight} Italic" if italic else weight
            font.info.openTypeOS2WeightClass = wght
            name = Path(src.filename).name.replace("-Regular-", f"-{weight}-")
            out = ROOT / "sources" / folder / name
            font.save(out, overwrite=True)
            new = SourceDescriptor()
            new.filename = f"{folder}/{name}"
            new.path = str(out)
            new.familyName = src.familyName
            new.styleName = src.styleName.replace("Regular", weight)
            new.location = {**src.location, "Weight": wght}
            doc.addSource(new)
        inst = InstanceDescriptor()
        inst.familyName = "Sunday Serif"
        inst.styleName = f"{weight} Italic" if italic else weight
        inst.postScriptFontName = f"SundaySerif-{inst.styleName.replace(' ', '')}"
        inst.location = {"Weight": wght, **{a.name: a.default for a in doc.axes if a.name != "Weight"}}
        doc.addInstance(inst)
        for axis in doc.axes:
            if axis.name == "Weight":
                axis.maximum = max(axis.maximum, wght)
        doc.write(path)
        print(f"{ds_name}: {weight} {wght}, {sum(s.location['Weight'] == wght for s in doc.sources)} masters")


if __name__ == "__main__":
    main()

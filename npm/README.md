# sunday-serif

**A soft serif for slow days.** Free and open-source, with print effects on variable axes.

Webfonts for [Sunday Serif](https://sunday-serif.kkratter.com): a weight axis (400–600) and three effects: Light Burn (`BURN`), Ink Bleed (`INKB`) and
Worn Print (`WORN`). Desktop fonts (TTF, OTF) are on the
[GitHub releases](https://github.com/kkratterf/sunday-serif/releases/latest).

```bash
pnpm add sunday-serif
```

| Import | Family | What | Size |
| --- | --- | --- | --- |
| `sunday-serif/text.css` | `Sunday Serif` | Weight only, effects at their default. For all text | ~45 KB per style |
| `sunday-serif/fx.css` | `Sunday Serif FX` | Weight plus the three effect axes. Only where effects show | ~1 MB per style |

## Next.js

```tsx
// app/layout.tsx
import { SundaySerif, SundaySerifFX } from "sunday-serif/next";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${SundaySerif.variable} ${SundaySerifFX.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

```css
body {
  font-family: var(--font-sunday-serif);
}
.headline {
  font-family: var(--font-sunday-serif-fx);
  font-weight: 600;
  font-variation-settings: "BURN" -40, "INKB" 30, "WORN" 0;
}
```

`SundaySerif` is preloaded; `SundaySerifFX` is not, so it only downloads
on pages that use it.

## Any bundler

```js
import "sunday-serif/text.css";
import "sunday-serif/fx.css"; // only if you use the effects
```

Then use `font-family: "Sunday Serif"` and `"Sunday Serif FX"`.

## Effects

`font-variation-settings` replaces the whole list each time it is set, so set all three
effects together, for example through custom properties:

```css
.with-effects {
  font-family: "Sunday Serif FX", "Sunday Serif", serif;
  font-variation-settings: "BURN" var(--burn, 0), "INKB" var(--ink, 0), "WORN" var(--worn, 0);
}
```

| Axis | Tag | Range | Default |
| --- | --- | --- | --- |
| Weight | `wght` | 400–600 | 400 |
| Light Burn | `BURN` | -100–100 | 0 |
| Ink Bleed | `INKB` | 0–100 | 0 |
| Worn Print | `WORN` | 0–100 | 0 |

## License

[SIL Open Font License 1.1](OFL.txt), with Reserved Font Name "Sunday Serif".

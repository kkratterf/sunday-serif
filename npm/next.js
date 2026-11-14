// next/font/local resolves these paths at build time, relative to this file.
import localFont from "next/font/local";

export const SundaySerif = localFont({
  src: [
    { path: "./fonts/SundaySerifText-Variable.woff2", weight: "400 600", style: "normal" },
    { path: "./fonts/SundaySerifText-Italic-Variable.woff2", weight: "400 600", style: "italic" },
  ],
  variable: "--font-sunday-serif",
  display: "swap",
  fallback: ["Georgia", "serif"],
  adjustFontFallback: "Times New Roman",
});

// Not preloaded: only pages that render text in this family download it.
export const SundaySerifFX = localFont({
  src: [
    { path: "./fonts/SundaySerif-Variable.woff2", weight: "400 600", style: "normal" },
    { path: "./fonts/SundaySerif-Italic-Variable.woff2", weight: "400 600", style: "italic" },
  ],
  variable: "--font-sunday-serif-fx",
  display: "swap",
  preload: false,
  fallback: ["Georgia", "serif"],
  adjustFontFallback: "Times New Roman",
});

export const SundaySerifBlur = localFont({
  src: [
    { path: "./fonts/SundaySerifBlur-Regular.woff2", weight: "400", style: "normal" },
    { path: "./fonts/SundaySerifBlur-Italic.woff2", weight: "400", style: "italic" },
  ],
  variable: "--font-sunday-serif-blur",
  display: "swap",
  preload: false,
  fallback: ["Georgia", "serif"],
});

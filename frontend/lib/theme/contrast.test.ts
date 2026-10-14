import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// --warn-text is the AA-safe text colour for warn surfaces (S58); --warn alone fails 4.5:1 in light.
const css = readFileSync("styles/theme.css", "utf8"); // vitest runs from frontend/;

function block(selector: string): string {
  const start = css.indexOf(selector);
  return css.slice(start, css.indexOf("}", start));
}
const light = block(':root[data-theme="compendium-light"]');
const dark = block(':root[data-theme="compendium-dark"]');

const hex = (b: string, name: string): string => {
  const m = b.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`--${name} missing`);
  return m[1];
};
const lum = (h: string): number => {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a: string, b: string): number => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

describe("--warn-text contrast (WCAG AA 4.5:1)", () => {
  for (const [theme, b] of [["light", light], ["dark", dark]] as const) {
    for (const bg of ["warn-soft", "surface"]) {
      it(`${theme}: on --${bg}`, () => {
        expect(ratio(hex(b, "warn-text"), hex(b, bg))).toBeGreaterThanOrEqual(4.5);
      });
    }
  }
});

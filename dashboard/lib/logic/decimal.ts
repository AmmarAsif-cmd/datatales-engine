/**
 * Exact decimal arithmetic for number matching (mirrors Python's Decimal use in verify.py).
 * A value is `int / 10^scale`. Floats are never used for comparisons.
 */
export type Dec = { int: bigint; scale: number };

export function parseDec(text: string): Dec {
  const m = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(text.trim());
  if (!m || (m[2] === "" && (m[3] ?? "") === "")) throw new Error(`not a number: ${text}`);
  const [, sign, whole, frac = "", exp = "0"] = m;
  let digits = (whole || "0") + frac;
  let scale = frac.length - Number(exp);
  if (scale < 0) {
    digits += "0".repeat(-scale);
    scale = 0;
  }
  const int = BigInt(digits) * (sign === "-" ? -1n : 1n);
  return { int, scale };
}

export function decFromNumber(n: number): Dec {
  return parseDec(String(n));
}

export function decAbs(d: Dec): Dec {
  return { int: d.int < 0n ? -d.int : d.int, scale: d.scale };
}

const pow10 = (n: number): bigint => 10n ** BigInt(n);

/** |a - t| <= 5 x 10^-(decimals + 1): `t`, written with `decimals` places, is `a` rounded. */
export function roundsTo(a: Dec, t: Dec, decimals: number): boolean {
  const s = Math.max(a.scale, t.scale, decimals + 1);
  const A = a.int * pow10(s - a.scale);
  const T = t.int * pow10(s - t.scale);
  const diff = A > T ? A - T : T - A;
  return diff <= 5n * pow10(s - (decimals + 1));
}

/** Canonical text with trailing zeros removed ("7.0" -> "7"), used to de-duplicate. */
export function decKey(d: Dec): string {
  let { int, scale } = d;
  while (scale > 0 && int % 10n === 0n) {
    int /= 10n;
    scale -= 1;
  }
  return `${int}e-${scale}`;
}

export function decToString(d: Dec): string {
  const neg = d.int < 0n;
  const digits = (neg ? -d.int : d.int).toString().padStart(d.scale + 1, "0");
  const text = d.scale ? `${digits.slice(0, -d.scale)}.${digits.slice(-d.scale)}` : digits;
  return (neg ? "-" : "") + text;
}

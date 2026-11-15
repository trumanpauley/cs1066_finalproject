/** Seedable random number generator so simulations can be reproduced in tests. */

export interface Rng {
  /** Uniform in [0, 1). */
  next(): number;
  /** Standard normal sample (mean 0, SD 1). */
  normal(): number;
}

/** Mulberry32: small, fast, good enough for game simulation. */
export function createRng(seed: number = Date.now()): Rng {
  let a = seed >>> 0;
  let spare: number | null = null;

  const next = (): number => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const normal = (): number => {
    if (spare !== null) {
      const s = spare;
      spare = null;
      return s;
    }
    // Box–Muller; guard against log(0).
    const u = Math.max(next(), 1e-12);
    const v = next();
    const r = Math.sqrt(-2 * Math.log(u));
    spare = r * Math.sin(2 * Math.PI * v);
    return r * Math.cos(2 * Math.PI * v);
  };

  return { next, normal };
}

/** Pick a key from a probability table that sums to 1. */
export function sampleCategorical<K extends string>(
  probabilities: Record<K, number>,
  rng: Rng,
): K {
  const u = rng.next();
  let cumulative = 0;
  const keys = Object.keys(probabilities) as K[];
  for (const key of keys) {
    cumulative += probabilities[key];
    if (u < cumulative) return key;
  }
  return keys[keys.length - 1];
}

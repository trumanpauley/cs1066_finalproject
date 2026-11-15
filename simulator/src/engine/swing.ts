/** Step B — swing decision. */

import type { Count, HitterProfile, PitchExecution, PitcherProfile } from "./types";
import { signedZoneDistance } from "./zone";

const pct = (p: number) => `${Math.round(p * 100)}%`;

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** 0 well outside the zone → 1 well inside; ~0.5 on the edge. */
export function zoneWeight(signedDistance: number): number {
  return 1 / (1 + Math.exp(-signedDistance / 0.08));
}

export interface SwingModel {
  probability: number;
  factors: string[];
}

/**
 * P(swing) blends the hitter's chase and zone-swing rates by how deep the
 * pitch is in the zone, then applies pitch-type, platoon, and count
 * adjustments. Every factor that moves the number is reported.
 */
export function swingProbability(
  pitch: PitchExecution,
  count: Count,
  hitter: HitterProfile,
  pitcher: PitcherProfile,
): SwingModel {
  const factors: string[] = [];
  const d = signedZoneDistance(pitch.actual, hitter);
  const w = zoneWeight(d);
  const t = hitter.byPitchType[pitch.category];

  let chase = hitter.rates.chase * t.chaseMult;
  const zoneSwing = hitter.rates.zoneSwing * t.zoneSwingMult;

  // Platoon: breaking balls away from same-side hitters and changeups to
  // opposite-side hitters are the classic chase pitches.
  const sameSide = pitcher.hand === hitter.bats;
  if ((sameSide && pitch.category === "breaking") || (!sameSide && pitch.category === "offspeed")) {
    chase *= 1.1;
    factors.push(`${sameSide ? "Same" : "Opposite"}-side ${pitch.category} pitch: chase ×1.1`);
  }

  let p = chase + (zoneSwing - chase) * w;

  if (d < 0) {
    const off = -d;
    // Pitches far off the plate are rarely offered at.
    const decay = Math.exp(-Math.max(0, off - 0.25) / 0.45);
    p *= decay;
    factors.push(
      `${(off * 12).toFixed(0)} in. off the zone — base chase ${pct(hitter.rates.chase)}, ` +
        `${pitch.category} chase ×${t.chaseMult}`,
    );
  } else {
    factors.push(
      `In the zone — base zone swing ${pct(hitter.rates.zoneSwing)}, ` +
        `${pitch.category} ×${t.zoneSwingMult}`,
    );
  }

  const { balls, strikes } = count;
  let countMult = 1;
  let countNote = "";
  if (balls === 0 && strikes === 0) {
    countMult = hitter.counts.firstPitchSwingMult;
    countNote = "First pitch";
  } else if (balls === 3 && strikes === 0) {
    countMult = hitter.counts.threeBallsNoStrikesSwingMult;
    countNote = "3-0 count";
  } else if (strikes === 2) {
    countMult = hitter.counts.twoStrikeSwingMult;
    countNote = "Two strikes — protecting";
  } else if (balls > strikes) {
    countMult = hitter.counts.hitterAheadSwingMult;
    countNote = "Hitter's count";
  }
  if (countMult !== 1) {
    p *= countMult;
    factors.push(`${countNote}: swing ×${countMult}`);
  }

  const probability = clamp(p, 0.01, 0.97);
  factors.push(`Swing chance ${pct(probability)}`);
  return { probability, factors };
}

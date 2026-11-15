/** Step C — contact decision: miss, foul, or ball in play (given a swing). */

import { clamp, zoneWeight } from "./swing";
import type { ContactProbabilities, Count, HitterProfile, PitchExecution } from "./types";
import { signedZoneDistance } from "./zone";

/**
 * P(contact | swing) blends zone and out-of-zone contact rates by location,
 * then splits contact into foul vs. in play. The three outcomes always sum
 * to exactly 1.
 */
export function contactProbabilities(
  pitch: PitchExecution,
  count: Count,
  hitter: HitterProfile,
): ContactProbabilities {
  const d = signedZoneDistance(pitch.actual, hitter);
  const w = zoneWeight(d);
  const t = hitter.byPitchType[pitch.category];

  let contact =
    hitter.rates.outZoneContact + (hitter.rates.zoneContact - hitter.rates.outZoneContact) * w;
  contact *= t.contactMult;

  // Extra velocity is harder to square up.
  if (pitch.category === "fastball" && pitch.velocity > 93) {
    contact *= 1 - 0.012 * (pitch.velocity - 93);
  }
  // Way off the plate: even a committed swing rarely connects.
  if (d < -0.3) contact *= Math.exp(-(-d - 0.3) / 0.8);

  contact = clamp(contact, 0.2, 0.98);

  // Edge pitches and two-strike defensive swings produce more fouls.
  let foulShare = hitter.rates.foulShare + 0.12 * (1 - w) + (count.strikes === 2 ? 0.05 : 0);
  foulShare = clamp(foulShare, 0.2, 0.8);

  const miss = 1 - contact;
  const foul = contact * foulShare;
  return { miss, foul, inPlay: 1 - miss - foul };
}

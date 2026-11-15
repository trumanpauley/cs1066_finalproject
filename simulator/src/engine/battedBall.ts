/**
 * Step D — ball-in-play outcome.
 *
 * Samples exit velocity, launch angle, and spray angle from the hitter's
 * batted-ball profile (adjusted for pitch location and type), then turns
 * them into a *probability* of a hit and samples the result. A hard line
 * drive is likely — not guaranteed — to fall in.
 */

import type { Rng } from "./rng";
import { clamp, zoneWeight } from "./swing";
import type { BattedBall, HitterProfile, PitchExecution, PlateAppearanceResult } from "./types";
import { insideness, signedZoneDistance, ZONE_HALF_WIDTH } from "./zone";

const MPH_TO_FPS = 1.4667;

/** Rough carry model: vacuum range scaled down for drag. Feet. */
export function estimateDistance(exitVelo: number, launchAngle: number): number {
  if (launchAngle < 10) {
    // Grounders: how far they get before an infielder could reach them.
    return clamp(exitVelo * 1.3, 20, 160);
  }
  const v = exitVelo * MPH_TO_FPS;
  const theta = (clamp(launchAngle, 0, 89) * Math.PI) / 180;
  const vacuum = (v * v * Math.sin(2 * theta)) / 32.17;
  return clamp(vacuum * 0.62, 30, 480);
}

export function battedBallType(launchAngle: number): BattedBall["type"] {
  if (launchAngle < 10) return "ground_ball";
  if (launchAngle < 25) return "line_drive";
  if (launchAngle < 50) return "fly_ball";
  return "popup";
}

interface HitTable {
  homeRun: number;
  hit: number; // non-HR hit
}

/** Hit probabilities from batted-ball quality (each in [0,1], sum ≤ 1). */
export function hitProbabilities(
  exitVelo: number,
  launchAngle: number,
  distance: number,
): HitTable {
  switch (battedBallType(launchAngle)) {
    case "ground_ball":
      return { homeRun: 0, hit: clamp(0.2 + 0.007 * (exitVelo - 85), 0.08, 0.5) };
    case "line_drive":
      return { homeRun: 0, hit: clamp(0.6 + 0.012 * (exitVelo - 90), 0.35, 0.9) };
    case "fly_ball": {
      const homeRun = clamp((distance - 370) / 40, 0, 0.95);
      let hit = distance < 200 ? 0.25 : distance < 300 ? 0.06 : 0.18;
      hit = Math.min(hit, 1 - homeRun);
      return { homeRun, hit };
    }
    default:
      return { homeRun: 0, hit: 0.02 };
  }
}

export function simulateBattedBall(
  pitch: PitchExecution,
  hitter: HitterProfile,
  rng: Rng,
): BattedBall {
  const bb = hitter.battedBall;
  const t = hitter.byPitchType[pitch.category];
  const d = signedZoneDistance(pitch.actual, hitter);
  const w = zoneWeight(d);
  // "Heart" of the zone: well inside every edge.
  const heart = d > 0 ? zoneWeight(d - 0.25) : 0;

  const evMean = bb.exitVeloMean * t.damageMult - 6 * (1 - w) + 4 * heart - 1.5;
  const exitVelo = clamp(evMean + rng.normal() * bb.exitVeloSd, 40, 118);

  const zoneMid = (hitter.zone.top + hitter.zone.bottom) / 2;
  const launchAngle = clamp(
    bb.launchAngleMean + 9 * (pitch.actual.z - zoneMid) + rng.normal() * bb.launchAngleSd,
    -40,
    80,
  );

  // Pull side: left field (negative) for righties, right field for lefties.
  const pullSign = hitter.bats === "R" ? -1 : 1;
  const inside = clamp(insideness(pitch.actual.x, hitter.bats) / ZONE_HALF_WIDTH, -1.5, 1.5);
  let pull = bb.pullBias + 10 * inside;
  if (pitch.category === "offspeed") pull += 5; // out in front
  if (pitch.category === "fastball") pull -= 0.3 * (pitch.perceivedVelocity - 92); // late
  const sprayAngle = clamp(pullSign * pull + rng.normal() * bb.spraySd, -44, 44);

  const distance = estimateDistance(exitVelo, launchAngle);
  const type = battedBallType(launchAngle);
  const probs = hitProbabilities(exitVelo, launchAngle, distance);

  const u = rng.next();
  let result: PlateAppearanceResult;
  if (u < probs.homeRun) {
    result = "home_run";
  } else if (u < probs.homeRun + probs.hit) {
    result = hitType(type, exitVelo, sprayAngle, distance, rng);
  } else {
    result = (
      { ground_ball: "groundout", line_drive: "lineout", fly_ball: "flyout", popup: "popout" } as const
    )[type];
  }

  const finalDistance = result === "home_run" ? Math.max(distance, 375) : distance;
  const rad = (sprayAngle * Math.PI) / 180;
  return {
    exitVelo: Math.round(exitVelo * 10) / 10,
    launchAngle: Math.round(launchAngle),
    sprayAngle: Math.round(sprayAngle),
    distance: Math.round(finalDistance),
    landing: { x: finalDistance * Math.sin(rad), y: finalDistance * Math.cos(rad) },
    hitProbability: probs.homeRun + probs.hit,
    result,
    type,
  };
}

function hitType(
  type: BattedBall["type"],
  exitVelo: number,
  sprayAngle: number,
  distance: number,
  rng: Rng,
): PlateAppearanceResult {
  const u = rng.next();
  if (type === "ground_ball") {
    return exitVelo > 103 && Math.abs(sprayAngle) > 35 && u < 0.3 ? "double" : "single";
  }
  if (type === "line_drive") {
    const pDouble = clamp(0.25 + 0.01 * (exitVelo - 95), 0.1, 0.45);
    const pTriple = exitVelo > 100 && Math.abs(sprayAngle) > 15 ? 0.03 : 0;
    if (u < pTriple) return "triple";
    return u < pTriple + pDouble ? "double" : "single";
  }
  if (type === "fly_ball") {
    if (distance < 220) return "single"; // bloop
    if (u < 0.1) return "triple";
    return u < 0.7 ? "double" : "single";
  }
  return "single";
}

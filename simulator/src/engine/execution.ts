/** Step A — pitch execution: the target is where you aim, not where it goes. */

import type { Rng } from "./rng";
import type { HitterProfile, Location, PitchDefinition, PitchExecution } from "./types";
import { isInZone } from "./zone";

/** Extension (feet) at which perceived velocity equals radar velocity. */
export const REFERENCE_EXTENSION = 6.0;
const RUBBER_TO_PLATE = 60.5;

/**
 * Radar velocity scaled by how much closer to the plate the ball is
 * released than a reference 6.0 ft extension: same speed, less distance,
 * less reaction time.
 */
export function perceivedVelocity(velocity: number, extension: number): number {
  return (velocity * (RUBBER_TO_PLATE - REFERENCE_EXTENSION)) / (RUBBER_TO_PLATE - extension);
}

/**
 * Sample the actual location around the target using the pitch's command
 * (1-SD scatter per axis, feet) and the pitch's velocity spread.
 */
export function executePitch(
  pitch: PitchDefinition,
  target: Location,
  hitter: HitterProfile,
  rng: Rng,
  pitcherExtension = REFERENCE_EXTENSION,
): PitchExecution {
  const actual: Location = {
    x: target.x + rng.normal() * pitch.command.sdX,
    z: Math.max(0.15, target.z + rng.normal() * pitch.command.sdZ),
  };
  const velocity = Math.round((pitch.velocity + rng.normal() * pitch.velocitySd) * 10) / 10;
  const extension = pitch.release?.extension ?? pitcherExtension;
  return {
    code: pitch.code,
    name: pitch.name,
    category: pitch.category,
    velocity,
    perceivedVelocity: Math.round(perceivedVelocity(velocity, extension) * 10) / 10,
    extension,
    target,
    actual,
    inZone: isInZone(actual, hitter),
  };
}

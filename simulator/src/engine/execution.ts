/** Step A — pitch execution: the target is where you aim, not where it goes. */

import type { Rng } from "./rng";
import type { HitterProfile, Location, PitchDefinition, PitchExecution } from "./types";
import { isInZone } from "./zone";

/**
 * Sample the actual location around the target using the pitch's command
 * (1-SD scatter per axis, feet) and the pitch's velocity spread.
 */
export function executePitch(
  pitch: PitchDefinition,
  target: Location,
  hitter: HitterProfile,
  rng: Rng,
): PitchExecution {
  const actual: Location = {
    x: target.x + rng.normal() * pitch.command.sdX,
    z: Math.max(0.15, target.z + rng.normal() * pitch.command.sdZ),
  };
  const velocity = Math.round((pitch.velocity + rng.normal() * pitch.velocitySd) * 10) / 10;
  return {
    code: pitch.code,
    name: pitch.name,
    category: pitch.category,
    velocity,
    target,
    actual,
    inZone: isInZone(actual, hitter),
  };
}

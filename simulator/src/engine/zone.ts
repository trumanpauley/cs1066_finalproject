import type { BatSide, HitterProfile, Location } from "./types";

/** Half the plate width (17 in) plus the ball's radius, in feet. */
export const ZONE_HALF_WIDTH = 17 / 12 / 2 + 0.121;
export const BALL_RADIUS = 0.121;

export interface ZoneBounds {
  left: number;
  right: number;
  bottom: number;
  top: number;
}

export function zoneBounds(hitter: HitterProfile): ZoneBounds {
  return {
    left: -ZONE_HALF_WIDTH,
    right: ZONE_HALF_WIDTH,
    bottom: hitter.zone.bottom - BALL_RADIUS,
    top: hitter.zone.top + BALL_RADIUS,
  };
}

export function isInZone(loc: Location, hitter: HitterProfile): boolean {
  const z = zoneBounds(hitter);
  return loc.x >= z.left && loc.x <= z.right && loc.z >= z.bottom && loc.z <= z.top;
}

/**
 * Signed distance (feet) to the zone edge: positive inside the zone (distance
 * to the nearest edge), negative outside (distance to the zone rectangle).
 */
export function signedZoneDistance(loc: Location, hitter: HitterProfile): number {
  const z = zoneBounds(hitter);
  const dx = Math.max(z.left - loc.x, 0, loc.x - z.right);
  const dz = Math.max(z.bottom - loc.z, 0, loc.z - z.top);
  if (dx === 0 && dz === 0) {
    return Math.min(loc.x - z.left, z.right - loc.x, loc.z - z.bottom, z.top - loc.z);
  }
  return -Math.hypot(dx, dz);
}

/** + = toward the hitter's body ("inside"), - = away. */
export function insideness(x: number, bats: BatSide): number {
  // A right-handed hitter stands on the third-base side (negative x).
  return bats === "R" ? -x : x;
}

/** Approximate area the hitter's body occupies (catcher's-view coordinates). */
export function hitterBodyContains(loc: Location, hitter: HitterProfile): boolean {
  const inside = insideness(loc.x, hitter.bats);
  return inside >= 1.75 && inside <= 2.9 && loc.z >= 0.4 && loc.z <= 5.6;
}

/** Plain-language location from the hitter's point of view: "low and away". */
export function describeLocation(loc: Location, hitter: HitterProfile): string {
  const zb = zoneBounds(hitter);
  const third = (zb.top - zb.bottom) / 3;
  const inside = insideness(loc.x, hitter.bats);

  let vertical = "";
  if (loc.z < 0.9) vertical = "in the dirt";
  else if (loc.z < zb.bottom) vertical = "low";
  else if (loc.z < zb.bottom + third) vertical = "low";
  else if (loc.z > zb.top) vertical = "high";
  else if (loc.z > zb.top - third) vertical = "up";

  let horizontal = "";
  if (inside > ZONE_HALF_WIDTH + 0.6) horizontal = "way inside";
  else if (inside > ZONE_HALF_WIDTH) horizontal = "inside";
  else if (inside > ZONE_HALF_WIDTH / 3) horizontal = "in";
  else if (inside < -(ZONE_HALF_WIDTH + 0.6)) horizontal = "way outside";
  else if (inside < -ZONE_HALF_WIDTH) horizontal = "off the plate away";
  else if (inside < -ZONE_HALF_WIDTH / 3) horizontal = "away";

  if (vertical === "in the dirt") return horizontal ? `in the dirt, ${horizontal}` : "in the dirt";
  if (!vertical && !horizontal) return "middle-middle";
  if (!vertical) return horizontal === "in" || horizontal === "away" ? `middle ${horizontal}` : horizontal;
  if (!horizontal) return vertical === "high" ? "high" : `${vertical} over the plate`;
  return `${vertical} and ${horizontal}`;
}

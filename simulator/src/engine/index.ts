/**
 * PitchIQ simulation engine — pure TypeScript, no UI or data-loading code.
 *
 *   A  executePitch          target + command  → actual location, velocity
 *   B  swingProbability      location, count, hand, tendencies → P(swing)
 *   C  contactProbabilities  → P(miss), P(foul), P(in play)   (sum = 1)
 *   D  simulateBattedBall    → exit velo, launch, spray, distance → result
 *      throwPitch            runs A–D and updates the count
 */

export * from "./types";
export { createRng, sampleCategorical, type Rng } from "./rng";
export { executePitch } from "./execution";
export { swingProbability, zoneWeight } from "./swing";
export { contactProbabilities } from "./contact";
export { simulateBattedBall, estimateDistance, hitProbabilities, battedBallType } from "./battedBall";
export { applyCall, isAtBatOver, newAtBat, throwPitch, OUT_RESULTS, RESULT_LABELS } from "./atBat";
export {
  describeLocation,
  hitterBodyContains,
  insideness,
  isInZone,
  signedZoneDistance,
  zoneBounds,
  ZONE_HALF_WIDTH,
  BALL_RADIUS,
} from "./zone";

/**
 * Core data types for the PitchIQ pitch simulator.
 *
 * Coordinates follow the Statcast convention, seen from the catcher:
 *   x = horizontal plate location in feet (0 = middle of plate, + = first-base side)
 *   z = height above the ground in feet
 * The UI mirrors x to draw the pitcher's view.
 */

export type Hand = "R" | "L";
export type BatSide = "R" | "L";

/** Broad pitch families used to look up hitter tendencies. */
export type PitchCategory = "fastball" | "breaking" | "offspeed";

export interface Location {
  x: number;
  z: number;
}

// ---------------------------------------------------------------------------
// Pitcher
// ---------------------------------------------------------------------------

export interface PitchDefinition {
  code: string; // "FF", "SL", "CH", ...
  name: string; // "Four-Seam Fastball"
  category: PitchCategory;
  velocity: number; // average mph
  velocitySd: number; // pitch-to-pitch spread, mph
  /** Horizontal break in inches, pitcher's perspective: + = arm side. */
  horizontalBreak: number;
  /** Induced vertical break in inches (+ = "rise" vs. a spinless pitch). */
  inducedVerticalBreak: number;
  spinRate?: number; // rpm, when available
  usage: number; // 0..1 share of pitches
  /**
   * This pitch's own release (feet): height off the ground and extension
   * toward the plate. Falls back to the pitcher's release when absent.
   */
  release?: { z?: number; extension?: number };
  /** Location scatter around the target (1 SD, feet) on each axis. */
  command: { sdX: number; sdZ: number };
}

export interface PitcherProfile {
  id: string;
  name: string;
  hand: Hand;
  /** Release point (feet): x from the catcher's view, z height, extension toward plate. */
  release: { x: number; z: number; extension: number };
  pitches: PitchDefinition[];
  /** Where the data came from — always shown in the UI. */
  source: DataSource;
}

// ---------------------------------------------------------------------------
// Hitter
// ---------------------------------------------------------------------------

export interface DataSource {
  kind: "synthetic" | "profile" | "scouting_report" | "api";
  label: string; // e.g. "Synthetic demo profile — not real MLB data"
}

/** Rates are probabilities in [0, 1]. */
export interface PlateDisciplineRates {
  /** Swing rate on pitches in the strike zone. */
  zoneSwing: number;
  /** Swing rate on pitches outside the zone (chase rate). */
  chase: number;
  /** Contact rate on swings at pitches in the zone. */
  zoneContact: number;
  /** Contact rate on swings at pitches outside the zone. */
  outZoneContact: number;
  /** Share of contact that goes foul (rest is in play). */
  foulShare: number;
}

/** Multipliers applied to the base rates for one pitch family (1 = neutral). */
export interface PitchTypeTendency {
  zoneSwingMult: number;
  chaseMult: number;
  contactMult: number;
  /** Scales exit velocity on contact (1 = neutral). */
  damageMult: number;
}

/** Count adjustments: multipliers on swing rates (1 = neutral). */
export interface CountTendencies {
  firstPitchSwingMult: number; // 0-0
  hitterAheadSwingMult: number; // 2-0, 3-1, 2-1 ...
  threeBallsNoStrikesSwingMult: number; // 3-0
  twoStrikeSwingMult: number; // protecting the plate
}

export interface BattedBallProfile {
  exitVeloMean: number; // mph
  exitVeloSd: number;
  launchAngleMean: number; // degrees
  launchAngleSd: number;
  /** Mean spray angle toward the pull side, degrees (0 = straight away center). */
  pullBias: number;
  spraySd: number;
}

export interface HitterProfile {
  id: string;
  name: string;
  bats: BatSide;
  /** Personal strike zone (feet). */
  zone: { bottom: number; top: number };
  rates: PlateDisciplineRates;
  byPitchType: Record<PitchCategory, PitchTypeTendency>;
  counts: CountTendencies;
  battedBall: BattedBallProfile;
  source: DataSource;
  /** Short scouting blurb shown on the hitter card (no invented stats). */
  blurb?: string;
  number?: string;
  position?: string;
  team?: string;
}

// ---------------------------------------------------------------------------
// Simulation state + results
// ---------------------------------------------------------------------------

export interface Count {
  balls: number;
  strikes: number;
}

export type PitchCall =
  | "ball"
  | "called_strike"
  | "swinging_strike"
  | "foul"
  | "in_play"
  | "hit_by_pitch";

export type PlateAppearanceResult =
  | "strikeout"
  | "walk"
  | "hit_by_pitch"
  | "single"
  | "double"
  | "triple"
  | "home_run"
  | "groundout"
  | "lineout"
  | "flyout"
  | "popout";

export interface ContactProbabilities {
  miss: number;
  foul: number;
  inPlay: number;
}

export interface BattedBall {
  exitVelo: number; // mph
  launchAngle: number; // degrees
  /** Degrees from center field; negative = left field, positive = right field. */
  sprayAngle: number;
  distance: number; // feet, approximate
  /** Landing spot in feet: x toward right field, y toward center field. */
  landing: { x: number; y: number };
  hitProbability: number;
  result: PlateAppearanceResult;
  type: "ground_ball" | "line_drive" | "fly_ball" | "popup";
}

export interface PitchExecution {
  code: string;
  name: string;
  category: PitchCategory;
  velocity: number;
  /**
   * Velocity adjusted for extension: a release closer to the plate gives the
   * hitter less time, so the pitch "plays" faster (and vice versa).
   */
  perceivedVelocity: number;
  /** Extension used for this pitch (feet). */
  extension: number;
  target: Location;
  actual: Location;
  inZone: boolean;
}

export interface SwingDecision {
  probability: number;
  swung: boolean;
  /** Human-readable inputs that moved the probability. */
  factors: string[];
}

export interface PitchOutcome {
  pitch: PitchExecution;
  countBefore: Count;
  swing: SwingDecision;
  contact?: { probabilities: ContactProbabilities; result: keyof ContactProbabilities };
  battedBall?: BattedBall;
  call: PitchCall;
  countAfter: Count;
  /** Set when this pitch ended the plate appearance. */
  paResult?: PlateAppearanceResult;
  headline: string;
  description: string;
  explanation: string[];
}

export interface AtBatState {
  count: Count;
  outs: number;
  pitches: PitchOutcome[];
  result?: PlateAppearanceResult;
}

export interface PitchInput {
  pitchCode: string;
  target: Location;
}

import type { BattedBall, HitterProfile, Location, PitchCall } from "../engine";
import type { Frame } from "./animation";

export interface PitchTrail {
  n: number;
  color: string;
  real: { sx: number; sy: number }[];
  ghost: { sx: number; sy: number }[];
  /** Total spin-induced break, inches. */
  breakIn: number;
}

export interface PitchMarker {
  n: number;
  loc: Location;
  call: PitchCall;
}

/** What the scene needs to fire effects for the pitch being shown. */
export interface PitchFx {
  /** Unique per showing (a replay gets a new id so effects play again). */
  id: string;
  call: PitchCall;
  perceivedVelocity: number;
  actual: Location;
  battedBallType?: BattedBall["type"];
}

/** Everything the Phaser stage draws; React owns it, the scene reads it. */
export interface StageState {
  hitter: HitterProfile;
  target: Location | null;
  aiming: boolean;
  frame: Frame | null;
  markers: PitchMarker[];
  trails: PitchTrail[];
  /** Color of the pitch in flight (for the ghost ball). */
  flightColor?: string;
  fx: PitchFx | null;
  onAim: (loc: Location) => void;
}

export const CALL_COLORS: Record<PitchCall, string> = {
  ball: "#4ade80",
  called_strike: "#ff6b6b",
  swinging_strike: "#ff6b6b",
  foul: "#fbbf24",
  in_play: "#7aa2f7",
  hit_by_pitch: "#c084fc",
};

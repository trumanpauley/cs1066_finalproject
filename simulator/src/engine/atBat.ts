/**
 * Plate-appearance state machine: runs steps A–D for one pitch and updates
 * the count. Pure functions — the UI holds the state.
 */

import { contactProbabilities } from "./contact";
import { executePitch } from "./execution";
import { battedBallType, simulateBattedBall } from "./battedBall";
import { sampleCategorical, type Rng } from "./rng";
import { swingProbability } from "./swing";
import type {
  AtBatState,
  BattedBall,
  Count,
  HitterProfile,
  PitchCall,
  PitchInput,
  PitchOutcome,
  PitcherProfile,
  PlateAppearanceResult,
} from "./types";
import { describeLocation, hitterBodyContains } from "./zone";

const pct = (p: number) => `${Math.round(p * 100)}%`;

export const OUT_RESULTS: PlateAppearanceResult[] = [
  "strikeout", "groundout", "lineout", "flyout", "popout",
];

export const RESULT_LABELS: Record<PlateAppearanceResult, string> = {
  strikeout: "Strikeout",
  walk: "Walk",
  hit_by_pitch: "Hit by pitch",
  single: "Single",
  double: "Double",
  triple: "Triple",
  home_run: "Home run",
  groundout: "Groundout",
  lineout: "Lineout",
  flyout: "Flyout",
  popout: "Popout",
};

export function newAtBat(outs = 0): AtBatState {
  return { count: { balls: 0, strikes: 0 }, outs, pitches: [] };
}

export function isAtBatOver(state: AtBatState): boolean {
  return state.result !== undefined;
}

/** Count bookkeeping for one pitch call (fouls can't produce strike three). */
export function applyCall(
  count: Count,
  call: PitchCall,
): { count: Count; result?: PlateAppearanceResult } {
  const { balls, strikes } = count;
  switch (call) {
    case "ball":
      return balls + 1 >= 4
        ? { count: { balls: 4, strikes }, result: "walk" }
        : { count: { balls: balls + 1, strikes } };
    case "called_strike":
    case "swinging_strike":
      return strikes + 1 >= 3
        ? { count: { balls, strikes: 3 }, result: "strikeout" }
        : { count: { balls, strikes: strikes + 1 } };
    case "foul":
      return { count: { balls, strikes: Math.min(2, strikes + 1) } };
    case "hit_by_pitch":
      return { count, result: "hit_by_pitch" };
    case "in_play":
      return { count };
  }
}

/** Throw one pitch: execution → swing → contact → batted ball → count. */
export function throwPitch(
  state: AtBatState,
  input: PitchInput,
  pitcher: PitcherProfile,
  hitter: HitterProfile,
  rng: Rng,
): { state: AtBatState; outcome: PitchOutcome } {
  if (isAtBatOver(state)) throw new Error("The plate appearance is already over.");
  const def = pitcher.pitches.find((p) => p.code === input.pitchCode);
  if (!def) throw new Error(`Unknown pitch: ${input.pitchCode}`);

  const countBefore = state.count;

  // A: execution
  const pitch = executePitch(def, input.target, hitter, rng, pitcher.release.extension);

  // B: swing decision (a pitch at the hitter's body is never offered at)
  const hitsBatter = hitterBodyContains(pitch.actual, hitter);
  const swingModel = swingProbability(pitch, countBefore, hitter, pitcher);
  const swung = !hitsBatter && rng.next() < swingModel.probability;

  let call: PitchCall;
  let contact: PitchOutcome["contact"];
  let battedBall: BattedBall | undefined;
  const explanation = [...swingModel.factors];

  if (hitsBatter) {
    call = "hit_by_pitch";
  } else if (!swung) {
    call = pitch.inZone ? "called_strike" : "ball";
    explanation.push(`No swing (${pct(1 - swingModel.probability)} take chance)`);
  } else {
    // C: contact
    const probabilities = contactProbabilities(pitch, countBefore, hitter);
    const result = sampleCategorical(probabilities, rng);
    contact = { probabilities, result };
    explanation.push(
      `On a swing: whiff ${pct(probabilities.miss)} · foul ${pct(probabilities.foul)} · ` +
        `in play ${pct(probabilities.inPlay)}`,
    );
    if (result === "miss") call = "swinging_strike";
    else if (result === "foul") call = "foul";
    else {
      call = "in_play";
      // D: batted ball
      battedBall = simulateBattedBall(pitch, hitter, rng);
      explanation.push(
        `Exit velo ${battedBall.exitVelo} mph, launch ${battedBall.launchAngle}° ` +
          `(${battedBallType(battedBall.launchAngle).replace("_", " ")}), ~${battedBall.distance} ft ` +
          `— model hit chance ${pct(battedBall.hitProbability)}`,
      );
    }
  }

  const applied = applyCall(countBefore, call);
  const paResult = battedBall ? battedBall.result : applied.result;
  const countAfter = applied.count;

  const outcome: PitchOutcome = {
    pitch,
    countBefore,
    swing: { probability: swingModel.probability, swung, factors: swingModel.factors },
    contact,
    battedBall,
    call,
    countAfter,
    paResult,
    headline: headlineFor(call, paResult),
    description: `${pitch.name}, ${pitch.velocity.toFixed(0)} mph, ${describeLocation(pitch.actual, hitter)}`,
    explanation,
  };

  const outs = paResult && OUT_RESULTS.includes(paResult) ? state.outs + 1 : state.outs;
  return {
    state: { count: countAfter, outs, pitches: [...state.pitches, outcome], result: paResult },
    outcome,
  };
}

function headlineFor(call: PitchCall, result?: PlateAppearanceResult): string {
  if (result === "strikeout") return call === "called_strike" ? "Strikeout looking" : "Strikeout swinging";
  if (result) return RESULT_LABELS[result];
  return {
    ball: "Ball",
    called_strike: "Called strike",
    swinging_strike: "Swing and miss",
    foul: "Foul ball",
    in_play: "In play",
    hit_by_pitch: "Hit by pitch",
  }[call];
}

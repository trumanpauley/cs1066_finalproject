/**
 * Pitch animation timeline. Pure function of elapsed time so the scene can
 * render any frame (and so animations are easy to reason about).
 */

import type { PitchDefinition, PitchOutcome, PitcherProfile } from "../engine";
import { CAMERA_Z, project, VIEW_W } from "./projection";

const G = 32.17; // ft/s²
const MPH_TO_FPS = 1.4667;
export const SLOW_MO = 2.3; // stretch real flight time so the eye can follow it
const WINDUP_MS = 260;
const AFTER_MS = 900;
/** The flight is shown from this fraction on: the camera sits just behind
 *  the release point, so the first few feet would be off-screen. */
const VISIBLE_FROM = 0.1;

export interface PitchAnimation {
  outcome: PitchOutcome;
  pitcher: PitcherProfile;
  def: PitchDefinition;
  flightMs: number;
  totalMs: number;
  /** Fixed per-pitch jitter for after-contact paths (keeps renders stable). */
  jitter: number;
}

export interface Frame {
  ball: { sx: number; sy: number; r: number; opacity: number } | null;
  trail: { sx: number; sy: number }[];
  swing: number;
  flinch: number;
  mitt: { x: number; z: number; pop: number };
  arrived: boolean;
  done: boolean;
}

export function makeAnimation(
  outcome: PitchOutcome,
  pitcher: PitcherProfile,
  jitter: number,
): PitchAnimation {
  const def = pitcher.pitches.find((p) => p.code === outcome.pitch.code)!;
  const flightSec = (60.5 - pitcher.release.extension) / (outcome.pitch.velocity * MPH_TO_FPS);
  const flightMs = flightSec * 1000 * SLOW_MO;
  return { outcome, pitcher, def, flightMs, totalMs: WINDUP_MS + flightMs + AFTER_MS, jitter };
}

/** World position of the ball at flight fraction t (0 = release, 1 = plate). */
function ballWorld(anim: PitchAnimation, t: number) {
  const { pitcher, def, outcome } = anim;
  // Visual release near the camera's eye line, slightly to the arm side;
  // the physics (actual location) is unaffected.
  const rel = { x: pitcher.release.x * 0.35, z: CAMERA_Z + 0.15, extension: pitcher.release.extension };
  const releaseY = 60.5 - rel.extension;
  const T = (60.5 - pitcher.release.extension) / (outcome.pitch.velocity * MPH_TO_FPS);
  // Arm-side break is toward the pitcher's arm: -x (catcher's view) for a righty.
  const armSign = pitcher.hand === "R" ? -1 : 1;
  const breakX = (armSign * def.horizontalBreak) / 12;
  const breakZ = def.inducedVerticalBreak / 12 - 0.5 * G * T * T;
  const a = outcome.pitch.actual;
  const k = t * t - t; // 0 at both ends; bends the path, break shows late
  return {
    x: rel.x + (a.x - rel.x) * t + breakX * k,
    y: releaseY * (1 - t),
    z: rel.z + (a.z - rel.z) * t + breakZ * k,
  };
}

function ballScreen(anim: PitchAnimation, t: number) {
  const w = ballWorld(anim, t);
  const p = project(w.x, w.y, w.z);
  return { sx: p.sx, sy: p.sy, r: Math.min(15, Math.max(2.6, 0.121 * p.scale)) };
}

const easeOut = (t: number) => 1 - (1 - t) ** 3;

export function frameAt(anim: PitchAnimation, elapsed: number): Frame {
  const { outcome } = anim;
  const target = outcome.pitch.target;
  const actual = outcome.pitch.actual;
  const flightStart = WINDUP_MS;
  const arriveAt = flightStart + anim.flightMs;
  const after = elapsed - arriveAt;
  const arrived = after >= 0;

  const frame: Frame = {
    ball: null,
    trail: [],
    swing: 0,
    flinch: 0,
    mitt: { x: target.x, z: target.z, pop: 0 },
    arrived,
    done: elapsed >= anim.totalMs,
  };

  // Swing: bat starts ~170 ms before the ball arrives (slow-motion time).
  if (outcome.swing.swung) {
    frame.swing = Math.min(1, Math.max(0, (elapsed - (arriveAt - 170)) / 300));
  }
  if (outcome.call === "hit_by_pitch" && arrived) {
    frame.flinch = Math.min(1, after / 120) * Math.max(0, 1 - (after - 300) / 400);
  }

  // Taken or missed pitches: the catcher reaches to where the ball is going.
  const caught = ["ball", "called_strike", "swinging_strike"].includes(outcome.call);
  if (caught) {
    const reach = Math.min(1, Math.max(0, (elapsed - (arriveAt - 160)) / 160));
    frame.mitt = {
      x: target.x + (actual.x - target.x) * reach,
      z: target.z + (actual.z - target.z) * reach,
      pop: arrived ? Math.max(0, 1 - after / 220) : 0,
    };
  }

  if (elapsed < flightStart) {
    const s = ballScreen(anim, VISIBLE_FROM);
    const k = elapsed / flightStart;
    frame.ball = { ...s, opacity: k * 0.9 };
    return frame;
  }

  if (!arrived) {
    const t = VISIBLE_FROM + ((1 - VISIBLE_FROM) * (elapsed - flightStart)) / anim.flightMs;
    const s = ballScreen(anim, t);
    frame.ball = { ...s, opacity: 1 };
    for (const dt of [0.03, 0.06, 0.09]) {
      if (t - dt > VISIBLE_FROM) {
        const tr = ballScreen(anim, t - dt);
        frame.trail.push({ sx: tr.sx, sy: tr.sy });
      }
    }
    return frame;
  }

  // ---- after the ball reaches the plate --------------------------------
  const plate = ballScreen(anim, 1);
  const call = outcome.call;

  if (call === "in_play" && outcome.battedBall) {
    const bb = outcome.battedBall;
    const k = easeOut(Math.min(1, after / 750));
    // Left field is behind the pitcher's right: screen right.
    const endX = VIEW_W / 2 - Math.sin((bb.sprayAngle * Math.PI) / 180) * 620;
    const endY =
      bb.type === "ground_ball" ? 640 : bb.type === "line_drive" ? 120 : bb.type === "popup" ? -60 : -40;
    frame.ball = {
      sx: plate.sx + (endX - plate.sx) * k,
      sy: plate.sy + (endY - plate.sy) * k - (bb.type === "ground_ball" ? Math.sin(k * Math.PI * 3) * 14 * (1 - k) : 0),
      r: plate.r + (bb.type === "popup" ? 2 : 10) * k,
      opacity: 1 - Math.max(0, (k - 0.8) / 0.2),
    };
    return frame;
  }

  if (call === "foul") {
    const k = easeOut(Math.min(1, after / 600));
    const side = anim.jitter < 0.5 ? -1 : 1;
    frame.ball = {
      sx: plate.sx + side * (60 + anim.jitter * 140) * k,
      sy: plate.sy - 420 * k,
      r: plate.r * (1 - 0.5 * k),
      opacity: 1 - k * 0.7,
    };
    return frame;
  }

  if (call === "hit_by_pitch") {
    const k = Math.min(1, after / 500);
    frame.ball = {
      sx: plate.sx + (plate.sx > VIEW_W / 2 ? -1 : 1) * 70 * k,
      sy: plate.sy + 90 * k - Math.sin(k * Math.PI) * 40,
      r: plate.r,
      opacity: 1 - k * 0.6,
    };
    return frame;
  }

  // Caught: the ball disappears into the mitt.
  return frame;
}

/**
 * Batter rig: poses in 3D, drawn in 2D.
 *
 * Local coordinates are in feet, origin on the ground between the feet:
 *   u = toward the plate (screen-horizontal, mirrored for lefties)
 *   v = down (negative is up)
 *   w = toward the pitcher (toward the camera)
 * A slight oblique projection (u += 0.22·w) gives depth: the front foot
 * sits a little toward the plate, shoulders and hips visibly turn, and the
 * bat foreshortens as the barrel comes around toward the pitcher.
 *
 * A pose is a handful of joint targets (pelvis, grip, feet, bat direction,
 * hip/shoulder rotation). Knees and elbows are solved with two-bone IK so
 * limbs always connect and bend naturally.
 */

export type HitterMode = "idle" | "take" | "contact" | "miss" | "hbp";

/** What the hitter is doing on this frame (from the pitch timeline). */
export interface HitterMotion {
  /** 0 → 1 as the pitch is delivered: hands load, front foot strides. */
  load: number;
  /** 0 → 1 through the swing (contact happens at SWING_CONTACT). */
  swing: number;
  /** 0 → 1 after a take: stride lands, hands stay back, eyes track. */
  take: number;
  /** 0 → 1 → 0 bail out on a pitch at the hitter. */
  flinch: number;
  mode: HitterMode;
}

/** Fraction of the swing at which the barrel meets the ball. */
export const SWING_CONTACT = 0.4;

export interface V3 {
  u: number;
  v: number;
  w: number;
}

interface Pose {
  pelvis: V3;
  /** Spine lean toward the plate (radians). */
  lean: number;
  /** Hip and shoulder rotation: 0 = closed (side-on), 1 = square to the pitcher. */
  hipOpen: number;
  shOpen: number;
  /** Bottom hand on the bat. */
  grip: V3;
  /** Bat direction: yaw 0 = toward the plate, −π/2 = toward the catcher, +π/2 = toward the pitcher. */
  batYaw: number;
  /** Bat elevation above horizontal (radians). */
  batElev: number;
  front: V3;
  back: V3;
  /** Back-heel lift (radians) as the back foot pivots. */
  backHeel: number;
  headTilt: number;
}

export const BODY = {
  thigh: 1.5,
  shin: 1.42,
  ankle: 0.2,
  torso: 1.72,
  upperArm: 1.0,
  forearm: 0.95,
  hipHalf: 0.36,
  shoulderHalf: 0.6,
  neck: 0.2,
  bat: 2.8,
};

const P = (u: number, v: number, w: number): V3 => ({ u, v, w });

// --- Key poses ---------------------------------------------------------------

const STANCE: Pose = {
  pelvis: P(-0.05, -2.62, 0),
  lean: 0.2,
  hipOpen: 0.08,
  shOpen: 0.05,
  grip: P(-0.42, -4.5, -0.55),
  batYaw: -1.95,
  batElev: 1.0,
  front: P(0.18, 0, 1.15),
  back: P(-0.25, 0, -1.15),
  backHeel: 0,
  headTilt: 0,
};

const LOADED: Pose = {
  ...STANCE,
  pelvis: P(-0.22, -2.56, -0.12),
  lean: 0.13,
  hipOpen: -0.12,
  shOpen: -0.16,
  grip: P(-0.62, -4.42, -0.82),
  batYaw: -2.15,
  batElev: 1.12,
  front: P(0.24, 0, 1.6),
};

const SLOT: Pose = {
  ...LOADED,
  pelvis: P(0.0, -2.52, 0.05),
  lean: 0.2,
  hipOpen: 0.55,
  shOpen: 0.18,
  grip: P(-0.3, -4.0, -0.6),
  batYaw: -2.6,
  batElev: 0.45,
  backHeel: 0.25,
};

const CONTACT: Pose = {
  ...SLOT,
  pelvis: P(0.18, -2.58, 0.12),
  lean: 0.28,
  hipOpen: 0.92,
  shOpen: 0.7,
  grip: P(0.22, -3.5, -0.05),
  batYaw: -0.12,
  batElev: 0.04,
  back: P(-0.2, -0.04, -1.1),
  backHeel: 0.75,
  headTilt: 0.12,
};

const EXTEND: Pose = {
  ...CONTACT,
  pelvis: P(0.22, -2.6, 0.14),
  lean: 0.24,
  hipOpen: 1.0,
  shOpen: 1.0,
  grip: P(0.32, -3.8, 0.45),
  batYaw: 0.9,
  batElev: 0.25,
  headTilt: 0.08,
};

const FINISH: Pose = {
  ...EXTEND,
  pelvis: P(0.18, -2.66, 0.1),
  lean: 0.1,
  hipOpen: 1.05,
  shOpen: 1.28,
  grip: P(-0.18, -4.85, 0.25),
  batYaw: 3.35,
  batElev: 0.95,
  backHeel: 0.9,
  headTilt: 0,
};

// A whiff: same path, but the barrel is under the ball, he over-rotates
// and finishes lower and off balance.
const MISS_CONTACT: Pose = { ...CONTACT, grip: P(0.25, -3.35, -0.05), batElev: -0.08, headTilt: 0.2 };
const MISS_FINISH: Pose = {
  ...FINISH,
  pelvis: P(0.26, -2.5, 0.18),
  lean: 0.36,
  shOpen: 1.18,
  grip: P(0.05, -4.25, 0.45),
  batYaw: 2.9,
  batElev: 0.45,
  headTilt: 0.25,
};

// Taking a pitch: stride lands, hands stay loaded, weight stays back.
const TAKE: Pose = {
  ...LOADED,
  pelvis: P(-0.12, -2.6, -0.02),
  lean: 0.1,
  hipOpen: 0.05,
  shOpen: -0.05,
  grip: P(-0.55, -4.48, -0.7),
  batElev: 1.18,
};

// Bailing out on an inside pitch: turn away, drop the hands, duck.
const FLINCH: Pose = {
  ...STANCE,
  pelvis: P(-0.42, -2.42, -0.2),
  lean: -0.22,
  hipOpen: -0.3,
  shOpen: -0.45,
  grip: P(-0.75, -4.0, -0.9),
  batYaw: -2.4,
  batElev: 1.3,
  headTilt: -0.35,
};

// --- Interpolation -------------------------------------------------------------

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerp3 = (a: V3, b: V3, t: number): V3 => ({ u: lerp(a.u, b.u, t), v: lerp(a.v, b.v, t), w: lerp(a.w, b.w, t) });
const smooth = (t: number) => t * t * (3 - 2 * t);
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));

function mix(a: Pose, b: Pose, t: number): Pose {
  return {
    pelvis: lerp3(a.pelvis, b.pelvis, t),
    lean: lerp(a.lean, b.lean, t),
    hipOpen: lerp(a.hipOpen, b.hipOpen, t),
    shOpen: lerp(a.shOpen, b.shOpen, t),
    grip: lerp3(a.grip, b.grip, t),
    batYaw: lerp(a.batYaw, b.batYaw, t),
    batElev: lerp(a.batElev, b.batElev, t),
    front: lerp3(a.front, b.front, t),
    back: lerp3(a.back, b.back, t),
    backHeel: lerp(a.backHeel, b.backHeel, t),
    headTilt: lerp(a.headTilt, b.headTilt, t),
  };
}

/** Piecewise pose along keyframes [time, pose] with smoothstep easing. */
function track(keys: [number, Pose][], t: number): Pose {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, p1] = keys[i];
    const [t0, p0] = keys[i - 1];
    if (t <= t1) return mix(p0, p1, smooth((t - t0) / (t1 - t0)));
  }
  return keys[keys.length - 1][1];
}

function poseFor(m: HitterMotion, timeMs: number): Pose {
  // Load: hands go back, weight shifts back, front foot lifts and strides.
  const load = clamp01(m.load);
  let pose = mix(STANCE, LOADED, smooth(load));
  const lift = Math.sin(Math.min(1, load * 1.15) * Math.PI) * 0.32;
  pose = { ...pose, front: { ...pose.front, v: pose.front.v - lift } };

  if ((m.mode === "contact" || m.mode === "miss") && m.swing > 0) {
    const miss = m.mode === "miss";
    pose = track(
      [
        [0, LOADED],
        [0.18, SLOT],
        [SWING_CONTACT, miss ? MISS_CONTACT : CONTACT],
        [0.58, miss ? { ...EXTEND, batElev: 0.05, grip: P(0.36, -3.6, 0.45) } : EXTEND],
        [1, miss ? MISS_FINISH : FINISH],
      ],
      clamp01(m.swing),
    );
  } else if (m.mode === "take" && m.take > 0) {
    pose = mix(pose, TAKE, smooth(clamp01(m.take)));
  }

  if (m.flinch > 0) pose = mix(pose, FLINCH, smooth(clamp01(m.flinch)));

  // Idle life: breathing and a small bat waggle while waiting.
  const calm = (1 - load) * (m.swing > 0 ? 0 : 1);
  if (calm > 0) {
    const t = timeMs / 1000;
    pose = {
      ...pose,
      pelvis: { ...pose.pelvis, v: pose.pelvis.v + Math.sin(t * 1.6) * 0.015 * calm },
      grip: { ...pose.grip, v: pose.grip.v + Math.sin(t * 2.4) * 0.05 * calm, u: pose.grip.u + Math.sin(t * 1.2) * 0.03 * calm },
      batElev: pose.batElev + Math.sin(t * 2.4 + 0.8) * 0.08 * calm,
    };
  }
  return pose;
}

// --- Skeleton --------------------------------------------------------------------

export interface Pt {
  x: number;
  y: number;
}

/** Oblique projection to local 2D (x toward the plate, y down). */
export const project2 = (p: V3): Pt => ({ x: p.u + 0.22 * p.w, y: p.v + 0.05 * p.w });

const add = (a: V3, b: V3, k = 1): V3 => ({ u: a.u + b.u * k, v: a.v + b.v * k, w: a.w + b.w * k });

/** Rotation axis from the back side to the front side of the hips/shoulders. */
function sideAxis(open: number): V3 {
  const a = (open * Math.PI) / 2;
  return { u: -Math.sin(a), v: 0, w: Math.cos(a) };
}

/** Two-bone IK: the middle joint, bent toward `prefer`. */
function ik(a: Pt, b: Pt, l1: number, l2: number, prefer: Pt): Pt {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  let d = Math.hypot(dx, dy) || 1e-6;
  d = Math.min(d, (l1 + l2) * 0.999);
  const along = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, l1 * l1 - along * along));
  const ux = dx / (Math.hypot(dx, dy) || 1e-6);
  const uy = dy / (Math.hypot(dx, dy) || 1e-6);
  const mx = a.x + ux * along;
  const my = a.y + uy * along;
  let nx = -uy;
  let ny = ux;
  if (nx * prefer.x + ny * prefer.y < 0) {
    nx = -nx;
    ny = -ny;
  }
  return { x: mx + nx * h, y: my + ny * h };
}

export interface HitterSkeleton {
  pelvis: Pt;
  neck: Pt;
  head: Pt;
  headTilt: number;
  hips: { front: Pt; back: Pt };
  shoulders: { front: Pt; back: Pt; frontW: number; backW: number };
  knees: { front: Pt; back: Pt };
  ankles: { front: Pt; back: Pt };
  feet: { front: Pt; back: Pt; backHeel: number };
  elbows: { front: Pt; back: Pt };
  hands: { bottom: Pt; top: Pt };
  bat: { knob: Pt; tip: Pt; towardCatcher: number };
  /** Torso/hip widths as drawn (feet), showing how far they've rotated. */
  shoulderSpan: number;
  hipSpan: number;
}

/** Full skeleton (local 2D, feet) for a motion state at time `timeMs`. */
export function hitterSkeleton(m: HitterMotion, timeMs: number): HitterSkeleton {
  const p = poseFor(m, timeMs);

  const hipAxis = sideAxis(p.hipOpen);
  const shAxis = sideAxis(p.shOpen);
  const hipF = add(p.pelvis, hipAxis, BODY.hipHalf);
  const hipB = add(p.pelvis, hipAxis, -BODY.hipHalf);
  const top = add(p.pelvis, { u: Math.sin(p.lean), v: -Math.cos(p.lean), w: 0 }, BODY.torso);
  const shF = add(top, shAxis, BODY.shoulderHalf);
  const shB = add(top, shAxis, -BODY.shoulderHalf);
  const head = add(top, { u: Math.sin(p.lean + p.headTilt) * 0.55, v: -0.55, w: 0.05 }, 1);

  const ce = Math.cos(p.batElev);
  const dir: V3 = { u: ce * Math.cos(p.batYaw), v: -Math.sin(p.batElev), w: ce * Math.sin(p.batYaw) };
  const bottom = p.grip;
  const topHand = add(bottom, dir, 0.3);
  const knob = add(bottom, dir, -0.14);
  const tip = add(knob, dir, BODY.bat);

  const ankleF = add(p.front, { u: 0, v: -BODY.ankle, w: 0 });
  const ankleB = add(p.back, { u: 0, v: -BODY.ankle, w: 0 });
  const proj = project2;
  const toPlate = { x: 1, y: 0.15 };
  const down = { x: 0, y: 1 };

  const hips = { front: proj(hipF), back: proj(hipB) };
  const ankles = { front: proj(ankleF), back: proj(ankleB) };
  const shoulders = { front: proj(shF), back: proj(shB), frontW: shF.w, backW: shB.w };
  const hands = { bottom: proj(bottom), top: proj(topHand) };

  return {
    pelvis: proj(p.pelvis),
    neck: proj(top),
    head: proj(head),
    headTilt: p.headTilt,
    hips,
    shoulders,
    knees: {
      front: ik(hips.front, ankles.front, BODY.thigh, BODY.shin, toPlate),
      // Back knee bows out (away from the plate) for a wide, stable base.
      back: ik(hips.back, ankles.back, BODY.thigh, BODY.shin, { x: -1, y: 0.1 }),
    },
    ankles,
    feet: { front: proj(p.front), back: proj(p.back), backHeel: p.backHeel },
    elbows: {
      front: ik(shoulders.front, hands.bottom, BODY.upperArm, BODY.forearm, down),
      back: ik(shoulders.back, hands.top, BODY.upperArm, BODY.forearm, { x: -0.4, y: 1 }),
    },
    hands,
    bat: { knob: proj(knob), tip: proj(tip), towardCatcher: -dir.w },
    shoulderSpan: Math.abs(shoulders.front.x - shoulders.back.x),
    hipSpan: Math.abs(hips.front.x - hips.back.x),
  };
}

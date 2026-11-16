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

// Proportions of a ~6'1" position player (feet).
export const BODY = {
  thigh: 1.45,
  shin: 1.38,
  ankle: 0.2,
  torso: 1.8,
  upperArm: 1.05,
  forearm: 0.95,
  hipHalf: 0.38,
  shoulderHalf: 0.62,
  neck: 0.2,
  bat: 2.8,
};

const P = (u: number, v: number, w: number): V3 => ({ u, v, w });

// --- Key poses ---------------------------------------------------------------
// Reference: a relaxed, balanced pro stance. Feet a bit wider than the
// shoulders along the line to the pitcher, knees softly flexed, hips and
// shoulders slightly open (three-quarter view from the mound), a small
// forward tilt at the hips, hands just above and behind the back shoulder,
// bat tipped back about 45°.

const STANCE: Pose = {
  // Weight a touch on the back leg, hips over the back half of the base.
  pelvis: P(-0.1, -2.9, -0.06),
  lean: 0.17,
  // Hips stay closed until the swing fires (opening them further would
  // swap the hips on screen and cross the legs); the shoulders carry the
  // three-quarter look.
  hipOpen: 0.08,
  shOpen: 0.24,
  // Hands a forearm's length off the back shoulder, just above it.
  grip: P(-0.66, -4.74, -0.5),
  // Bat ~45° back behind the head and back shoulder.
  batYaw: -2.82,
  batElev: 0.74,
  front: P(0.1, 0, 1.05),
  back: P(-0.24, 0, -1.08),
  backHeel: 0,
  headTilt: 0.04,
};

// Load: weight eases onto the back leg, hands drift back, hips coil a
// little, and the front foot takes a short stride (toe tap).
const LOADED: Pose = {
  ...STANCE,
  // Sits into the back hip: more knee flex, weight over the back leg.
  pelvis: P(-0.24, -2.76, -0.18),
  lean: 0.14,
  hipOpen: 0.0,
  shOpen: 0.08,
  grip: P(-0.78, -4.72, -0.7),
  batYaw: -2.9,
  batElev: 0.82,
  front: P(0.16, 0, 1.36),
};

const SLOT: Pose = {
  ...LOADED,
  pelvis: P(0.0, -2.78, 0.04),
  lean: 0.16,
  hipOpen: 0.6,
  shOpen: 0.22,
  grip: P(-0.3, -4.3, -0.62),
  batYaw: -2.6,
  batElev: 0.42,
  backHeel: 0.25,
};

const CONTACT: Pose = {
  ...SLOT,
  pelvis: P(0.14, -2.8, 0.1),
  lean: 0.22,
  hipOpen: 0.95,
  shOpen: 0.72,
  grip: P(0.2, -3.75, -0.05),
  batYaw: -0.12,
  batElev: 0.04,
  back: P(-0.08, -0.04, -0.92),
  backHeel: 0.75,
  headTilt: 0.14,
};

const EXTEND: Pose = {
  ...CONTACT,
  pelvis: P(0.18, -2.82, 0.12),
  lean: 0.2,
  hipOpen: 1.02,
  shOpen: 1.0,
  grip: P(0.3, -4.0, 0.45),
  batYaw: 0.9,
  batElev: 0.25,
  headTilt: 0.1,
};

const FINISH: Pose = {
  ...EXTEND,
  pelvis: P(0.14, -2.86, 0.1),
  lean: 0.08,
  hipOpen: 1.05,
  shOpen: 1.28,
  grip: P(-0.16, -5.0, 0.25),
  batYaw: 3.35,
  batElev: 0.95,
  backHeel: 0.9,
  headTilt: 0.02,
};

// A whiff: same path, but the barrel is under the ball, he over-rotates
// and finishes lower and off balance.
const MISS_CONTACT: Pose = { ...CONTACT, grip: P(0.24, -3.6, -0.05), batElev: -0.08, headTilt: 0.22 };
const MISS_FINISH: Pose = {
  ...FINISH,
  pelvis: P(0.22, -2.74, 0.16),
  lean: 0.3,
  shOpen: 1.18,
  grip: P(0.05, -4.45, 0.45),
  batYaw: 2.9,
  batElev: 0.45,
  headTilt: 0.25,
};

// Taking a pitch: stride lands, hands stay back, weight stays centered.
const TAKE: Pose = {
  ...LOADED,
  pelvis: P(-0.12, -2.8, -0.06),
  lean: 0.13,
  hipOpen: 0.06,
  shOpen: 0.16,
  grip: P(-0.72, -4.76, -0.62),
  batElev: 0.84,
};

// Bailing out on an inside pitch: turn away, drop the hands, duck.
const FLINCH: Pose = {
  ...STANCE,
  pelvis: P(-0.36, -2.66, -0.2),
  lean: -0.22,
  hipOpen: -0.2,
  shOpen: -0.4,
  grip: P(-0.7, -4.2, -0.9),
  batYaw: -2.4,
  batElev: 1.25,
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
  const lift = Math.sin(Math.min(1, load * 1.15) * Math.PI) * 0.2;
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

  // Idle life while waiting on the pitch. The feet never move; everything
  // above them does, on a few unrelated rhythms so it never looks looped:
  //   - weight sways slowly between the legs (knees flex and extend with it)
  //   - breathing lifts the chest and shoulders slightly
  //   - the hands draw small circles, so the bat "rides" rather than jitters
  //   - the bat tips back and forth a little around its 45° rest angle
  const calm = (1 - load) * (m.swing > 0 ? 0 : 1);
  if (calm > 0) {
    const t = timeMs / 1000;
    const sway = Math.sin(t * 0.9);
    const breath = Math.sin(t * 1.7);
    const circle = t * 2.1;
    pose = {
      ...pose,
      pelvis: {
        ...pose.pelvis,
        u: pose.pelvis.u + sway * 0.035 * calm,
        v: pose.pelvis.v + (0.02 * Math.abs(sway) - 0.01 + breath * 0.008) * calm,
      },
      lean: pose.lean + breath * 0.012 * calm,
      shOpen: pose.shOpen + Math.sin(t * 0.9 + 0.6) * 0.03 * calm,
      grip: {
        ...pose.grip,
        u: pose.grip.u + Math.cos(circle) * 0.035 * calm + sway * 0.02 * calm,
        v: pose.grip.v + Math.sin(circle) * 0.035 * calm - breath * 0.01 * calm,
        w: pose.grip.w,
      },
      batElev: pose.batElev + Math.sin(circle + 0.9) * 0.06 * calm,
      batYaw: pose.batYaw + Math.sin(t * 0.7) * 0.05 * calm,
      headTilt: pose.headTilt + Math.sin(t * 0.5) * 0.015 * calm,
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
  // Natural tilt: front shoulder a little lower than the back one.
  const shF = add(add(top, shAxis, BODY.shoulderHalf), { u: 0, v: 0.07, w: 0 });
  const shB = add(add(top, shAxis, -BODY.shoulderHalf), { u: 0, v: -0.05, w: 0 });
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
      // Back knee sets slightly in, toward the plate (no bow-legged look).
      back: ik(hips.back, ankles.back, BODY.thigh, BODY.shin, toPlate),
    },
    ankles,
    feet: { front: proj(p.front), back: proj(p.back), backHeel: p.backHeel },
    elbows: {
      // Front elbow hangs down and a little toward the plate; back elbow
      // down and back (relaxed, not chicken-winged or tucked).
      front: ik(shoulders.front, hands.bottom, BODY.upperArm, BODY.forearm, { x: 0.35, y: 1 }),
      back: ik(shoulders.back, hands.top, BODY.upperArm, BODY.forearm, { x: -0.6, y: 1 }),
    },
    hands,
    bat: { knob: proj(knob), tip: proj(tip), towardCatcher: -dir.w },
    shoulderSpan: Math.abs(shoulders.front.x - shoulders.back.x),
    hipSpan: Math.abs(hips.front.x - hips.back.x),
  };
}

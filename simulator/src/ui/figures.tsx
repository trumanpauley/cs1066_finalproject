/**
 * Vector art for the pitcher's-view scene. Figures are drawn in local feet
 * (x toward the plate, y down, origin at the feet) and turned into Phaser
 * textures by `textures.ts`; the hitter's arms and bat are drawn live by the
 * Phaser scene from `hitterRig()` so the swing is smooth at any frame.
 */

import type { BatSide } from "../engine";
import { project } from "./projection";

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

/** Where the hitter stands on screen and which way "toward the plate" is. */
export function hitterPlacement(bats: BatSide) {
  // A right-handed hitter stands on the third-base side (x < 0), which is
  // the pitcher's right — screen right — so "toward the plate" is screen-left.
  const p = project(bats === "R" ? -2.55 : 2.55, -0.4, 0);
  return { sx: p.sx, sy: p.sy, scale: p.scale, dir: bats === "R" ? -1 : 1 };
}

/** Local-feet frame that the hitter textures cover (x, y, width, height). */
export const HITTER_FRAME = { x: -2.6, y: -5.45, w: 4.6, h: 5.75 };

/** Shadow, legs, shoes, torso, belt — everything behind the arms. */
export function HitterBody() {
  return (
    <g>
      <ellipse cx={0} cy={0.02} rx={1.6} ry={0.18} fill="#000" opacity={0.28} />
      <path d="M0.78,0 L0.72,-1.45 L0.3,-2.7" stroke="#cfd5df" strokeWidth={0.42} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M-0.75,0 L-0.6,-1.4 L-0.25,-2.7" stroke="#b9c0cc" strokeWidth={0.42} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <ellipse cx={0.86} cy={-0.06} rx={0.3} ry={0.12} fill="#1a1f29" />
      <ellipse cx={-0.82} cy={-0.06} rx={0.3} ry={0.12} fill="#1a1f29" />
      <path d="M-0.45,-2.6 C-0.52,-3.35 -0.42,-4.0 -0.2,-4.45 L0.6,-4.45 C0.7,-4.0 0.62,-3.35 0.45,-2.6 Z" fill="#dfe4ec" />
      <rect x={-0.47} y={-2.8} width={0.94} height={0.16} rx={0.05} fill="#e05d5d" />
    </g>
  );
}

/** Head and helmet (face turned toward the pitcher) — drawn over the bat. */
export function HitterHead() {
  return (
    <g>
      <circle cx={0.25} cy={-4.88} r={0.33} fill="#c99a78" />
      <path d="M-0.14,-4.86 A0.41,0.41 0 0 1 0.68,-4.98 L0.84,-4.92 L0.62,-4.84 Z" fill="#e05d5d" />
      <path d="M-0.13,-4.88 L-0.13,-4.66 Q0.04,-4.6 0.09,-4.76 Z" fill="#c24b4b" />
    </g>
  );
}

export interface Pt {
  x: number;
  y: number;
}

/**
 * Arms and bat in local feet for a swing value (0 = stance, 1 = follow
 * through). Hands travel from behind the back shoulder down through the
 * zone while the barrel sweeps 142° across the plate.
 */
export function hitterRig(swing: number) {
  const s = ease(Math.min(1, Math.max(0, swing)));
  const hands = { x: -0.55 + 1.0 * s, y: -4.55 + 1.15 * s };
  const angle = (142 * s * Math.PI) / 180;
  const rot = (p: Pt): Pt => ({
    x: hands.x + p.x * Math.cos(angle) - p.y * Math.sin(angle),
    y: hands.y + p.x * Math.sin(angle) + p.y * Math.cos(angle),
  });
  return {
    hands,
    // [shoulder, control point, hands] quadratic curves
    frontArm: [{ x: 0.5, y: -4.3 }, { x: hands.x + 0.55, y: hands.y + 0.5 }, hands] as Pt[],
    backArm: [{ x: -0.2, y: -4.3 }, { x: hands.x - 0.05, y: hands.y + 0.45 }, hands] as Pt[],
    handle: [rot({ x: 0, y: 0 }), rot({ x: -1.55, y: -1.95 })],
    barrel: [rot({ x: -0.75, y: -0.95 }), rot({ x: -1.65, y: -2.08 })],
  };
}

/** Catcher in the crouch behind the plate. The mitt is drawn separately. */
export function CatcherFigure() {
  const p = project(0, -2.9, 0);
  return (
    <g transform={`translate(${p.sx},${p.sy}) scale(${p.scale})`}>
      <ellipse cx={0} cy={0.02} rx={1.4} ry={0.16} fill="#000" opacity={0.3} />
      <path d="M-0.35,-1.35 L-0.95,-1.15 L-0.75,0" stroke="#3b4660" strokeWidth={0.36} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M0.35,-1.35 L0.95,-1.15 L0.75,0" stroke="#3b4660" strokeWidth={0.36} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M-0.62,-1.25 L-0.68,-2.75 Q0,-3.05 0.68,-2.75 L0.62,-1.25 Q0,-1.05 -0.62,-1.25 Z" fill="#2b3445" />
      <path d="M-0.45,-1.5 L-0.48,-2.6 M0,-1.35 L0,-2.75 M0.45,-1.5 L0.48,-2.6" stroke="#3b4660" strokeWidth={0.05} />
      <path d="M0.6,-2.6 Q0.95,-2.1 0.7,-1.65" stroke="#2b3445" strokeWidth={0.22} fill="none" strokeLinecap="round" />
      <circle cx={0} cy={-3.32} r={0.36} fill="#222a38" />
      <path d="M-0.26,-3.45 L0.26,-3.45 M-0.28,-3.3 L0.28,-3.3 M-0.24,-3.15 L0.24,-3.15 M0,-3.6 L0,-3.0" stroke="#5b6680" strokeWidth={0.035} />
    </g>
  );
}

/** Umpire behind the catcher, mostly hidden. */
export function UmpireFigure() {
  const p = project(0.25, -5.2, 0);
  return (
    <g transform={`translate(${p.sx},${p.sy}) scale(${p.scale})`} opacity={0.9}>
      <path d="M-0.8,-1.6 L-0.85,-3.5 Q0,-3.85 0.85,-3.5 L0.8,-1.6 Z" fill="#161b26" />
      <circle cx={0} cy={-4.05} r={0.36} fill="#161b26" />
      <path d="M-0.24,-4.15 L0.24,-4.15 M-0.24,-3.98 L0.24,-3.98" stroke="#3a4255" strokeWidth={0.035} />
    </g>
  );
}

/** Catcher's mitt, unit radius 1 centered at the origin. */
export function MittShape() {
  return (
    <g>
      <ellipse rx={1} ry={0.92} fill="#7a4a2a" />
      <ellipse rx={0.62} ry={0.56} fill="#5c3720" />
      <path d="M-0.9,-0.2 Q0,-1.25 0.9,-0.2" stroke="#9a6640" strokeWidth={0.12} fill="none" />
    </g>
  );
}

/** Mitt radius in screen px at a location (catcher sets up 1.6 ft behind the plate). */
export function mittScreen(x: number, z: number, pop: number) {
  const p = project(x, -1.6, z);
  return { sx: p.sx, sy: p.sy, r: 0.42 * p.scale * (1 + 0.12 * pop) };
}

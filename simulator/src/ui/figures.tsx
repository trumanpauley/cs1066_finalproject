/**
 * Vector art for the pitcher's-view scene (catcher, umpire, mitt), drawn in
 * local feet and turned into Phaser textures by `textures.ts`. The batter is
 * a posed, layered rig: see `hitterRig.ts` and `hitterArt.ts`.
 */

import type { BatSide } from "../engine";
import { project } from "./projection";

/** Where the hitter stands on screen and which way "toward the plate" is. */
export function hitterPlacement(bats: BatSide) {
  // A right-handed hitter stands on the third-base side (x < 0), which is
  // the pitcher's right — screen right — so "toward the plate" is screen-left.
  const p = project(bats === "R" ? -2.55 : 2.55, -0.4, 0);
  return { sx: p.sx, sy: p.sy, scale: p.scale, dir: bats === "R" ? -1 : 1 };
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

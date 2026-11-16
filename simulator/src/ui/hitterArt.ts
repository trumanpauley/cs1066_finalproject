/**
 * Layered SVG body parts for the batter. Each part is authored in feet with
 * its joint at a known point, rendered to a texture, and posed every frame
 * by the Phaser scene from `hitterRig`. Limbs are drawn lying along +x from
 * their joint so they can be rotated and stretched (foreshortened) freely.
 */

import { createElement as h, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { BODY } from "./hitterRig";
import { TEXTURE_RES } from "./textureRes";

/** Texture pixels per foot for hitter parts. */
export const PART_PX = 80 * TEXTURE_RES;

const C = {
  jersey: "#e9ecf1",
  jerseyShade: "#c7ccd6",
  pants: "#e3e6ec",
  pantsShade: "#bfc5d0",
  navy: "#1d2740",
  navyHi: "#34436a",
  red: "#c8414b",
  skin: "#c99a78",
  skinShade: "#a87b5c",
  glove: "#f3f4f6",
  cleat: "#14171d",
  maple: "#d9b37a",
  mapleDark: "#b88d55",
};

export interface PartTexture {
  key: string;
  svg: string;
  width: number;
  height: number;
  /** Texture origin (0..1) = the joint the part rotates around. */
  originX: number;
  originY: number;
  /** Length along +x (feet) that maps to the bone, for limb parts. */
  boneLength?: number;
}

function part(
  key: string,
  box: { x: number; y: number; w: number; h: number },
  content: ReactElement[],
  defs: ReactElement[] = [],
  boneLength?: number,
): PartTexture {
  const width = Math.round(box.w * PART_PX);
  const height = Math.round(box.h * PART_PX);
  const svg = renderToStaticMarkup(
    h("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox: `${box.x} ${box.y} ${box.w} ${box.h}`, width, height },
      h("defs", null, ...defs), ...content),
  );
  return { key, svg, width, height, originX: -box.x / box.w, originY: -box.y / box.h, boneLength };
}

/** Vertical shading across a limb's thickness (light on top). */
const limbShade = (id: string, light: string, dark: string) =>
  h("linearGradient", { id, key: id, x1: 0, y1: 0, x2: 0, y2: 1 },
    h("stop", { offset: 0, stopColor: light }),
    h("stop", { offset: 0.55, stopColor: light }),
    h("stop", { offset: 1, stopColor: dark }));

/** Tapered capsule along +x from 0 to len, half-thickness r0 → r1. */
function capsule(len: number, r0: number, r1: number) {
  return `M0,${-r0} L${len},${-r1} A${r1},${r1} 0 0 1 ${len},${r1} L0,${r0} A${r0},${r0} 0 0 1 0,${-r0} Z`;
}

function thigh(): PartTexture {
  const len = BODY.thigh;
  return part("h-thigh", { x: -0.28, y: -0.28, w: len + 0.5, h: 0.56 }, [
    h("path", { key: "p", d: capsule(len, 0.27, 0.2), fill: "url(#pantsT)", stroke: C.pantsShade, strokeWidth: 0.015 }),
    h("path", { key: "s", d: `M0,-0.1 L${len},-0.07`, stroke: C.navy, strokeWidth: 0.045 }),
  ], [limbShade("pantsT", C.pants, C.pantsShade)], len);
}

function shin(): PartTexture {
  const len = BODY.shin + BODY.ankle * 0.4;
  const sockFrom = len * 0.5;
  return part("h-shin", { x: -0.22, y: -0.24, w: len + 0.4, h: 0.48 }, [
    // Navy sock with a red stripe, then the pant leg over the top half.
    h("path", { key: "sock", d: capsule(len, 0.17, 0.13), fill: "url(#sockT)" }),
    h("rect", { key: "st", x: sockFrom + 0.12, y: -0.16, width: 0.06, height: 0.32, fill: C.red }),
    h("path", { key: "pant", d: `M-0.02,-0.22 L${sockFrom},-0.2 L${sockFrom + 0.05},0.2 L-0.02,0.22 A0.22,0.22 0 0 1 -0.02,-0.22 Z`, fill: "url(#pantsS)", stroke: C.pantsShade, strokeWidth: 0.015 }),
    h("path", { key: "s", d: `M0,-0.08 L${sockFrom},-0.07`, stroke: C.navy, strokeWidth: 0.045 }),
  ], [limbShade("pantsS", C.pants, C.pantsShade), limbShade("sockT", C.navyHi, C.navy)], BODY.shin);
}

function upperArm(): PartTexture {
  const len = BODY.upperArm;
  return part("h-upper", { x: -0.2, y: -0.2, w: len + 0.38, h: 0.4 }, [
    h("path", { key: "u", d: capsule(len, 0.17, 0.14), fill: "url(#under)" }),
    // Short jersey sleeve with piping.
    h("path", { key: "sl", d: `M-0.03,-0.2 L0.46,-0.18 L0.46,0.18 L-0.03,0.2 A0.2,0.2 0 0 1 -0.03,-0.2 Z`, fill: "url(#sleeve)" }),
    h("rect", { key: "pp", x: 0.4, y: -0.18, width: 0.05, height: 0.36, fill: C.navy }),
  ], [limbShade("under", C.navyHi, C.navy), limbShade("sleeve", C.jersey, C.jerseyShade)], len);
}

function forearm(): PartTexture {
  const len = BODY.forearm;
  return part("h-fore", { x: -0.16, y: -0.16, w: len + 0.3, h: 0.32 }, [
    h("path", { key: "f", d: capsule(len, 0.14, 0.11), fill: "url(#underF)" }),
    h("rect", { key: "wb", x: len - 0.16, y: -0.12, width: 0.12, height: 0.24, rx: 0.03, fill: "#f4f5f7" }),
  ], [limbShade("underF", C.navyHi, C.navy)], len);
}

function glove(): PartTexture {
  return part("h-glove", { x: -0.2, y: -0.2, w: 0.4, h: 0.4 }, [
    h("ellipse", { key: "g", cx: 0, cy: 0, rx: 0.15, ry: 0.13, fill: C.glove, stroke: "#c9ced8", strokeWidth: 0.015 }),
    h("path", { key: "k", d: "M-0.1,-0.06 Q0,-0.12 0.1,-0.06", stroke: "#c9ced8", strokeWidth: 0.02, fill: "none" }),
    h("rect", { key: "s", x: -0.15, y: 0.02, width: 0.3, height: 0.06, rx: 0.02, fill: C.navy }),
  ]);
}

function cleat(): PartTexture {
  // Origin at the ankle point above the heel; toe points toward the plate.
  return part("h-cleat", { x: -0.2, y: -0.3, w: 0.9, h: 0.34 }, [
    h("path", { key: "c", d: "M-0.14,-0.2 Q-0.16,0 -0.1,0.02 L0.58,0.02 Q0.66,0.01 0.64,-0.06 Q0.6,-0.14 0.3,-0.17 L0.12,-0.26 L-0.08,-0.26 Z", fill: C.cleat }),
    h("path", { key: "sw", d: "M0.02,-0.12 Q0.25,-0.04 0.48,-0.1", stroke: "#e9ecf1", strokeWidth: 0.035, fill: "none" }),
    h("rect", { key: "sole", x: -0.13, y: 0.0, width: 0.75, height: 0.03, fill: "#3a3f4a" }),
  ]);
}

function bat(): PartTexture {
  const L = BODY.bat;
  return part("h-bat", { x: -0.08, y: -0.14, w: L + 0.12, h: 0.28 }, [
    h("path", {
      key: "b",
      d: `M0.04,-0.045 L1.05,-0.04 C1.5,-0.05 1.75,-0.11 2.2,-0.112 L${L - 0.06},-0.112 A0.11,0.11 0 0 1 ${L - 0.06},0.112 L2.2,0.112 C1.75,0.11 1.5,0.05 1.05,0.04 L0.04,0.045 Z`,
      fill: "url(#maple)",
    }),
    h("rect", { key: "tape", x: 0.06, y: -0.047, width: 0.62, height: 0.094, fill: "#22252c" }),
    h("ellipse", { key: "knob", cx: 0.02, cy: 0, rx: 0.05, ry: 0.075, fill: C.mapleDark }),
    h("path", { key: "logo", d: `M2.05,-0.05 L2.35,-0.05`, stroke: "#7a5a33", strokeWidth: 0.03, opacity: 0.6 }),
  ], [
    h("linearGradient", { id: "maple", key: "maple", x1: 0, y1: 0, x2: 0, y2: 1 },
      h("stop", { offset: 0, stopColor: "#efd09c" }),
      h("stop", { offset: 0.45, stopColor: C.maple }),
      h("stop", { offset: 1, stopColor: C.mapleDark })),
  ], L);
}

/** Torso: waist at the origin, neck at (0, −torso). Shoulders 1.32 ft wide. */
function torso(): PartTexture {
  const t = BODY.torso;
  return part("h-torso", { x: -0.72, y: -t - 0.12, w: 1.44, h: t + 0.16 }, [
    h("path", {
      key: "j",
      d: `M-0.42,0.02 C-0.5,-0.6 -0.62,-1.0 -0.64,${-t + 0.32} Q-0.66,${-t + 0.04} -0.36,${-t - 0.02} L0.36,${-t - 0.02} Q0.66,${-t + 0.04} 0.64,${-t + 0.32} C0.62,-1.0 0.5,-0.6 0.42,0.02 Z`,
      fill: "url(#jersey)",
      stroke: C.jerseyShade,
      strokeWidth: 0.015,
    }),
    // Collar and placket piping, buttons.
    h("path", { key: "col", d: `M-0.2,${-t - 0.01} L0,${-t + 0.22} L0.2,${-t - 0.01}`, stroke: C.navy, strokeWidth: 0.05, fill: C.navy }),
    h("path", { key: "pl", d: `M0,${-t + 0.22} L0.02,0.0`, stroke: C.navy, strokeWidth: 0.04 }),
    ...[0.45, 0.8, 1.15].map((y) => h("circle", { key: `b${y}`, cx: 0.07, cy: -y, r: 0.025, fill: C.navy })),
    // Chest script stand-in: a team-colored swash.
    h("path", { key: "sw", d: `M-0.48,${-t + 0.62} Q-0.2,${-t + 0.48} 0.1,${-t + 0.6}`, stroke: C.red, strokeWidth: 0.07, fill: "none", strokeLinecap: "round" }),
    h("path", { key: "sw2", d: `M-0.46,${-t + 0.66} Q-0.2,${-t + 0.52} 0.08,${-t + 0.64}`, stroke: C.navy, strokeWidth: 0.025, fill: "none" }),
  ], [
    h("linearGradient", { id: "jersey", key: "jersey", x1: 0, y1: 0, x2: 1, y2: 0 },
      h("stop", { offset: 0, stopColor: C.jerseyShade }),
      h("stop", { offset: 0.35, stopColor: C.jersey }),
      h("stop", { offset: 0.7, stopColor: C.jersey }),
      h("stop", { offset: 1, stopColor: C.jerseyShade })),
  ]);
}

/** Hips: belt and the top of the pants, centered on the pelvis point. */
function pelvis(): PartTexture {
  return part("h-pelvis", { x: -0.52, y: -0.2, w: 1.04, h: 0.66 }, [
    h("path", { key: "p", d: "M-0.44,-0.1 L0.44,-0.1 Q0.5,0.2 0.42,0.42 L-0.42,0.42 Q-0.5,0.2 -0.44,-0.1 Z", fill: "url(#pantsP)" }),
    h("rect", { key: "belt", x: -0.45, y: -0.16, width: 0.9, height: 0.12, rx: 0.03, fill: C.navy }),
    h("rect", { key: "buckle", x: -0.06, y: -0.155, width: 0.12, height: 0.11, rx: 0.02, fill: "#c9ced8" }),
  ], [
    h("linearGradient", { id: "pantsP", key: "pantsP", x1: 0, y1: 0, x2: 1, y2: 0 },
      h("stop", { offset: 0, stopColor: C.pantsShade }),
      h("stop", { offset: 0.4, stopColor: C.pants }),
      h("stop", { offset: 1, stopColor: C.pantsShade })),
  ]);
}

/** Head in a batting helmet, face turned toward the pitcher; origin at the head's center. */
function head(): PartTexture {
  return part("h-head", { x: -0.5, y: -0.56, w: 1.04, h: 1.02 }, [
    // Neck
    h("path", { key: "n", d: "M-0.13,0.18 L-0.15,0.44 L0.17,0.44 L0.15,0.18 Z", fill: C.skinShade }),
    // Face
    h("ellipse", { key: "f", cx: 0.03, cy: 0.06, rx: 0.25, ry: 0.31, fill: "url(#skin)" }),
    h("path", { key: "nose", d: "M0.06,0.02 Q0.1,0.13 0.05,0.16", stroke: C.skinShade, strokeWidth: 0.025, fill: "none" }),
    h("path", { key: "eb1", d: "M-0.13,0.06 L-0.03,0.06", stroke: "#111", strokeWidth: 0.04, strokeLinecap: "round" }),
    h("path", { key: "eb2", d: "M0.09,0.06 L0.19,0.06", stroke: "#111", strokeWidth: 0.04, strokeLinecap: "round" }),
    h("circle", { key: "e1", cx: -0.08, cy: -0.01, r: 0.022, fill: "#1a1a1a" }),
    h("circle", { key: "e2", cx: 0.14, cy: -0.01, r: 0.022, fill: "#1a1a1a" }),
    h("path", { key: "m", d: "M-0.02,0.24 Q0.05,0.27 0.12,0.24", stroke: C.skinShade, strokeWidth: 0.02, fill: "none" }),
    // Helmet shell, brim, and the earflap on the side toward the pitcher.
    h("path", { key: "shell", d: "M-0.36,-0.02 Q-0.38,-0.48 0.04,-0.5 Q0.42,-0.48 0.38,-0.06 L0.3,-0.06 Q0.2,-0.1 -0.24,-0.08 Z", fill: "url(#helmet)" }),
    h("path", { key: "brim", d: "M-0.28,-0.1 Q0.05,-0.18 0.46,-0.07 L0.44,-0.02 Q0.05,-0.1 -0.26,-0.05 Z", fill: C.navy }),
    h("path", { key: "flap", d: "M0.22,-0.1 L0.4,-0.08 Q0.42,0.12 0.3,0.22 L0.2,0.16 Q0.24,0.04 0.22,-0.1 Z", fill: "url(#helmet)" }),
    h("path", { key: "hi", d: "M-0.22,-0.32 Q-0.05,-0.45 0.15,-0.42", stroke: "#ffffff", strokeOpacity: 0.35, strokeWidth: 0.05, fill: "none", strokeLinecap: "round" }),
    h("circle", { key: "logo", cx: 0.05, cy: -0.28, r: 0.06, fill: C.red }),
  ], [
    h("radialGradient", { id: "skin", key: "skin", cx: 0.6, cy: 0.4, r: 0.7 },
      h("stop", { offset: 0, stopColor: "#d8aa88" }),
      h("stop", { offset: 1, stopColor: C.skinShade })),
    h("radialGradient", { id: "helmet", key: "helmet", cx: 0.35, cy: 0.25, r: 0.8 },
      h("stop", { offset: 0, stopColor: C.navyHi }),
      h("stop", { offset: 1, stopColor: "#121a2c" })),
  ]);
}

export function buildHitterParts(): PartTexture[] {
  return [thigh(), shin(), upperArm(), forearm(), glove(), cleat(), bat(), torso(), pelvis(), head()];
}

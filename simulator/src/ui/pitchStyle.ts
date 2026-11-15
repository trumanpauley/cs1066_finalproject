/** Pitch colors (match the My Arsenal movement chart) and movement wording. */

import type { PitchDefinition } from "../engine";

export const PITCH_COLORS: Record<string, string> = {
  FF: "#ff6b4a",
  FA: "#ff6b4a",
  SI: "#f3a712",
  FC: "#b388ff",
  SL: "#00b4d8",
  ST: "#2ec4b6",
  SV: "#2ec4b6",
  CU: "#4895ef",
  KC: "#4895ef",
  CH: "#80ed99",
  FS: "#f15bb5",
  KN: "#adb5bd",
};

export const pitchColor = (code: string) => PITCH_COLORS[code] ?? "#c9d1e0";

/** "8 in arm-side run · 17 in ride" — from the pitch profile's HB / IVB. */
export function describeMovement(def: PitchDefinition): string {
  const hb = Math.round(def.horizontalBreak);
  const ivb = Math.round(def.inducedVerticalBreak);
  const horiz =
    hb === 0 ? "no run" : hb > 0 ? `${hb} in arm-side run` : `${-hb} in glove-side ${def.category === "breaking" ? "sweep" : "cut"}`;
  const vert = ivb === 0 ? "no ride" : ivb > 0 ? `${ivb} in ride` : `${-ivb} in drop`;
  return `${horiz} · ${vert}`;
}

/** Total spin-induced break in inches. */
export const totalBreak = (def: PitchDefinition) =>
  Math.round(Math.hypot(def.horizontalBreak, def.inducedVerticalBreak));

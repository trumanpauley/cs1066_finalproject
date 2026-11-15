/**
 * Data adapters. The engine only sees `PitcherProfile` / `HitterProfile`;
 * where they come from is decided here.
 *
 *   now:    bundled JSON (synthetic demo profiles)
 *   later:  window.PITCHIQ_DATA injected by the Streamlit page (profiles
 *           built from uploaded scouting reports), or a licensed data API.
 */

import type { HitterProfile, PitcherProfile } from "../engine";
import samplePitcher from "./samplePitcher.json";
import sampleHitters from "./sampleHitters.json";

export interface SimulatorData {
  pitcher: PitcherProfile;
  /** In batting order when they come from a loaded lineup. */
  hitters: HitterProfile[];
  /** Opponent name when hitters come from a team lineup. */
  team?: string;
}

declare global {
  interface Window {
    PITCHIQ_DATA?: Partial<SimulatorData>;
  }
}

const isRate = (v: unknown) => typeof v === "number" && v >= 0 && v <= 1;

/** Minimal shape checks so bad external data fails loudly, not silently. */
export function validateHitter(h: HitterProfile): string[] {
  const errors: string[] = [];
  if (!h.name) errors.push("missing name");
  if (h.bats !== "R" && h.bats !== "L") errors.push(`${h.name}: bats must be R or L`);
  for (const [k, v] of Object.entries(h.rates ?? {})) {
    if (!isRate(v)) errors.push(`${h.name}: rates.${k} must be in [0, 1]`);
  }
  if (!(h.zone?.top > h.zone?.bottom)) errors.push(`${h.name}: zone.top must exceed zone.bottom`);
  for (const cat of ["fastball", "breaking", "offspeed"] as const) {
    if (!h.byPitchType?.[cat]) errors.push(`${h.name}: missing byPitchType.${cat}`);
  }
  if (!h.source?.label) errors.push(`${h.name}: missing source label`);
  return errors;
}

export function validatePitcher(p: PitcherProfile): string[] {
  const errors: string[] = [];
  if (!p.pitches?.length) errors.push("pitcher has no pitches");
  for (const pitch of p.pitches ?? []) {
    if (!(pitch.velocity > 40)) errors.push(`${pitch.code}: invalid velocity`);
    if (!(pitch.command?.sdX > 0 && pitch.command?.sdZ > 0)) errors.push(`${pitch.code}: invalid command`);
  }
  return errors;
}

export function loadSimulatorData(): SimulatorData {
  const injected = typeof window !== "undefined" ? window.PITCHIQ_DATA : undefined;

  // Pitcher and hitters are validated separately so one bad record never
  // throws away the rest; anything invalid falls back to the samples.
  let pitcher = samplePitcher as PitcherProfile;
  if (injected?.pitcher) {
    const errors = validatePitcher(injected.pitcher);
    if (errors.length) console.warn("PitchIQ: injected pitcher ignored:", errors);
    else pitcher = injected.pitcher;
  }

  const lineup = (injected?.hitters ?? []).filter((h) => {
    const errors = validateHitter(h);
    if (errors.length) console.warn(`PitchIQ: hitter ${h?.name ?? "?"} ignored:`, errors);
    return errors.length === 0;
  });

  return lineup.length
    ? { pitcher, hitters: lineup, team: injected?.team || undefined }
    : { pitcher, hitters: sampleHitters as HitterProfile[] };
}

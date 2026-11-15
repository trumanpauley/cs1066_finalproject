import { describe, expect, it } from "vitest";
import samplePitcher from "../data/samplePitcher.json";
import sampleHitters from "../data/sampleHitters.json";
import { validateHitter, validatePitcher } from "../data/loaders";
import {
  applyCall,
  contactProbabilities,
  createRng,
  describeLocation,
  executePitch,
  hitProbabilities,
  newAtBat,
  simulateBattedBall,
  swingProbability,
  throwPitch,
  type AtBatState,
  type Count,
  type HitterProfile,
  type PitchExecution,
  type PitcherProfile,
} from "./index";

const pitcher = samplePitcher as PitcherProfile;
const hitters = sampleHitters as HitterProfile[];
const rhh = hitters.find((h) => h.bats === "R")!;
const lhh = hitters.find((h) => h.bats === "L")!;

const MIDDLE = { x: 0, z: 2.5 };
const LOW_AWAY_CHASE_RHH = { x: 1.25, z: 1.0 }; // off the plate away + below the zone

function pitchAt(code: string, x: number, z: number, hitter = rhh): PitchExecution {
  const def = pitcher.pitches.find((p) => p.code === code)!;
  const exec = executePitch({ ...def, command: { sdX: 1e-9, sdZ: 1e-9 }, velocitySd: 0 }, { x, z }, hitter, createRng(1));
  return exec;
}

const COUNTS: Count[] = [];
for (let b = 0; b <= 3; b++) for (let s = 0; s <= 2; s++) COUNTS.push({ balls: b, strikes: s });

describe("sample data", () => {
  it("passes validation and is labeled synthetic", () => {
    expect(validatePitcher(pitcher)).toEqual([]);
    for (const h of hitters) {
      expect(validateHitter(h)).toEqual([]);
      expect(h.source.kind).toBe("synthetic");
      expect(h.source.label).toMatch(/not real MLB data/);
    }
  });
});

describe("rng", () => {
  it("is reproducible with a fixed seed", () => {
    const a = createRng(42);
    const b = createRng(42);
    for (let i = 0; i < 50; i++) expect(a.next()).toBe(b.next());
  });

  it("produces roughly standard-normal samples", () => {
    const rng = createRng(7);
    const xs = Array.from({ length: 20000 }, () => rng.normal());
    const mean = xs.reduce((s, x) => s + x, 0) / xs.length;
    const sd = Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / xs.length);
    expect(Math.abs(mean)).toBeLessThan(0.03);
    expect(Math.abs(sd - 1)).toBeLessThan(0.03);
  });
});

describe("step A — execution", () => {
  it("scatters around the target according to command", () => {
    const rng = createRng(3);
    const ff = pitcher.pitches[0];
    const misses = Array.from({ length: 5000 }, () => executePitch(ff, MIDDLE, rhh, rng).actual.x);
    const sd = Math.sqrt(misses.reduce((s, x) => s + x * x, 0) / misses.length);
    expect(Math.abs(sd - ff.command.sdX)).toBeLessThan(0.02);
  });

  it("target and actual are different concepts", () => {
    const exec = executePitch(pitcher.pitches[1], MIDDLE, rhh, createRng(9));
    expect(exec.target).toEqual(MIDDLE);
    expect(exec.actual).not.toEqual(MIDDLE);
  });
});

describe("steps B + C — probabilities are valid everywhere", () => {
  it("swing and contact probabilities stay in range and sum to 1", () => {
    for (const hitter of hitters) {
      for (const code of ["FF", "SL", "CH"]) {
        for (let x = -2.5; x <= 2.5; x += 0.25) {
          for (let z = 0.3; z <= 5; z += 0.25) {
            const pitch = pitchAt(code, x, z, hitter);
            for (const count of COUNTS) {
              const s = swingProbability(pitch, count, hitter, pitcher).probability;
              expect(s).toBeGreaterThanOrEqual(0);
              expect(s).toBeLessThanOrEqual(1);
              const c = contactProbabilities(pitch, count, hitter);
              for (const v of Object.values(c)) {
                expect(v).toBeGreaterThanOrEqual(0);
                expect(v).toBeLessThanOrEqual(1);
              }
              expect(c.miss + c.foul + c.inPlay).toBeCloseTo(1, 10);
            }
          }
        }
      }
    }
  });

  it("hitters swing more at strikes than at chase pitches", () => {
    const count = { balls: 1, strikes: 1 };
    const middle = swingProbability(pitchAt("SL", 0, 2.5), count, rhh, pitcher).probability;
    const chase = swingProbability(pitchAt("SL", LOW_AWAY_CHASE_RHH.x, LOW_AWAY_CHASE_RHH.z), count, rhh, pitcher).probability;
    const wayOff = swingProbability(pitchAt("SL", 3, 0.5), count, rhh, pitcher).probability;
    expect(middle).toBeGreaterThan(chase);
    expect(chase).toBeGreaterThan(wayOff);
  });

  it("two strikes raise swing rate; 3-0 lowers it", () => {
    const p = pitchAt("FF", 0.6, 2.0);
    const neutral = swingProbability(p, { balls: 1, strikes: 1 }, rhh, pitcher).probability;
    expect(swingProbability(p, { balls: 1, strikes: 2 }, rhh, pitcher).probability).toBeGreaterThan(neutral);
    expect(swingProbability(p, { balls: 3, strikes: 0 }, rhh, pitcher).probability).toBeLessThan(neutral);
  });

  it("the free-swinger chases more than the patient hitter", () => {
    const count = { balls: 0, strikes: 1 };
    const away = (h: HitterProfile) => (h.bats === "R" ? 1.3 : -1.3);
    const slugger = swingProbability(pitchAt("SL", away(rhh), 1.2, rhh), count, rhh, pitcher).probability;
    const patient = swingProbability(pitchAt("SL", away(lhh), 1.2, lhh), count, lhh, pitcher).probability;
    expect(slugger).toBeGreaterThan(patient);
  });

  it("contact is easier in the zone than out of it", () => {
    const count = { balls: 0, strikes: 0 };
    const inZone = contactProbabilities(pitchAt("CH", 0, 2.4), count, rhh);
    const outZone = contactProbabilities(pitchAt("CH", 1.2, 1.0), count, rhh);
    expect(inZone.miss).toBeLessThan(outZone.miss);
  });
});

describe("step D — batted balls", () => {
  it("hit probabilities are valid probabilities", () => {
    for (let ev = 40; ev <= 118; ev += 4) {
      for (let la = -40; la <= 80; la += 5) {
        for (const dist of [50, 150, 250, 350, 420]) {
          const p = hitProbabilities(ev, la, dist);
          expect(p.homeRun).toBeGreaterThanOrEqual(0);
          expect(p.hit).toBeGreaterThanOrEqual(0);
          expect(p.homeRun + p.hit).toBeLessThanOrEqual(1);
        }
      }
    }
  });

  it("identical pitches do not always produce identical outcomes", () => {
    const rng = createRng(11);
    const results = new Set(
      Array.from({ length: 200 }, () => simulateBattedBall(pitchAt("FF", 0, 2.5), rhh, rng).result),
    );
    expect(results.size).toBeGreaterThan(3);
  });

  it("produces a plausible league-like batting average on balls in play", () => {
    const rng = createRng(5);
    const n = 4000;
    let hits = 0;
    for (let i = 0; i < n; i++) {
      const r = simulateBattedBall(pitchAt("FF", 0.3, 2.3), rhh, rng).result;
      if (["single", "double", "triple", "home_run"].includes(r)) hits++;
    }
    const avg = hits / n;
    expect(avg).toBeGreaterThan(0.22);
    expect(avg).toBeLessThan(0.45);
  });
});

describe("count + plate appearance logic", () => {
  it("fouls with two strikes keep the count", () => {
    expect(applyCall({ balls: 1, strikes: 2 }, "foul").count).toEqual({ balls: 1, strikes: 2 });
    expect(applyCall({ balls: 1, strikes: 1 }, "foul").count).toEqual({ balls: 1, strikes: 2 });
  });

  it("ball four is a walk, strike three is a strikeout", () => {
    expect(applyCall({ balls: 3, strikes: 2 }, "ball").result).toBe("walk");
    expect(applyCall({ balls: 3, strikes: 2 }, "called_strike").result).toBe("strikeout");
    expect(applyCall({ balls: 0, strikes: 2 }, "swinging_strike").result).toBe("strikeout");
  });

  it("a full plate appearance always ends, and the seed reproduces it", () => {
    const play = (seed: number) => {
      const rng = createRng(seed);
      let state: AtBatState = newAtBat();
      let guard = 0;
      while (!state.result && guard++ < 100) {
        state = throwPitch(state, { pitchCode: "SL", target: { x: 0.9, z: 1.5 } }, pitcher, rhh, rng).state;
      }
      return state;
    };
    for (let seed = 1; seed <= 200; seed++) {
      const s = play(seed);
      expect(s.result).toBeDefined();
      expect(s.pitches.length).toBeGreaterThan(0);
    }
    expect(play(77)).toEqual(play(77));
  });

  it("pitches at the hitter's body are hit-by-pitch", () => {
    const rng = createRng(2);
    const def = { ...pitcher, pitches: pitcher.pitches.map((p) => ({ ...p, command: { sdX: 1e-9, sdZ: 1e-9 } })) };
    const { outcome, state } = throwPitch(newAtBat(), { pitchCode: "FF", target: { x: -2, z: 3 } }, def, rhh, rng);
    expect(outcome.call).toBe("hit_by_pitch");
    expect(state.result).toBe("hit_by_pitch");
  });

  it("refuses pitches after the plate appearance ends", () => {
    const done: AtBatState = { ...newAtBat(), result: "walk" };
    expect(() => throwPitch(done, { pitchCode: "FF", target: MIDDLE }, pitcher, rhh, createRng(1))).toThrow();
  });

  it("explanations cite the model's own probabilities", () => {
    const { outcome } = throwPitch(newAtBat(), { pitchCode: "SL", target: { x: 0.9, z: 1.4 } }, pitcher, rhh, createRng(4));
    expect(outcome.explanation.some((e) => /Swing chance \d+%/.test(e))).toBe(true);
    expect(outcome.description).toMatch(/^Slider, \d+ mph, /);
  });
});

describe("location language", () => {
  it("describes location from the hitter's point of view", () => {
    // x > 0 is the first-base side: away from a righty, inside on a lefty.
    expect(describeLocation({ x: 0.6, z: 1.8 }, rhh)).toBe("low and away");
    expect(describeLocation({ x: 0.6, z: 1.8 }, lhh)).toBe("low and in");
    expect(describeLocation({ x: 0, z: 2.5 }, rhh)).toBe("middle-middle");
  });
});

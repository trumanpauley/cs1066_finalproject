import { expect, it } from "vitest";
import pitcherJson from "../data/samplePitcher.json";
import type { PitchOutcome, PitcherProfile } from "../engine";
import { flightPaths, makeAnimation } from "./animation";
import { setCameraHeight } from "./projection";

// Regression test: a close camera made balls released below eye level look
// like they climbed out of the hand. Only a ball actually thrown upward
// (a low release to a high target) may move up on screen.
it("pitch trails move down on screen unless the ball is thrown upward", () => {
  const base = pitcherJson as PitcherProfile;
  let worst = 0;
  let worstCase = "";
  for (const hand of ["R", "L"] as const)
    for (const relZ of [5.0, 5.5, 6.0, 6.5])
      for (const ext of [5.5, 6.5, 7.2])
        for (const def of base.pitches)
          for (const tz of [1.2, 2.0, 2.8, 3.6])
            for (const tx of [-1.2, 0, 1.2]) {
              setCameraHeight(relZ);
              const pitcher = { ...base, hand, release: { x: hand === "R" ? -1.8 : 1.8, z: relZ, extension: ext } };
              const outcome = { pitch: { code: def.code, velocity: def.velocity, actual: { x: tx, z: tz }, target: { x: tx, z: tz } },
                swing: { swung: false }, call: "ball" } as unknown as PitchOutcome;
              const { real } = flightPaths(makeAnimation(outcome, pitcher, 0.5));
              // World height of the ball: initial vertical velocity (ft per unit t).
              const T = (60.5 - ext) / (def.velocity * 1.4667);
              const drop = 0.5 * 32.17 * T * T;
              const vz0 = tz - def.inducedVerticalBreak / 12 - relZ + drop; // dz/dt at t=0 (ghost)
              for (let i = 1; i < real.length; i++) {
                const step = real[i].sy - real[i - 1].sy;
                if (vz0 <= 0 && step < worst) { worst = step; worstCase = `${hand} rel ${relZ} ext ${ext} ${def.code} -> (${tx},${tz}) i=${i}`; }
              }
            }
  expect(worstCase === "" || worst > -0.5, worstCase).toBe(true);
});

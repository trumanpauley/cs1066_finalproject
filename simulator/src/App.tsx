import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createRng,
  newAtBat,
  OUT_RESULTS,
  throwPitch,
  type AtBatState,
  type Location,
  type PitchOutcome,
} from "./engine";
import { loadSimulatorData } from "./data/loaders";
import { flightPaths, frameAt, makeAnimation, releaseOf, type Frame, type PitchAnimation } from "./ui/animation";
import { pitchColor, totalBreak } from "./ui/pitchStyle";
import { setCameraHeight } from "./ui/projection";
import { BoxScore, PitchMenu, ResultBanner, Scoreboard, type BoxEntry } from "./ui/Hud";
import { PhaserStage } from "./game/PhaserStage";
import type { PitchFx, PitchMarker, PitchTrail } from "./ui/sceneTypes";

/** Replays run at this fraction of the (already slowed) pitch speed. */
const REPLAY_SPEED = 0.35;

declare global {
  interface Window {
    PITCHIQ_SEED?: number;
  }
}

function initialSeed(): number {
  const fromUrl = Number(new URLSearchParams(window.location.search).get("seed"));
  if (Number.isFinite(fromUrl) && fromUrl > 0) return fromUrl;
  if (typeof window.PITCHIQ_SEED === "number") return window.PITCHIQ_SEED;
  return Date.now();
}

type Phase = "aiming" | "pitching" | "done";

export default function App() {
  const data = useMemo(() => {
    const d = loadSimulatorData();
    setCameraHeight(d.pitcher.release.z); // before the first render
    return d;
  }, []);
  const rng = useMemo(() => createRng(initialSeed()), []);
  const { pitcher } = data;

  const lineup = data.hitters;
  const [batterIndex, setBatterIndex] = useState(0);
  const hitter = lineup[batterIndex] ?? lineup[0];
  const nextHitter = lineup[(batterIndex + 1) % lineup.length];
  const [box, setBox] = useState<BoxEntry[]>([]);
  // Flight paths of this plate appearance's pitches (cleared each new PA).
  const [trails, setTrails] = useState<PitchTrail[]>([]);
  const [atBat, setAtBat] = useState<AtBatState>(() => newAtBat());
  const [pitchCode, setPitchCode] = useState(pitcher.pitches[0].code);
  const [target, setTarget] = useState<Location | null>(null);
  const [phase, setPhase] = useState<Phase>("aiming");
  const [last, setLast] = useState<PitchOutcome | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const [frame, setFrame] = useState<Frame | null>(null);
  const pending = useRef<{ anim: PitchAnimation & { hitterName: string }; next: AtBatState } | null>(null);
  // The last pitch's animation, kept for slow-motion replays.
  const lastAnim = useRef<PitchAnimation | null>(null);
  const [replays, setReplays] = useState(0);
  // Counts every pitch thrown this session (gives each pitch's effects an id).
  const [pitchSerial, setPitchSerial] = useState(0);
  const [replaying, setReplaying] = useState(false);

  // --- animation loop -------------------------------------------------------
  useEffect(() => {
    if (phase !== "pitching" || !pending.current) return;
    const { anim, next } = pending.current;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const f = frameAt(anim, now - start);
      setFrame(f);
      if (f.done) {
        setAtBat(next);
        setTrails((t) => [
          ...t,
          {
            n: next.pitches.length,
            color: pitchColor(anim.def.code),
            ...flightPaths(anim),
            breakIn: totalBreak(anim.def),
          },
        ]);
        if (next.result) {
          const result = next.result;
          setBox((b) => [...b, { hitter: anim.hitterName, result, pitches: next.pitches.length }]);
        }
        setLast(anim.outcome);
        lastAnim.current = anim;
        setPhase(next.result ? "done" : "aiming");
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  // --- slow-motion replay of the last pitch ---------------------------------
  useEffect(() => {
    const anim = lastAnim.current;
    if (!replaying || !anim) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const f = frameAt(anim, (now - start) * REPLAY_SPEED);
      setFrame(f);
      if (f.done) {
        setReplaying(false);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [replaying]);

  const replay = useCallback(() => {
    if (phase === "pitching" || replaying || !lastAnim.current) return;
    setReplays((n) => n + 1);
    setReplaying(true);
  }, [phase, replaying]);

  const throwIt = useCallback(() => {
    if (phase !== "aiming" || !target || replaying) return;
    const { state, outcome } = throwPitch(atBat, { pitchCode, target }, pitcher, hitter, rng);
    pending.current = { anim: { ...makeAnimation(outcome, pitcher, rng.next()), hitterName: hitter.name }, next: state };
    setLast(null);
    setPitchSerial((n) => n + 1);
    setPhase("pitching");
  }, [phase, target, atBat, pitchCode, pitcher, hitter, rng, replaying]);

  /** Start a plate appearance; three outs retire the side and clear the box. */
  const startAtBat = useCallback(
    (index: number, keepOuts: boolean) => {
      const sideRetired = atBat.outs >= 3;
      setBatterIndex(index);
      setAtBat(newAtBat(keepOuts && !sideRetired ? atBat.outs : 0));
      if (!keepOuts || sideRetired) setBox([]);
      setTrails([]);
      setLast(null);
      lastAnim.current = null;
      setReplaying(false);
      setFrame(null);
      setPhase("aiming");
    },
    [atBat.outs],
  );
  const nextBatter = useCallback(
    () => startAtBat((batterIndex + 1) % lineup.length, true),
    [startAtBat, batterIndex, lineup.length],
  );

  // --- keyboard: 1-9 pick a pitch, Space/Enter throws ----------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLSelectElement) return;
      const n = Number(e.key);
      if (n >= 1 && n <= pitcher.pitches.length) setPitchCode(pitcher.pitches[n - 1].code);
      if (e.key === "r" || e.key === "R") replay();
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (phase === "done") nextBatter();
        else throwIt();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pitcher, phase, throwIt, nextBatter, replay]);

  const markers: PitchMarker[] = atBat.pitches.map((p, i) => ({
    n: i + 1,
    loc: p.pitch.actual,
    call: p.call,
  }));

  const lastDef = last ? pitcher.pitches.find((p) => p.code === last.pitch.code) : undefined;

  // The pitch the stage is showing (in flight, or being replayed).
  const shown = phase === "pitching" ? pending.current?.anim : replaying ? lastAnim.current : null;
  const fx: PitchFx | null = shown
    ? {
        id: `${pitchSerial}-${replaying ? `replay${replays}` : "live"}`,
        call: shown.outcome.call,
        perceivedVelocity: shown.outcome.pitch.perceivedVelocity,
        actual: shown.outcome.pitch.actual,
        battedBallType: shown.outcome.battedBall?.type,
      }
    : null;
  const result = atBat.result;
  const isOut = result ? OUT_RESULTS.includes(result) : false;
  const sideRetired = atBat.outs >= 3;

  return (
    <div className="app">
      <Scoreboard
        hitters={lineup}
        hitter={hitter}
        team={data.team}
        state={atBat}
        locked={phase === "pitching"}
        onHitter={(id) => startAtBat(Math.max(0, lineup.findIndex((h) => h.id === id)), true)}
        onReset={() => startAtBat(batterIndex, false)}
      />
      <BoxScore entries={box} isOut={(r) => OUT_RESULTS.includes(r)} />

      <div className="stage">
        <PhaserStage
          hitter={hitter}
          target={target}
          aiming={phase === "aiming" && !replaying}
          frame={phase === "aiming" && !replaying ? null : frame}
          markers={markers}
          trails={replaying ? trails.slice(0, -1) : trails}
          flightColor={shown ? pitchColor(shown.def.code) : undefined}
          fx={fx}
          onAim={setTarget}
        />
        {replaying && <div className="replay-tag">Replay · slow motion</div>}
        {phase === "aiming" && !target && atBat.pitches.length === 0 && (
          <div className="hint">Pick a pitch, then click where you want to locate it.</div>
        )}
        {phase === "done" && result && last && !replaying && (
          <div className="overlay">
            <div className={`final ${isOut ? "final-out" : "final-safe"}`}>
              <span className="final-label">
                {sideRetired ? "Side retired" : isOut ? "Out" : "On base"}
              </span>
              <h2>{last.headline}</h2>
              <p>
                {hitter.name} · {atBat.pitches.length} pitch{atBat.pitches.length === 1 ? "" : "es"} ·{" "}
                {last.description}
              </p>
              <div className="final-actions">
                {lineup.length > 1 ? (
                  <>
                    <button className="throw" onClick={nextBatter}>
                      {sideRetired ? "New inning" : "Next batter"}: {nextHitter.name.split(" ").slice(-1)[0]}{" "}
                      <kbd>Space</kbd>
                    </button>
                    <button className="ghost" onClick={() => startAtBat(batterIndex, true)}>
                      Face again
                    </button>
                  </>
                ) : (
                  <button className="throw" onClick={() => startAtBat(batterIndex, true)}>
                    Face again <kbd>Space</kbd>
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <ResultBanner
        outcome={last}
        pitchDef={lastDef}
        releaseHeight={lastDef ? releaseOf(lastDef, pitcher).z : undefined}
        sourceLabel={hitter.source.label}
        showWhy={showWhy}
        onToggleWhy={() => setShowWhy((v) => !v)}
        onReplay={lastAnim.current && !replaying && phase !== "pitching" ? replay : undefined}
      />

      <PitchMenu
        pitches={pitcher.pitches}
        selected={pitchCode}
        onSelect={setPitchCode}
        onThrow={throwIt}
        canThrow={phase === "aiming" && !!target && !replaying}
        hasTarget={!!target}
      />
      <footer className="foot">
        {pitcher.name} ({pitcher.hand}HP) · {hitter.blurb ? `${hitter.name} ${hitter.blurb} · ` : ""}
        {hitter.source.label}
      </footer>
    </div>
  );
}

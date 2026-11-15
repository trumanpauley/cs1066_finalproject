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
import { frameAt, makeAnimation, type Frame, type PitchAnimation } from "./ui/animation";
import { BoxScore, PitchMenu, ResultBanner, Scoreboard, type BoxEntry } from "./ui/Hud";
import { Scene, type PitchMarker } from "./ui/Scene";

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
  const data = useMemo(loadSimulatorData, []);
  const rng = useMemo(() => createRng(initialSeed()), []);
  const { pitcher } = data;

  const lineup = data.hitters;
  const [batterIndex, setBatterIndex] = useState(0);
  const hitter = lineup[batterIndex] ?? lineup[0];
  const nextHitter = lineup[(batterIndex + 1) % lineup.length];
  const [box, setBox] = useState<BoxEntry[]>([]);
  const [atBat, setAtBat] = useState<AtBatState>(() => newAtBat());
  const [pitchCode, setPitchCode] = useState(pitcher.pitches[0].code);
  const [target, setTarget] = useState<Location | null>(null);
  const [phase, setPhase] = useState<Phase>("aiming");
  const [last, setLast] = useState<PitchOutcome | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const [frame, setFrame] = useState<Frame | null>(null);
  const pending = useRef<{ anim: PitchAnimation & { hitterName: string }; next: AtBatState } | null>(null);

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
        if (next.result) {
          const result = next.result;
          setBox((b) => [...b, { hitter: anim.hitterName, result, pitches: next.pitches.length }]);
        }
        setLast(anim.outcome);
        setPhase(next.result ? "done" : "aiming");
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  const throwIt = useCallback(() => {
    if (phase !== "aiming" || !target) return;
    const { state, outcome } = throwPitch(atBat, { pitchCode, target }, pitcher, hitter, rng);
    pending.current = { anim: { ...makeAnimation(outcome, pitcher, rng.next()), hitterName: hitter.name }, next: state };
    setLast(null);
    setPhase("pitching");
  }, [phase, target, atBat, pitchCode, pitcher, hitter, rng]);

  /** Start a plate appearance; three outs retire the side and clear the box. */
  const startAtBat = useCallback(
    (index: number, keepOuts: boolean) => {
      const sideRetired = atBat.outs >= 3;
      setBatterIndex(index);
      setAtBat(newAtBat(keepOuts && !sideRetired ? atBat.outs : 0));
      if (!keepOuts || sideRetired) setBox([]);
      setLast(null);
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
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (phase === "done") nextBatter();
        else throwIt();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pitcher, phase, throwIt, nextBatter]);

  const markers: PitchMarker[] = atBat.pitches.map((p, i) => ({
    n: i + 1,
    loc: p.pitch.actual,
    call: p.call,
  }));

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
        <Scene
          hitter={hitter}
          target={target}
          aiming={phase === "aiming"}
          frame={phase === "aiming" ? null : frame}
          markers={markers}
          onAim={setTarget}
        />
        {phase === "aiming" && !target && atBat.pitches.length === 0 && (
          <div className="hint">Pick a pitch, then click where you want to locate it.</div>
        )}
        {phase === "done" && result && last && (
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

      <ResultBanner outcome={last} sourceLabel={hitter.source.label} showWhy={showWhy} onToggleWhy={() => setShowWhy((v) => !v)} />

      <PitchMenu
        pitches={pitcher.pitches}
        selected={pitchCode}
        onSelect={setPitchCode}
        onThrow={throwIt}
        canThrow={phase === "aiming" && !!target}
        hasTarget={!!target}
      />
      <footer className="foot">
        {pitcher.name} ({pitcher.hand}HP) · {hitter.blurb ? `${hitter.name} ${hitter.blurb} · ` : ""}
        {hitter.source.label}
      </footer>
    </div>
  );
}

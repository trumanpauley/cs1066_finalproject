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
import { PitchMenu, ResultBanner, Scoreboard } from "./ui/Hud";
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

  const [hitterId, setHitterId] = useState(data.hitters[0].id);
  const hitter = data.hitters.find((h) => h.id === hitterId) ?? data.hitters[0];
  const [atBat, setAtBat] = useState<AtBatState>(() => newAtBat());
  const [pitchCode, setPitchCode] = useState(pitcher.pitches[0].code);
  const [target, setTarget] = useState<Location | null>(null);
  const [phase, setPhase] = useState<Phase>("aiming");
  const [last, setLast] = useState<PitchOutcome | null>(null);
  const [showWhy, setShowWhy] = useState(false);
  const [frame, setFrame] = useState<Frame | null>(null);
  const pending = useRef<{ anim: PitchAnimation; next: AtBatState } | null>(null);

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
    pending.current = { anim: makeAnimation(outcome, pitcher, rng.next()), next: state };
    setLast(null);
    setPhase("pitching");
  }, [phase, target, atBat, pitchCode, pitcher, hitter, rng]);

  const startAtBat = useCallback(
    (keepOuts: boolean) => {
      // Three outs retires the side: the next plate appearance starts fresh.
      setAtBat(newAtBat(keepOuts && atBat.outs < 3 ? atBat.outs : 0));
      setLast(null);
      setFrame(null);
      setPhase("aiming");
    },
    [atBat.outs],
  );

  // --- keyboard: 1-9 pick a pitch, Space/Enter throws ----------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLSelectElement) return;
      const n = Number(e.key);
      if (n >= 1 && n <= pitcher.pitches.length) setPitchCode(pitcher.pitches[n - 1].code);
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        if (phase === "done") startAtBat(true);
        else throwIt();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pitcher, phase, throwIt, startAtBat]);

  const markers: PitchMarker[] = atBat.pitches.map((p, i) => ({
    n: i + 1,
    loc: p.pitch.actual,
    call: p.call,
  }));

  const result = atBat.result;
  const isOut = result ? OUT_RESULTS.includes(result) : false;

  return (
    <div className="app">
      <Scoreboard
        hitters={data.hitters}
        hitter={hitter}
        state={atBat}
        locked={phase === "pitching"}
        onHitter={(id) => {
          setHitterId(id);
          setAtBat(newAtBat(atBat.outs < 3 ? atBat.outs : 0));
          setLast(null);
          setFrame(null);
          setPhase("aiming");
        }}
        onReset={() => startAtBat(false)}
      />

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
              <span className="final-label">{isOut ? "Out" : "On base"}</span>
              <h2>{last.headline}</h2>
              <p>
                {atBat.pitches.length} pitch{atBat.pitches.length === 1 ? "" : "es"} · {last.description}
              </p>
              <div className="final-actions">
                <button className="throw" onClick={() => startAtBat(true)}>
                  Face again <kbd>Space</kbd>
                </button>
                <button className="ghost" onClick={() => startAtBat(false)}>
                  Reset
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ResultBanner outcome={last} showWhy={showWhy} onToggleWhy={() => setShowWhy((v) => !v)} />

      <PitchMenu
        pitches={pitcher.pitches}
        selected={pitchCode}
        onSelect={setPitchCode}
        onThrow={throwIt}
        canThrow={phase === "aiming" && !!target}
        hasTarget={!!target}
      />
      <footer className="foot">
        {pitcher.name} ({pitcher.hand}HP) · {pitcher.source.label} · {hitter.source.label}
      </footer>
    </div>
  );
}

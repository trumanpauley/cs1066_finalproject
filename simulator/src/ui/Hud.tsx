import type { AtBatState, HitterProfile, PitchDefinition, PitchOutcome } from "../engine";
import { CALL_COLORS } from "./Scene";

function Dots({ label, n, max, color }: { label: string; n: number; max: number; color: string }) {
  return (
    <div className="dots" aria-label={`${label} ${n}`}>
      <span className="dots-label">{label}</span>
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className="dot" style={i < n ? { background: color, boxShadow: `0 0 8px ${color}` } : undefined} />
      ))}
    </div>
  );
}

interface ScoreboardProps {
  hitters: HitterProfile[];
  hitter: HitterProfile;
  state: AtBatState;
  onHitter: (id: string) => void;
  onReset: () => void;
  locked: boolean;
}

export function Scoreboard({ hitters, hitter, state, onHitter, onReset, locked }: ScoreboardProps) {
  return (
    <header className="scoreboard">
      <div className="sb-hitter">
        <select
          value={hitter.id}
          onChange={(e) => onHitter(e.target.value)}
          disabled={locked}
          aria-label="Choose a hitter"
        >
          {hitters.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name} ({h.bats}HH)
            </option>
          ))}
        </select>
        <span className={`chip ${hitter.source.kind === "synthetic" ? "chip-demo" : ""}`} title={hitter.source.label}>
          {hitter.source.kind === "synthetic" ? "Demo data" : "Report"}
        </span>
      </div>
      <div className="sb-count">
        <Dots label="B" n={Math.min(3, state.count.balls)} max={3} color="#4ade80" />
        <Dots label="S" n={Math.min(2, state.count.strikes)} max={2} color="#ff6b6b" />
        <Dots label="O" n={Math.min(3, state.outs)} max={3} color="#fbbf24" />
      </div>
      <button className="ghost" onClick={onReset} disabled={locked} title="Reset count and outs">
        Reset
      </button>
    </header>
  );
}

interface PitchMenuProps {
  pitches: PitchDefinition[];
  selected: string;
  onSelect: (code: string) => void;
  onThrow: () => void;
  canThrow: boolean;
  hasTarget: boolean;
}

export function PitchMenu({ pitches, selected, onSelect, onThrow, canThrow, hasTarget }: PitchMenuProps) {
  return (
    <div className="pitch-menu">
      <div className="pitch-options" role="radiogroup" aria-label="Pitch type">
        {pitches.map((p, i) => (
          <button
            key={p.code}
            role="radio"
            aria-checked={p.code === selected}
            className={`pitch ${p.code === selected ? "selected" : ""}`}
            onClick={() => onSelect(p.code)}
            title={`${p.name} · ${p.velocity} mph · ${Math.round(p.usage * 100)}% usage (key ${i + 1})`}
          >
            <span className="pitch-top">
              <span className="pitch-code">{p.code}</span>
              <span className="pitch-velo">{p.velocity}</span>
            </span>
            <span className="pitch-name">{p.name}</span>
          </button>
        ))}
      </div>
      <button className="throw" onClick={onThrow} disabled={!canThrow}>
        {hasTarget ? "Throw" : "Aim first"}
        <kbd>Space</kbd>
      </button>
    </div>
  );
}

interface ResultProps {
  outcome: PitchOutcome | null;
  showWhy: boolean;
  onToggleWhy: () => void;
}

export function ResultBanner({ outcome, showWhy, onToggleWhy }: ResultProps) {
  if (!outcome) return null;
  const color = CALL_COLORS[outcome.call];
  const bb = outcome.battedBall;
  return (
    <div className="result" key={outcome.pitch.code + outcome.countBefore.balls + outcome.countBefore.strikes + outcome.headline}>
      <div className="result-head">
        <span className="result-dot" style={{ background: color }} />
        <strong>{outcome.headline}</strong>
        <span className="result-desc">{outcome.description}</span>
        <button className="link" onClick={onToggleWhy}>
          {showWhy ? "Hide" : "Why?"}
        </button>
      </div>
      {bb && (
        <div className="bb-chips">
          <span>{bb.exitVelo} mph EV</span>
          <span>{bb.launchAngle}° LA</span>
          <span>{bb.distance} ft</span>
          <span>{bb.type.replace("_", " ")}</span>
        </div>
      )}
      {showWhy && (
        <div className="why">
          <ProbBar label="Swing" p={outcome.swing.probability} hit={outcome.swing.swung} />
          {outcome.contact && (
            <>
              <ProbBar label="Whiff" p={outcome.contact.probabilities.miss} hit={outcome.contact.result === "miss"} />
              <ProbBar label="Foul" p={outcome.contact.probabilities.foul} hit={outcome.contact.result === "foul"} />
              <ProbBar label="In play" p={outcome.contact.probabilities.inPlay} hit={outcome.contact.result === "inPlay"} />
            </>
          )}
          {bb && <ProbBar label="Hit" p={bb.hitProbability} hit={["single", "double", "triple", "home_run"].includes(bb.result)} />}
          <ul>
            {outcome.explanation.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
          <p className="fine">Model inputs come from the hitter's synthetic demo profile — not real MLB data.</p>
        </div>
      )}
    </div>
  );
}

function ProbBar({ label, p, hit }: { label: string; p: number; hit: boolean }) {
  return (
    <div className={`prob ${hit ? "prob-hit" : ""}`}>
      <span className="prob-label">{label}</span>
      <span className="prob-track">
        <span className="prob-fill" style={{ width: `${Math.round(p * 100)}%` }} />
      </span>
      <span className="prob-val">{Math.round(p * 100)}%</span>
    </div>
  );
}

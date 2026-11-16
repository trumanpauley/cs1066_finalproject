import type { AtBatState, DataSource, HitterProfile, PitchDefinition, PitchOutcome, PlateAppearanceResult } from "../engine";
import { CALL_COLORS } from "./sceneTypes";
import { describeMovement, pitchColor } from "./pitchStyle";

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

const SOURCE_CHIP: Record<DataSource["kind"], string> = {
  synthetic: "Demo data",
  profile: "Profile",
  scouting_report: "Report",
  api: "Savant",
};

interface ScoreboardProps {
  hitters: HitterProfile[];
  hitter: HitterProfile;
  team?: string;
  state: AtBatState;
  onHitter: (id: string) => void;
  onReset: () => void;
  locked: boolean;
}

export function Scoreboard({ hitters, hitter, team, state, onHitter, onReset, locked }: ScoreboardProps) {
  return (
    <header className="scoreboard">
      <div className="sb-hitter">
        {team && <span className="sb-team">{team}</span>}
        <select
          value={hitter.id}
          onChange={(e) => onHitter(e.target.value)}
          disabled={locked}
          aria-label="Choose a hitter"
        >
          {hitters.map((h, i) => (
            <option key={h.id} value={h.id}>
              {team ? `${i + 1}. ` : ""}
              {h.name} ({h.bats}HH)
            </option>
          ))}
        </select>
        <span
          className={`chip ${hitter.source.kind === "synthetic" ? "chip-demo" : "chip-real"}`}
          title={hitter.source.label}
        >
          {SOURCE_CHIP[hitter.source.kind]}
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
            title={`${p.name} · ${p.velocity} mph · ${describeMovement(p)} · ${Math.round(p.usage * 100)}% usage (key ${i + 1})`}
          >
            <span className="pitch-top">
              <span className="pitch-code" style={{ color: pitchColor(p.code) }}>
                <span className="pitch-dot" style={{ background: pitchColor(p.code) }} />
                {p.code}
              </span>
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
  pitchDef?: PitchDefinition;
  /** Release height (ft) used for this pitch. */
  releaseHeight?: number;
  sourceLabel: string;
  showWhy: boolean;
  /** Present when a slow-motion replay of the last pitch is available. */
  onReplay?: () => void;
  onToggleWhy: () => void;
}

export function ResultBanner({ outcome, pitchDef, releaseHeight, sourceLabel, showWhy, onToggleWhy, onReplay }: ResultProps) {
  if (!outcome) return null;
  const color = CALL_COLORS[outcome.call];
  const bb = outcome.battedBall;
  return (
    <div className="result" key={outcome.pitch.code + outcome.countBefore.balls + outcome.countBefore.strikes + outcome.headline}>
      <div className="result-head">
        <span className="result-dot" style={{ background: color }} />
        <strong>{outcome.headline}</strong>
        <span className="result-desc">{outcome.description}</span>
        {onReplay && (
          <button className="link" onClick={onReplay} title="Slow-motion replay (R)">
            Replay
          </button>
        )}
        <button className="link" onClick={onToggleWhy}>
          {showWhy ? "Hide" : "Why?"}
        </button>
      </div>
      {pitchDef && (
        <div className="move-line" style={{ color: pitchColor(pitchDef.code) }}>
          <span className="pitch-dot" style={{ background: pitchColor(pitchDef.code) }} />
          {pitchDef.name} break: {describeMovement(pitchDef)}
          <span className="move-hint"> · dashed ring = same pitch with no spin</span>
        </div>
      )}
      <div className="release-line">
        Release {releaseHeight ? `${feetInches(releaseHeight)} high · ` : ""}
        {feetInches(outcome.pitch.extension)} extension · plays like{" "}
        <b>{outcome.pitch.perceivedVelocity.toFixed(1)} mph</b>
        {Math.abs(outcome.pitch.perceivedVelocity - outcome.pitch.velocity) >= 0.1 && (
          <span className="move-hint"> (radar {outcome.pitch.velocity.toFixed(1)})</span>
        )}
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
          <p className="fine">Hitter model inputs: {sourceLabel}.</p>
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

const SHORT: Record<PlateAppearanceResult, string> = {
  strikeout: "K", walk: "BB", hit_by_pitch: "HBP", single: "1B", double: "2B", triple: "3B",
  home_run: "HR", groundout: "GO", lineout: "LO", flyout: "FO", popout: "PO",
};

export interface BoxEntry {
  hitter: string;
  result: PlateAppearanceResult;
  pitches: number;
}

/** Results of every plate appearance so far, e.g. "Turang K · Chourio 1B". */
export function BoxScore({ entries, isOut }: { entries: BoxEntry[]; isOut: (r: PlateAppearanceResult) => boolean }) {
  if (!entries.length) return null;
  return (
    <div className="box" aria-label="Plate appearance results">
      {entries.map((e, i) => (
        <span key={i} className={`box-pa ${isOut(e.result) ? "box-out" : "box-safe"}`} title={`${e.pitches} pitches`}>
          {e.hitter.split(" ").slice(-1)[0]} <b>{SHORT[e.result]}</b>
        </span>
      ))}
    </div>
  );
}

/** 6.3 -> 6'4" */
function feetInches(feet: number): string {
  let ft = Math.floor(feet);
  let inches = Math.round((feet - ft) * 12);
  if (inches === 12) {
    ft += 1;
    inches = 0;
  }
  return `${ft}'${inches}"`;
}

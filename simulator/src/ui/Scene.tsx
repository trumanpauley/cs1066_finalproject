import { useRef, useState, type MouseEvent } from "react";
import { zoneBounds, type HitterProfile, type Location, type PitchCall } from "../engine";
import type { Frame } from "./animation";
import { CatcherFigure, HitterFigure, Mitt, UmpireFigure } from "./figures";
import { polygon, project, unprojectAtPlate, VIEW_H, VIEW_W } from "./projection";

export interface PitchTrail {
  n: number;
  color: string;
  real: { sx: number; sy: number }[];
  ghost: { sx: number; sy: number }[];
  /** Total spin-induced break, inches. */
  breakIn: number;
}

export interface PitchMarker {
  n: number;
  loc: Location;
  call: PitchCall;
}

export const CALL_COLORS: Record<PitchCall, string> = {
  ball: "#4ade80",
  called_strike: "#ff6b6b",
  swinging_strike: "#ff6b6b",
  foul: "#fbbf24",
  in_play: "#7aa2f7",
  hit_by_pitch: "#c084fc",
};

interface SceneProps {
  hitter: HitterProfile;
  target: Location | null;
  aiming: boolean;
  frame: Frame | null;
  markers: PitchMarker[];
  trails: PitchTrail[];
  /** Color of the pitch in flight (for the ghost ball). */
  flightColor?: string;
  onAim: (loc: Location) => void;
}

export function Scene({ hitter, target, aiming, frame, markers, trails, flightColor, onAim }: SceneProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<Location | null>(null);

  const zb = zoneBounds(hitter);
  const cw = (zb.right - zb.left) / 3;
  const ch = (zb.top - zb.bottom) / 3;
  const grid = {
    left: zb.left - cw,
    right: zb.right + cw,
    bottom: zb.bottom - ch,
    top: zb.top + ch,
  };

  const toWorld = (e: MouseEvent<SVGElement>): Location | null => {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) return null;
    const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
    const w = unprojectAtPlate(pt.x, pt.y);
    if (w.x < grid.left || w.x > grid.right || w.z < grid.bottom || w.z > grid.top) return null;
    return { x: w.x, z: w.z };
  };

  const rectPts = (l: number, r: number, b: number, t: number) =>
    polygon([[l, 0, t], [r, 0, t], [r, 0, b], [l, 0, b]]);

  const hoverCell = hover && aiming ? cellOf(hover) : null;
  function cellOf(loc: Location) {
    const c = Math.floor((loc.x - grid.left) / cw);
    const r = Math.floor((loc.z - grid.bottom) / ch);
    return { l: grid.left + c * cw, b: grid.bottom + r * ch };
  }

  const mitt = frame?.mitt ?? (target ? { ...target, pop: 0 } : { x: 0, z: (zb.top + zb.bottom) / 2, pop: 0 });
  const plateCorner = project(0, 0, 0);

  // Home-plate dirt circle (13 ft radius), only the near half is visible.
  const dirt: [number, number, number][] = [];
  for (let a = 0; a <= 360; a += 10) {
    const rad = (a * Math.PI) / 180;
    dirt.push([13 * Math.cos(rad), Math.min(9, 13 * Math.sin(rad)), 0]);
  }

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="scene"
      role="img"
      aria-label={`Pitcher's view of ${hitter.name} at the plate`}
    >
      <defs>
        <linearGradient id="stands" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#070a10" />
          <stop offset="1" stopColor="#121826" />
        </linearGradient>
        <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1d1a18" />
          <stop offset="1" stopColor="#2c241e" />
        </linearGradient>
        <radialGradient id="clay" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#4a3a2e" />
          <stop offset="1" stopColor="#35291f" />
        </radialGradient>
        <radialGradient id="ballShade" cx="0.35" cy="0.35" r="0.7">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#d6d9df" />
        </radialGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" />
        </filter>
      </defs>

      {/* stands + backstop */}
      <rect width={VIEW_W} height={VIEW_H} fill="url(#stands)" />
      {Array.from({ length: 9 }, (_, i) => (
        <line key={i} x1={0} x2={VIEW_W} y1={40 + i * 19} y2={40 + i * 19} stroke="#ffffff" opacity={0.025} />
      ))}
      <rect x={0} y={214} width={VIEW_W} height={122} fill="#0f141d" />
      <rect x={0} y={212} width={VIEW_W} height={4} fill="#7aa2f7" opacity={0.35} />

      {/* ground */}
      <rect x={0} y={334} width={VIEW_W} height={VIEW_H - 334} fill="url(#ground)" />
      <polygon points={polygon(dirt)} fill="url(#clay)" />

      {/* foul lines + batter's boxes */}
      <g stroke="#e9e4da" strokeOpacity={0.55} fill="none" strokeWidth={2}>
        <line x1={plateCorner.sx} y1={plateCorner.sy} x2={plateCorner.sx - 900} y2={plateCorner.sy + 900} />
        <line x1={plateCorner.sx} y1={plateCorner.sy} x2={plateCorner.sx + 900} y2={plateCorner.sy + 900} />
        <polygon points={polygon([[1.21, -3, 0], [5.21, -3, 0], [5.21, 3, 0], [1.21, 3, 0]])} strokeWidth={1.5} />
        <polygon points={polygon([[-1.21, -3, 0], [-5.21, -3, 0], [-5.21, 3, 0], [-1.21, 3, 0]])} strokeWidth={1.5} />
      </g>
      <polygon
        points={polygon([[0.71, 0, 0], [-0.71, 0, 0], [-0.71, -0.71, 0], [0, -1.42, 0], [0.71, -0.71, 0]])}
        fill="#f4f1ea"
      />

      <UmpireFigure />
      <CatcherFigure />
      <Mitt x={mitt.x} z={mitt.z} pop={mitt.pop} />
      <HitterFigure bats={hitter.bats} swing={frame?.swing ?? 0} flinch={frame?.flinch ?? 0} />

      {/* strike zone + target grid */}
      <g pointerEvents="none">
        {aiming && (
          <polygon
            points={rectPts(grid.left, grid.right, grid.bottom, grid.top)}
            fill="#7aa2f7"
            fillOpacity={0.04}
            stroke="#7aa2f7"
            strokeOpacity={0.25}
            strokeDasharray="4 5"
          />
        )}
        {hoverCell && (
          <polygon
            points={rectPts(hoverCell.l, hoverCell.l + cw, hoverCell.b, hoverCell.b + ch)}
            fill="#7aa2f7"
            fillOpacity={0.14}
          />
        )}
        {[1, 2].map((i) => (
          <g key={i} stroke="#ffffff" strokeOpacity={aiming ? 0.18 : 0.08}>
            <polyline points={polygon([[zb.left + i * cw, 0, zb.bottom], [zb.left + i * cw, 0, zb.top]])} />
            <polyline points={polygon([[zb.left, 0, zb.bottom + i * ch], [zb.right, 0, zb.bottom + i * ch]])} />
          </g>
        ))}
        <polygon
          points={rectPts(zb.left, zb.right, zb.bottom, zb.top)}
          fill="none"
          stroke="#ffffff"
          strokeOpacity={aiming ? 0.7 : 0.35}
          strokeWidth={1.6}
        />

        {trails.map((t, i) => (
          <TrailView key={t.n} trail={t} latest={i === trails.length - 1 && !frame?.ball} />
        ))}

        {markers.map((m) => {
          const p = project(m.loc.x, 0, m.loc.z);
          return (
            <g key={m.n} transform={`translate(${p.sx},${p.sy})`}>
              <circle r={8.5} fill={CALL_COLORS[m.call]} fillOpacity={0.9} />
              <text y={3.6} textAnchor="middle" fontSize={10} fontWeight={700} fill="#0e1117">
                {m.n}
              </text>
            </g>
          );
        })}

        {target && aiming && <Crosshair loc={target} />}
      </g>

      {/* ghost ball: same pitch with no spin-induced movement */}
      {frame?.ghost && frame.ball && (
        <circle
          cx={frame.ghost.sx}
          cy={frame.ghost.sy}
          r={frame.ghost.r}
          fill="none"
          stroke={flightColor ?? "#ffffff"}
          strokeWidth={1.4}
          strokeDasharray="3 2.5"
          opacity={frame.ghost.opacity}
        />
      )}

      {/* ball */}
      {frame?.trail.map((t, i) => (
        <circle key={i} cx={t.sx} cy={t.sy} r={(frame.ball?.r ?? 3) * (0.8 - i * 0.2)} fill="#ffffff" opacity={0.18 - i * 0.05} />
      ))}
      {frame?.ball && (
        <g opacity={frame.ball.opacity}>
          <circle cx={frame.ball.sx} cy={frame.ball.sy} r={frame.ball.r * 1.6} fill="#ffffff" opacity={0.25} filter="url(#glow)" />
          <circle cx={frame.ball.sx} cy={frame.ball.sy} r={frame.ball.r} fill="url(#ballShade)" />
          {frame.ball.r > 6 && (
            <path
              d={`M${frame.ball.sx - frame.ball.r * 0.55},${frame.ball.sy - frame.ball.r * 0.6} q${frame.ball.r * 0.35},${frame.ball.r * 0.6} 0,${frame.ball.r * 1.2}`}
              stroke="#e05d5d"
              strokeWidth={1.2}
              fill="none"
            />
          )}
        </g>
      )}

      {/* click/hover capture over the target grid */}
      {aiming && (
        <polygon
          points={rectPts(grid.left, grid.right, grid.bottom, grid.top)}
          fill="transparent"
          style={{ cursor: "crosshair" }}
          onMouseMove={(e) => setHover(toWorld(e))}
          onMouseLeave={() => setHover(null)}
          onClick={(e) => {
            const w = toWorld(e);
            if (w) onAim(w);
          }}
        />
      )}
    </svg>
  );
}

function Crosshair({ loc }: { loc: Location }) {
  const p = project(loc.x, 0, loc.z);
  return (
    <g transform={`translate(${p.sx},${p.sy})`} className="crosshair">
      <circle r={11} fill="none" stroke="#7aa2f7" strokeWidth={2} />
      <circle r={2.5} fill="#7aa2f7" />
      <path d="M-18,0 L-13,0 M13,0 L18,0 M0,-18 L0,-13 M0,13 L0,18" stroke="#7aa2f7" strokeWidth={2} />
    </g>
  );
}

const toPoints = (pts: { sx: number; sy: number }[]) =>
  pts.map((p) => `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(" ");

/** A pitch's flight path; the latest one also shows its break. */
function TrailView({ trail, latest }: { trail: PitchTrail; latest: boolean }) {
  const end = trail.real[trail.real.length - 1];
  const ghostEnd = trail.ghost[trail.ghost.length - 1];
  const dx = end.sx - ghostEnd.sx;
  const dy = end.sy - ghostEnd.sy;
  const len = Math.hypot(dx, dy);
  // Label beside the arrow's midpoint (offset perpendicular to it).
  const ux = len ? dx / len : 0;
  const uy = len ? dy / len : 0;
  const labelX = ghostEnd.sx + dx / 2 - uy * 22;
  const labelY = ghostEnd.sy + dy / 2 + ux * 22;

  return (
    <g className="trail">
      <polyline
        points={toPoints(trail.real)}
        fill="none"
        stroke={trail.color}
        strokeWidth={latest ? 2 : 1.4}
        strokeLinecap="round"
        opacity={latest ? 0.75 : 0.3}
      />
      {latest && len > 4 && (
        <g className="break-arrow">
          <polyline
            points={toPoints(trail.ghost)}
            fill="none"
            stroke="#ffffff"
            strokeWidth={1.1}
            strokeDasharray="4 4"
            opacity={0.35}
          />
          <circle cx={ghostEnd.sx} cy={ghostEnd.sy} r={5} fill="none" stroke="#ffffff" strokeDasharray="2.5 2" opacity={0.7} />
          {/* Break: dotted black line from the no-spin spot to the actual pitch.
              A faint light band underneath keeps it readable on the dark scene. */}
          <line x1={ghostEnd.sx} y1={ghostEnd.sy} x2={end.sx} y2={end.sy}
            stroke="#ffffff" strokeOpacity={0.35} strokeWidth={4} strokeLinecap="round" />
          <line x1={ghostEnd.sx} y1={ghostEnd.sy} x2={end.sx} y2={end.sy}
            stroke="#000000" strokeWidth={2} strokeDasharray="0.1 4" strokeLinecap="round" />
          <g transform={`translate(${labelX},${labelY})`}>
            <rect x={-18} y={-9} width={36} height={16} rx={8} fill="#0e1117" opacity={0.85} />
            <text textAnchor="middle" y={3} fontSize={10} fontWeight={700} fill={trail.color}>
              {trail.breakIn} in
            </text>
          </g>
        </g>
      )}
    </g>
  );
}

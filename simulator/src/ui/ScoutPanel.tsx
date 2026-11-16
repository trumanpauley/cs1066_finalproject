/**
 * Side panel: the current batter's photo and PitchIQ scouting report, in
 * the same Quick / Standard / Detailed format as the Scout page. It follows
 * whoever is at the plate, so you can read the plan and then execute it.
 */

import { useEffect, useState } from "react";
import type { HitterProfile, ReportDepth, ReportRow } from "../engine";

const DEPTHS: ReportDepth[] = ["Quick", "Standard", "Detailed"];

export function ScoutPanel({ hitter, glossary }: { hitter: HitterProfile; glossary?: string }) {
  const r = hitter.report;
  const [depth, setDepth] = useState<ReportDepth>(r?.defaultDepth ?? "Standard");
  const [photoOk, setPhotoOk] = useState(true);
  useEffect(() => setPhotoOk(true), [hitter.id]);

  const initials = hitter.name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2);

  return (
    <aside className="scout-panel" aria-label={`Scouting report: ${hitter.name}`}>
      <div className="sp-head">
        {hitter.photo && photoOk ? (
          <img
            className="sp-photo"
            src={hitter.photo}
            alt={hitter.name}
            onError={() => setPhotoOk(false)}
          />
        ) : (
          <div className="sp-photo sp-initials" aria-hidden="true">
            {initials}
          </div>
        )}
        <div className="sp-id">
          <div className="sp-name">
            {r?.number ? `#${r.number} ` : ""}
            {hitter.name}
          </div>
          <div className="sp-meta">
            {[r?.meta, `Bats: ${r?.bats ?? hitter.bats}`].filter(Boolean).join(" · ")}
          </div>
          {r && <span className={`sp-badge sp-badge-${r.threat.toLowerCase()}`}>{r.threat} threat</span>}
        </div>
      </div>

      <div className="sp-title">PitchIQ scouting report</div>

      {!r ? (
        <div className="sp-empty">
          <p>{hitter.blurb || "No scouting report for this hitter."}</p>
          <p className="sp-fine">{hitter.source.label}. Load a lineup on the Simulate page for real reports.</p>
        </div>
      ) : (
        <>
          <div className="sp-depth" role="radiogroup" aria-label="Report depth">
            {DEPTHS.map((d) => (
              <button
                key={d}
                role="radio"
                aria-checked={depth === d}
                className={depth === d ? "on" : ""}
                onClick={() => setDepth(d)}
              >
                {d}
              </button>
            ))}
          </div>

          <div className="sp-metrics">
            {r.metrics.map((m) => (
              <div key={m.label} className="sp-metric">
                <span>{m.label}</span>
                <b>{m.value}</b>
              </div>
            ))}
          </div>

          {depth !== "Quick" && <p className="sp-summary">{r.summary}</p>}

          <div className="sp-rec">
            <span className="sp-rec-label">How to attack</span>
            {depth === "Quick" && <p>{r.quick}</p>}
            {depth === "Standard" && <p>{r.standard}</p>}
            {depth === "Detailed" && (
              <ul>
                {r.detailed.map((l, i) => (
                  <li key={i}>
                    {l.label && <b>{l.label}: </b>}
                    {l.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
          {!r.hasArsenal && (
            <p className="sp-fine">Add your pitches on My Arsenal to turn these tendencies into a game plan.</p>
          )}

          {depth !== "Quick" && r.arsenalRows.length > 0 && (
            <ReportTable
              title={`vs your arsenal · his results vs ${r.handLabel}`}
              rows={depth === "Detailed" ? r.arsenalRowsFull : r.arsenalRows}
            />
          )}
          {(depth === "Detailed" || (depth === "Standard" && !r.hasArsenal)) && r.tendencyRows.length > 0 && (
            <ReportTable title={`vs every pitch type · from ${r.handLabel}`} rows={r.tendencyRows} />
          )}
          {depth !== "Quick" && <p className="sp-fine">Zone heatmaps are on the Scout page.</p>}
          {glossary && <p className="sp-fine sp-glossary">{glossary}</p>}
        </>
      )}
    </aside>
  );
}

function fmt(key: string, v: string | number | null): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "string") return v;
  if (key.startsWith("xwOBA")) return v.toFixed(3).replace(/^0/, "");
  if (key === "RV/100") return (v > 0 ? "+" : "") + v.toFixed(1);
  if (key.endsWith("%")) return `${Math.round(v)}%`;
  return String(v);
}

function ReportTable({ title, rows }: { title: string; rows: ReportRow[] }) {
  const cols = Object.keys(rows[0] ?? {});
  return (
    <div className="sp-table-wrap">
      <div className="sp-table-title">{title}</div>
      <table className="sp-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{fmt(c, row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

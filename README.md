# ⚾ PitchIQ — Baseball Scouting for Pitchers

**CS 1066 Final Project · V0.7 (Game Plan + Simulator)**

PitchIQ helps a pitcher prepare for an opponent: pick an MLB team, get a game
plan for every hitter built from public Baseball Savant data and your own
arsenal, then practice it against those hitters in the Pitch Simulator.
Everything is computed by the program itself — no LLM — so results are
deterministic and free to run.

## Pages

Navigation runs along the top of the app, in the order of the main flow:

- **Game Plan** (home) — pick an MLB team and get a plan for every hitter on
  the active roster, most dangerous first; then jump straight to Simulate
- **Simulate** — face that team's lineup batter by batter in the Pitch
  Simulator, with each hitter driven by his own Savant data (see below)
- **Hitter Lookup** — search any MLB hitter and get his Savant tendencies plus
  a plan built around your arsenal
- **My Arsenal** — pitcher profile, report uploads, pitch arsenal, and
  movement chart

## Features

- **PDF extraction** — three supported report formats, detected automatically:
  - *Pitcher process reports*: pitch types, velocity, usage, spin efficiency,
    IVB/HB, and report dates — apply directly to an editable My Arsenal profile
  - *Opponent statistical reports*: hitters, handedness, RHP/LHP splits, and
    all stat columns, with sample sizes (P) and missing values ("-") preserved
  - *Opponent heatmap reports*: hitter/handedness per page, with the original
    heatmaps displayed as rendered pages (values are never re-invented)
- **Extraction review** — the Scouting Library shows extracted hitters,
  statistics, source pages, and extraction errors; every table is editable so
  you can correct values before analysis
- **Pitcher Profile** — throwing hand, editable pitch arsenal (type, velocity,
  usage, notes), and self-scouting notes (strengths / weaknesses / preferences)
- **Pitch Movement Chart** — interactive HB vs. IVB plot (catcher's view) with
  per-pitch movement inputs that update the chart live
- **Report Uploads** — separate upload cards for your own pitching report and
  opponent scouting reports, with filename/size/status feedback
- **Example Scouting Report** — fictional opposing lineup with per-hitter stat
  tables (TruMedia-style schema) and pitching recommendations

## Simulate (Pitch Simulator)

Pick an opponent on **Simulate**, choose the hitters in batting order, and
click **Load lineup**. Each hitter's rates come from his own Baseball Savant
pitches against your throwing hand (`pitchiq/mlb/sim_profile.py`): zone swing,
chase, zone/out-of-zone contact, and foul rates; per-pitch-family
multipliers (fastball / breaking / offspeed); count tendencies; and exit
velocity, launch angle, and spray direction. Small samples are shrunk toward
league-wide priors. Your pitches come from **My Arsenal** (a sample RHP is
used until you add some). After each plate appearance, **Next batter**
brings up the next hitter; outs carry over and three outs retire the side.

An interactive at-bat from the pitcher's point of view. Choose a pitch
(four-seam, slider, changeup), click anywhere on the 5×5 target grid (inner
3×3 = strike zone, outer ring = chase area), and throw. The pitch flies with
its own movement, the hitter reacts, and the count updates until a strikeout,
walk, HBP, or ball in play. **Why?** shows the model's actual probabilities.

Keys: `1`–`3` pick a pitch, `Space` throws (or faces the hitter again).

With no lineup loaded, the simulator falls back to two **synthetic demo
hitters** (not real MLB data), labeled "Demo data" in the UI; Savant-driven
hitters are labeled "Savant".

How a pitch is simulated (`simulator/src/engine/`, pure TypeScript):

| Step | Module | What it does |
|------|--------|--------------|
| A | `execution.ts` | Target ≠ actual: location scatters around the aim point by the pitch's command (SD in feet) |
| B | `swing.ts` | P(swing) blends chase and zone-swing rates by depth in the zone, then pitch-type, platoon, and count adjustments |
| C | `contact.ts` | Given a swing: P(whiff), P(foul), P(in play) — always sums to 1 |
| D | `battedBall.ts` | Exit velocity, launch angle, spray angle → distance → a hit *probability*, then a sampled result |
| — | `atBat.ts` | Count state machine: fouls with two strikes, walks, strikeouts, HBP |

Randomness comes from a seedable RNG (`rng.ts`), so tests are reproducible;
open the dev server with `?seed=123` to replay a sequence. Hitter and pitcher
data load through `simulator/src/data/loaders.ts`, which validates profiles
and can accept data injected by the app (`window.PITCHIQ_DATA`) — the plug-in
point for scouting-report or API data in later phases.

The field and pitch animation are rendered with **Phaser 4** (WebGL): ball
glow and ground shadow, mitt-pop dust, contact sparks, dirt, camera shake on
95+ mph fastballs, and a slow-motion **Replay** (key `R`). Static art (field,
crowd, catcher, hitter) is vector SVG turned into Phaser textures
(`simulator/src/ui/textures.ts`); the scene lives in `simulator/src/game/`.
React keeps the scoreboard, pitch menu, and result panel.

The simulator is a Vite + React + TypeScript app compiled to one HTML file,
`pitchiq/static/simulator.html`, which is committed so the Streamlit app runs
without Node. To work on it (Node 20+):

```bash
cd simulator
npm install
npm run dev      # standalone at http://localhost:5173
npm test         # engine tests (Vitest)
npm run build    # rebuilds pitchiq/static/simulator.html
```

Roadmap: Phase 2 adds hitter heatmaps, richer command profiles, and batted-ball
visualization; Phase 3 connects real scouting reports, saves practice
sessions, and compares strategies.

## Quick Start

```bash
# 1. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 2. Launch the app
streamlit run app.py
```

Streamlit will open the app in your browser (default: http://localhost:8501).

## Project Structure

```
app.py                        # Entry point: page config, top navigation, footer
assets/
└── logo.svg                  # Logo
pitchiq/
├── navigation.py             # Page registry so pages can link to each other
├── config.py                 # Constants: pitch types, analysis modes, limits
├── state.py                  # Session-state initialization & helpers
├── styles.py                 # Minimal dark-theme CSS
├── data/
│   └── sample_data.py        # Fictional hitters + default arsenal (demo data)
├── extraction/
│   ├── extract.py            # Format detection, dispatch, page rendering
│   ├── pitcher_report.py     # Sockeye pitcher process reports
│   ├── opponent_stats.py     # TruMedia statistical grids (coordinate-based)
│   └── heatmap_report.py     # TruMedia heatmap pages (identify, don't invent)
├── services/
│   ├── pdf_service.py        # Upload validation + extraction entry point
│   └── report_service.py     # Report assembly
├── static/
│   └── simulator.html        # Built Pitch Simulator (from simulator/)
└── ui/
    ├── team_matchup.py       # Game Plan page (home)
    ├── scout.py              # Hitter Lookup page
    ├── hitter_card.py        # Shared hitter card + profile loading
    ├── pitcher_profile.py    # Arsenal editor, movement chart, report import
    ├── uploads.py            # Dual PDF upload cards + extraction status
    ├── extracted.py          # Extraction review/correction UI
    ├── scouting_report.py    # Hitter cards, stat tables, recommendations
    └── simulator.py          # Embeds the built Pitch Simulator
simulator/                    # Pitch Simulator source (Vite + React + TS)
├── src/engine/               # Simulation engine + Vitest tests (no UI code)
├── src/data/                 # Sample pitcher/hitters (synthetic) + loaders
├── src/game/                 # Phaser scene + React host
└── src/ui/                   # Flight math, projection, textures, HUD
tests/
└── test_extraction.py        # Extraction vs. original-PDF value tests
```

## Tests

```bash
python -m pytest tests/ -v
```

The tests compare extracted values against the original reference PDFs in
`journals/Scouting_Reports/` and skip automatically when those files are
absent.

## Data privacy

Scouting PDFs and extracted data stay local: `journals/Scouting_Reports/`,
`*.pdf`, and extracted output are gitignored and must never be committed.
Uploaded files are held in session memory only.

## Roadmap

| Version | Milestone |
|---------|-----------|
| V0.1 | ✅ Streamlit UI foundation |
| V0.2 | ✅ Dark theme, upload cards, interactive pitch-movement chart |
| V0.3 | ✅ Chat-style scouting workspace homepage + page navigation |
| V0.4 | ✅ Minimal ChatGPT-style redesign |
| V0.5 | ✅ PDF extraction for pitcher, stats, and heatmap reports |
| V0.6 | ✅ MLB hitters from Baseball Savant, Team Matchup, Pitch Simulator |
| **V0.7** | ✅ Top navigation built around Game Plan → Simulate; chatbot removed (this release) |
| Next | Accounts with Supabase and a hosted, shareable link |

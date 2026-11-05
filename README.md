# ⚾ PitchIQ — AI Baseball Scouting Reports

**CS 1066 Final Project · V0.5 (PDF Extraction)**

PitchIQ is a ChatGPT-style baseball scouting assistant: ask natural-language
questions about hitters ("I throw a four-seam, slider, and changeup — how
should I pitch to their cleanup hitter?") and get a conversational scouting
report built around your arsenal.

**V0.5 scope:** the minimal chat UI plus reliable PDF extraction for three
real report formats. RAG and LLM-generated reports arrive in future
iterations — the code is structured so they plug in without a rewrite.

## Pages

- **Scout** (homepage) — centered chat prompt; ask about any hitter with no
  profile or uploads required. Analysis depth (Quick / Standard / Detailed)
  and PDF attachments live right in the composer. Each response reserves
  space for future heatmaps, statistics, and evidence.
- **My Arsenal** — pitcher profile, pitch arsenal editor, and movement chart
- **Scouting Library** — report uploads and the example scouting report

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
- **Scouting chat** — natural-language questions, per-report analysis depth in
  the composer, optional PDF attachments from the chat, demo-labeled responses
  with evidence/context expanders
- **Pitcher Profile** — throwing hand, editable pitch arsenal (type, velocity,
  usage, notes), and self-scouting notes (strengths / weaknesses / preferences)
- **Pitch Movement Chart** — interactive HB vs. IVB plot (catcher's view) with
  per-pitch movement inputs that update the chart live
- **Report Uploads** — separate upload cards for your own pitching report and
  opponent scouting reports, with filename/size/status feedback
- **Example Scouting Report** — fictional opposing lineup with per-hitter stat
  tables (TruMedia-style schema) and pitching recommendations

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
app.py                        # Entry point: page config, navigation, footer
assets/
└── logo.svg                  # Sidebar logo
pitchiq/
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
│   └── report_service.py     # Report + answer assembly; future: RAG + LLM
└── ui/
    ├── scout.py              # Chat homepage (composer, messages, evidence)
    ├── pitcher_profile.py    # Arsenal editor, movement chart, report import
    ├── uploads.py            # Dual PDF upload cards + extraction status
    ├── extracted.py          # Extraction review/correction UI
    └── scouting_report.py    # Hitter cards, stat tables, recommendations
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
| **V0.5** | ✅ PDF extraction for pitcher, stats, and heatmap reports (this release) |
| V0.6 | RAG over extracted scouting data |
| V1.0 | LLM-generated personalized scouting reports |

### How future versions plug in

- `pitchiq/extraction/` is modular: each report format has its own parser and
  a detector rule in `extract.py`; new formats add a module + rule. The
  structured dict output is the contract RAG indexing will consume.
- `report_service.answer_scouting_question()` powers the Scout workspace and
  already receives the question, pitcher profile, uploaded-report metadata, and
  depth — its internals swap from sample data to RAG retrieval + an LLM call.
- `report_service.generate_scouting_report()` keeps its signature; its internals
  swap from sample data to RAG + LLM output.
- The UI renders whatever those services return, so no interface rewrite is needed.

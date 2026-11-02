# ⚾ PitchIQ — AI Baseball Scouting Reports

**CS 1066 Final Project · V0.3 (Scouting Workspace)**

PitchIQ helps pitchers prepare for opponents: enter your pitching profile, upload
scouting reports, and get a personalized game plan for every hitter in the
opposing lineup.

**V0.3 scope:** a polished, fully functional Streamlit interface centered on a
ChatGPT-style scouting workspace, with sample data, a consistent dark theme,
and an interactive pitch-movement chart. PDF data extraction, RAG, and
LLM-generated reports arrive in future iterations — the code is structured so
they plug in without a rewrite.

## Pages

- 🎯 **Scout** (homepage) — chat-style workspace: ask scouting questions,
  generate game plans at Quick/Standard/Detailed depth, and see exactly which
  pitcher profile and reports provide the context for each answer
- 🧢 **My Arsenal** — pitcher profile, pitch arsenal editor, and movement chart
- 📚 **Scouting Library** — report uploads and the example scouting report

## Features

- 💬 **Scouting Workspace** — chat interface with quick prompts, per-report
  analysis-depth control, context chips, and a conversation history
- 🧢 **Pitcher Profile** — throwing hand, editable pitch arsenal (type, velocity,
  usage, notes), and self-scouting notes (strengths / weaknesses / preferences)
- 📈 **Pitch Movement Chart** — interactive HB vs. IVB plot (catcher's view) with
  per-pitch movement inputs that update the chart live
- 📄 **Report Uploads** — separate upload cards for your own pitching report and
  opponent scouting reports, with filename/size/status feedback
- 📊 **Example Scouting Report** — fictional opposing lineup with per-hitter stat
  tables (TruMedia-style schema) and pitching recommendations
- 🎚️ **Analysis Depth** — modern Quick / Standard / Detailed selector next to the
  scouting prompt (and on the example report), adjustable per report

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
app.py                        # Entry point: page config, navigation, hero, footer
pitchiq/
├── config.py                 # Constants: pitch types, analysis modes, limits
├── state.py                  # Session-state initialization & helpers
├── styles.py                 # Custom CSS theme
├── data/
│   └── sample_data.py        # Fictional hitters + default arsenal (demo data)
├── services/
│   ├── pdf_service.py        # Upload validation; future: real PDF extraction
│   └── report_service.py     # Report + answer assembly; future: RAG + LLM
└── ui/
    ├── scout.py              # Scouting workspace (chat homepage)
    ├── sidebar.py            # Branding and session status
    ├── pitcher_profile.py    # Arsenal editor & movement chart
    ├── uploads.py            # Dual PDF upload cards with status feedback
    └── scouting_report.py    # Hitter cards, stat tables, recommendations
```

## Roadmap

| Version | Milestone |
|---------|-----------|
| V0.1 | ✅ Streamlit UI foundation |
| V0.2 | ✅ Dark theme, upload cards, interactive pitch-movement chart |
| **V0.3** | ✅ Chat-style scouting workspace homepage + page navigation (this release) |
| V0.4 | PDF extraction of pitcher/opponent report data |
| V0.5 | RAG over extracted scouting data |
| V1.0 | LLM-generated personalized scouting reports |

### How future versions plug in

- `pdf_service.extract_report_data()` is the stub where PDF parsing lands —
  it returns the same hitter/arsenal schema the UI already renders.
- `report_service.answer_scouting_question()` powers the Scout workspace and
  already receives the question, pitcher profile, uploaded-report metadata, and
  depth — its internals swap from sample data to RAG retrieval + an LLM call.
- `report_service.generate_scouting_report()` keeps its signature; its internals
  swap from sample data to RAG + LLM output.
- The UI renders whatever those services return, so no interface rewrite is needed.

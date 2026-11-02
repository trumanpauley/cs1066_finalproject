# ⚾ PitchIQ — AI Baseball Scouting Reports

**CS 1066 Final Project · V0.2 (Interactive UI)**

PitchIQ helps pitchers prepare for opponents: enter your pitching profile, upload
scouting reports, and get a personalized game plan for every hitter in the
opposing lineup.

**V0.2 scope:** a polished, fully functional Streamlit interface with sample
data, a consistent dark theme, and an interactive pitch-movement chart. PDF
data extraction, RAG, and LLM-generated reports arrive in future iterations —
the code is structured so they plug in without a rewrite.

## Features

- 🧢 **Pitcher Profile** — throwing hand, editable pitch arsenal (type, velocity,
  usage, notes), and self-scouting notes (strengths / weaknesses / preferences)
- 📈 **Pitch Movement Chart** — interactive HB vs. IVB plot (catcher's view) with
  per-pitch movement inputs that update the chart live
- 📄 **Report Uploads** — separate upload cards for your own pitching report and
  opponent scouting reports, with filename/size/status feedback
- 📊 **Example Scouting Report** — fictional opposing lineup with per-hitter stat
  tables (TruMedia-style schema) and pitching recommendations
- 🎚️ **Analysis Depth** — switch between Quick, Standard, and Detailed modes to
  change how much detail the report shows

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
app.py                        # Entry point: page config, hero, tab layout
pitchiq/
├── config.py                 # Constants: pitch types, analysis modes, limits
├── state.py                  # Session-state initialization & helpers
├── styles.py                 # Custom CSS theme
├── data/
│   └── sample_data.py        # Fictional hitters + default arsenal (V0.1 demo data)
├── services/
│   ├── pdf_service.py        # Upload validation; future: real PDF extraction
│   └── report_service.py     # Report assembly; future: RAG + LLM generation
└── ui/
    ├── sidebar.py            # Branding, analysis-depth control, session status
    ├── pitcher_profile.py    # Profile form & arsenal editor
    ├── uploads.py            # Dual PDF uploaders with status feedback
    └── scouting_report.py    # Hitter cards, stat tables, recommendations
```

## Roadmap

| Version | Milestone |
|---------|-----------|
| V0.1 | ✅ Streamlit UI foundation |
| **V0.2** | ✅ Dark theme, upload cards, interactive pitch-movement chart (this release) |
| V0.3 | PDF extraction of pitcher/opponent report data |
| V0.4 | RAG over extracted scouting data |
| V1.0 | LLM-generated personalized scouting reports |

### How future versions plug in

- `pdf_service.extract_report_data()` is the stub where PDF parsing lands —
  it returns the same hitter/arsenal schema the UI already renders.
- `report_service.generate_scouting_report()` keeps its signature; its internals
  swap from sample data to RAG + LLM output.
- The UI renders whatever those services return, so no interface rewrite is needed.

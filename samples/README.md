# Sample data (fictional)

**Casey Marlow is a made-up left-handed pitcher.** These files exist so the app
can be tested end to end — including with free AI tiers that may use inputs
for training — without uploading confidential team reports.

| File | What it tests |
|---|---|
| `sample_outing_2026-07-12.pdf`, `sample_outing_2026-07-24.pdf` | Outing reports in the pitching-process-report layout the app parses (4-seam, sinker, changeup, curveball) |
| `sample_pitching_notes.pdf` | A notes PDF (pitching identity, how he throws each pitch, coach's notes) — saved as notes, searched by the chatbot |

To try it: on **My Arsenal**, set the throwing hand to **Left (LHP)** and upload
all three files; then ask **Ask PitchIQ** something like "How should I pitch to
the Dodgers?".

Regenerate or edit them with `python scripts/make_sample_data.py`.

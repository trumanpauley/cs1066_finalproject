"""Application-wide constants and configuration for PitchIQ."""

APP_NAME = "PitchIQ"
APP_TAGLINE = "AI-Powered Baseball Scouting Reports"
APP_ICON = "⚾"
VERSION = "0.4.0"

# Pitch types a pitcher can add to their arsenal (TruMedia-style taxonomy).
PITCH_TYPES = [
    "Fastball (4-Seam)",
    "Sinker (2-Seam)",
    "Cutter",
    "Slider",
    "Sweeper",
    "Curveball",
    "ChangeUp",
    "Splitter",
    "Knuckleball",
]

THROWING_HANDS = ["Right (RHP)", "Left (LHP)"]

# Marker colors for the pitch-movement chart (one per pitch type).
PITCH_COLORS = {
    "Fastball (4-Seam)": "#ff6b4a",
    "Sinker (2-Seam)": "#f3a712",
    "Cutter": "#b388ff",
    "Slider": "#00b4d8",
    "Sweeper": "#2ec4b6",
    "Curveball": "#4895ef",
    "ChangeUp": "#80ed99",
    "Splitter": "#f15bb5",
    "Knuckleball": "#adb5bd",
}

# Movement chart bounds (inches of break).
MOVEMENT_RANGE = 25.0

# Analysis depth options surfaced in the sidebar.
ANALYSIS_MODES = ["Quick", "Standard", "Detailed"]

ANALYSIS_MODE_DESCRIPTIONS = {
    "Quick": "A fast, at-a-glance game plan — one key recommendation per hitter.",
    "Standard": "A balanced report — pitch-by-pitch tendencies and sequencing notes.",
    "Detailed": "A deep dive — full stat tables, count-specific plans, and situational notes.",
}

# Accepted upload formats (V0.1 accepts PDFs only).
ACCEPTED_UPLOAD_TYPES = ["pdf"]
MAX_UPLOAD_MB = 25

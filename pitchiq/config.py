"""Application-wide constants and configuration for PitchIQ."""

APP_NAME = "PitchIQ"
APP_TAGLINE = "MLB Hitter Scouting"
APP_ICON = "⚾"
VERSION = "0.6.0"

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

# Scouting chatbot (Claude API). Change CHAT_MODEL to "claude-sonnet-5-5" to
# halve the cost per report; prices below must match the model you pick.
CHAT_MODEL = "claude-opus-5-5"
CHAT_EFFORT = "medium"      # low | medium | high — how hard the model thinks before answering
CHAT_MAX_TOKENS = 64000     # ceiling only; you pay for tokens actually generated
CHAT_PRICES = {             # $ per 1M tokens, Claude Opus 5.5 list price
    "input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_read": 0.20,
}

# Which provider answers chat questions: "auto" uses Claude when an
# ANTHROPIC_API_KEY is set, otherwise Gemini when a GEMINI_API_KEY is set.
# Force one with "anthropic" or "gemini".
CHAT_PROVIDER = "auto"

# Google Gemini (Interactions API). All models below are on the free tier.
# Free-tier inputs may be used by Google to improve its products — test with
# the fictional samples/ files, not confidential team reports.
# Tried in order: if one is overloaded (503) or out of free quota (429), the
# next answers. gemini-3.8-flash is stronger but was returning "high demand"
# 503s in November 2026; put it first again once it's reliable.
GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite")
GEMINI_MODEL = GEMINI_MODELS[0]
GEMINI_TIMEOUT_MS = 60_000          # a request that takes longer fails instead of hanging
# How much the model reasons before answering. "medium" spent ~5,900 hidden
# thinking tokens on a Dodgers report (most of a 44 s wait); "low" is plenty
# for writing up numbers it's already been given.
GEMINI_THINKING = "low"             # minimal | low | medium | high
GEMINI_MAX_OUTPUT_TOKENS = 16000
GEMINI_FREE_TIER = True             # shows "free tier" and $0.00 instead of a cost estimate

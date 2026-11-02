"""Sample/demo data for PitchIQ V0.1.

Fictional hitters and canned recommendations that mirror the real TruMedia
report schema (P, FPSwing%, InZoneWhiff%, Pre2K-Ch%, 2K-Ch%, SoftCt%,
Ground%, AVG, ISO, wOBA). In future iterations this module is replaced by
real data extracted from uploaded opponent PDFs.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Default pitch arsenal (pre-filled example a user can edit or clear).
# ---------------------------------------------------------------------------
DEFAULT_ARSENAL = [
    {"pitch": "Sweeper", "velo_low": 80, "velo_high": 84, "usage_pct": 38, "ivb": -4.1, "hb": -9.2, "notes": "Big horizontal break; best swing-and-miss pitch."},
    {"pitch": "Fastball (4-Seam)", "velo_low": 90, "velo_high": 94, "usage_pct": 31, "ivb": 18.0, "hb": 5.3, "notes": "Good ride up in the zone."},
    {"pitch": "Cutter", "velo_low": 88, "velo_high": 91, "usage_pct": 21, "ivb": 9.8, "hb": -0.8, "notes": "In on lefties' hands; steals strikes."},
    {"pitch": "Slider", "velo_low": 84, "velo_high": 88, "usage_pct": 10, "ivb": -0.2, "hb": -0.3, "notes": "Shorter/harder than sweeper; chase pitch."},
]

# ---------------------------------------------------------------------------
# Fictional opponent hitters (names invented; stat schema mirrors TruMedia).
# Each hitter: profile info + per-pitch-type rows + canned recommendations
# keyed by analysis mode.
# ---------------------------------------------------------------------------
STAT_COLUMNS = [
    "Pitch", "P", "FPSwing%", "InZoneWhiff%", "Pre2K-Ch%", "2K-Ch%",
    "SoftCt%", "Ground%", "AVG", "ISO", "wOBA",
]

SAMPLE_HITTERS = [
    {
        "number": 12,
        "name": "Dax Carver",
        "bats": "R",
        "threat": "High",
        "summary": "Aggressive first-pitch fastball hunter with plus pull-side power.",
        "stats": [
            {"Pitch": "Fastball", "P": 142, "FPSwing%": 48.0, "InZoneWhiff%": 11.0, "Pre2K-Ch%": 22.0, "2K-Ch%": 30.0, "SoftCt%": 10.0, "Ground%": 32.0, "AVG": 0.318, "ISO": 0.270, "wOBA": 0.412},
            {"Pitch": "Slider", "P": 88, "FPSwing%": 25.0, "InZoneWhiff%": 34.0, "Pre2K-Ch%": 28.0, "2K-Ch%": 41.0, "SoftCt%": 19.0, "Ground%": 51.0, "AVG": 0.188, "ISO": 0.063, "wOBA": 0.244},
            {"Pitch": "ChangeUp", "P": 46, "FPSwing%": 30.0, "InZoneWhiff%": 26.0, "Pre2K-Ch%": 31.0, "2K-Ch%": 38.0, "SoftCt%": 17.0, "Ground%": 58.0, "AVG": 0.214, "ISO": 0.071, "wOBA": 0.262},
        ],
        "recommendations": {
            "Quick": "Never groove a first-pitch fastball — start him with spin away.",
            "Standard": "Start with sliders/changeups low-away to steal strike one, then expand with two strikes. Fastballs only up and out of the nitro zone — he slugs .588 on heaters in the zone.",
            "Detailed": "0-0: slider away (25% FPSwing on soft stuff vs 48% on FB). Ahead in count: climb the ladder above the zone. 2K: he chases 41% on sliders — bury it glove-side. Avoid: middle-in fastballs at any count (.270 ISO). Ground-ball option: changeup down gets 58% grounders if you need a double play.",
        },
    },
    {
        "number": 7,
        "name": "Rio Maldonado",
        "bats": "L",
        "threat": "Medium",
        "summary": "Patient lefty with a good eye; struggles vs. soft stuff from same side.",
        "stats": [
            {"Pitch": "Fastball", "P": 120, "FPSwing%": 18.0, "InZoneWhiff%": 15.0, "Pre2K-Ch%": 12.0, "2K-Ch%": 24.0, "SoftCt%": 14.0, "Ground%": 40.0, "AVG": 0.276, "ISO": 0.138, "wOBA": 0.351},
            {"Pitch": "Sweeper", "P": 64, "FPSwing%": 16.0, "InZoneWhiff%": 42.0, "Pre2K-Ch%": 18.0, "2K-Ch%": 35.0, "SoftCt%": 24.0, "Ground%": 47.0, "AVG": 0.141, "ISO": 0.047, "wOBA": 0.198},
            {"Pitch": "Curveball", "P": 41, "FPSwing%": 12.0, "InZoneWhiff%": 29.0, "Pre2K-Ch%": 14.0, "2K-Ch%": 27.0, "SoftCt%": 21.0, "Ground%": 55.0, "AVG": 0.179, "ISO": 0.036, "wOBA": 0.221},
        ],
        "recommendations": {
            "Quick": "Pound the zone early — he takes strike one 82% of the time.",
            "Standard": "Get ahead with in-zone fastballs/cutters (he rarely swings early), then finish with sweepers — 42% in-zone whiff. Don't waste pitches; he won't chase before two strikes.",
            "Detailed": "0-0: attack the zone, any pitch (18% FPSwing). 0-1/0-2: sweeper down-and-in to a lefty is the putaway (42% InZoneWhiff, .198 wOBA). He only chases 24-35% even at 2K, so finish in the zone's edges rather than bouncing pitches. Two-strike curveball is a secondary option (55% Ground%).",
        },
    },
    {
        "number": 23,
        "name": "Boone Whitaker",
        "bats": "S",
        "threat": "Medium",
        "summary": "Switch hitter; chases breaking balls early, dangerous once ahead.",
        "stats": [
            {"Pitch": "Fastball", "P": 150, "FPSwing%": 35.0, "InZoneWhiff%": 18.0, "Pre2K-Ch%": 20.0, "2K-Ch%": 28.0, "SoftCt%": 12.0, "Ground%": 38.0, "AVG": 0.290, "ISO": 0.161, "wOBA": 0.362},
            {"Pitch": "Cutter", "P": 58, "FPSwing%": 31.0, "InZoneWhiff%": 22.0, "Pre2K-Ch%": 33.0, "2K-Ch%": 37.0, "SoftCt%": 22.0, "Ground%": 49.0, "AVG": 0.222, "ISO": 0.089, "wOBA": 0.274},
            {"Pitch": "Slider", "P": 72, "FPSwing%": 28.0, "InZoneWhiff%": 30.0, "Pre2K-Ch%": 39.0, "2K-Ch%": 44.0, "SoftCt%": 18.0, "Ground%": 52.0, "AVG": 0.164, "ISO": 0.055, "wOBA": 0.213},
        ],
        "recommendations": {
            "Quick": "Breaking balls off the plate — he chases 39% before two strikes.",
            "Standard": "Spin early and often: he expands on sliders in every count (39% Pre2K chase, 44% at 2K). Cutters in on the hands produce weak contact. Keep fastballs out of the heart once behind.",
            "Detailed": "0-0: slider just off the edge — near-40% chase rate makes free strikes likely. Behind in count: cutter on the hands (22% SoftCt). 2K: slider below the zone is the finisher (.213 wOBA, 44% chase). Caution: if he reaches a hitter's count, fastball damage jumps (.362 wOBA) — pitch backwards instead.",
        },
    },
    {
        "number": 31,
        "name": "Cal Reyes-Ozuna",
        "bats": "L",
        "threat": "Low",
        "summary": "Contact-first lefty; minimal power but puts everything in play.",
        "stats": [
            {"Pitch": "Fastball", "P": 98, "FPSwing%": 27.0, "InZoneWhiff%": 9.0, "Pre2K-Ch%": 25.0, "2K-Ch%": 33.0, "SoftCt%": 26.0, "Ground%": 57.0, "AVG": 0.252, "ISO": 0.054, "wOBA": 0.288},
            {"Pitch": "Sinker", "P": 66, "FPSwing%": 29.0, "InZoneWhiff%": 7.0, "Pre2K-Ch%": 27.0, "2K-Ch%": 36.0, "SoftCt%": 30.0, "Ground%": 66.0, "AVG": 0.231, "ISO": 0.031, "wOBA": 0.259},
            {"Pitch": "ChangeUp", "P": 39, "FPSwing%": 24.0, "InZoneWhiff%": 21.0, "Pre2K-Ch%": 30.0, "2K-Ch%": 42.0, "SoftCt%": 28.0, "Ground%": 61.0, "AVG": 0.194, "ISO": 0.028, "wOBA": 0.230},
        ],
        "recommendations": {
            "Quick": "Attack the zone — worst-case outcome is a single.",
            "Standard": "Fill the zone with fastballs/sinkers and let the defense work (57-66% ground-ball rates, .031-.054 ISO). Changeup at 2K gets a 42% chase if you want the strikeout.",
            "Detailed": "Challenge him everywhere — only 9% in-zone whiff on fastballs but 26% soft contact and almost zero power (.288 wOBA ceiling). Sinker down produces 66% grounders: ideal with runners on. Save your best breaking balls for the middle of the order; expend minimum pitches here.",
        },
    },
]

# ---------------------------------------------------------------------------
# Mode-level placeholder content shown above the hitter cards.
# ---------------------------------------------------------------------------
MODE_PREVIEWS = {
    "Quick": {
        "title": "Quick Game Plan",
        "body": "One actionable takeaway per hitter — designed to be read in the dugout between innings.",
        "sections": ["Top-line recommendation per hitter"],
    },
    "Standard": {
        "title": "Standard Scouting Report",
        "body": "Pitch-by-pitch tendencies with sequencing guidance — the everyday pregame report.",
        "sections": ["Recommendation per hitter", "Key stat table per hitter"],
    },
    "Detailed": {
        "title": "Detailed Scouting Dossier",
        "body": "Count-specific plans, situational notes, and full stat tables — maximum preparation.",
        "sections": ["Count-by-count plan", "Full stat table", "Situational notes", "Threat assessment"],
    },
}

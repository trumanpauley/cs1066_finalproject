"""Public MLB data sources: MLB Stats API (teams/rosters) and Baseball Savant.

Savant's Statcast search has an official CSV export; we request one hitter's
regular-season pitches at a time and cache the CSV on disk so each hitter is
downloaded once. Data is for personal, non-commercial use (MLB terms).
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import requests

STATS_API = "https://statsapi.mlb.com/api/v1"
SAVANT_CSV = "https://baseballsavant.mlb.com/statcast_search/csv"
HEADERS = {"User-Agent": "PitchIQ student scouting project"}
TIMEOUT = 60

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "savant_cache"


def list_teams(season: int) -> list[dict]:
    """All MLB teams for a season, sorted by name."""
    resp = requests.get(f"{STATS_API}/teams", params={"sportId": 1, "season": season},
                        headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    teams = [
        {"id": t["id"], "name": t["name"], "abbreviation": t.get("abbreviation", ""),
         "nickname": t.get("teamName", ""),        # "Dodgers"
         "location": t.get("locationName", "")}   # "Los Angeles"
        for t in resp.json()["teams"]
    ]
    return sorted(teams, key=lambda t: t["name"])


def list_hitters(season: int) -> list[dict]:
    """Every MLB position player (incl. two-way players) for the search box.

    One Stats API call returns the whole league with team, position, and
    batting side. `team` is the player's current team.
    """
    resp = requests.get(f"{STATS_API}/sports/1/players", params={"season": season},
                        headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    abbrev = {t["id"]: t["abbreviation"] for t in list_teams(season)}
    hitters = []
    for p in resp.json().get("people", []):
        if p.get("primaryPosition", {}).get("type") == "Pitcher":
            continue
        hitters.append({
            "id": p["id"],
            "name": p["fullName"],
            "position": p["primaryPosition"].get("abbreviation", ""),
            "team": abbrev.get(p.get("currentTeam", {}).get("id"), ""),
            "bats": p.get("batSide", {}).get("code", ""),
            "number": p.get("primaryNumber", ""),
        })
    return sorted(hitters, key=lambda h: h["name"])


def team_hitters(team_id: int, season: int) -> list[dict]:
    """Non-pitchers on a team's active roster (two-way players included)."""
    resp = requests.get(f"{STATS_API}/teams/{team_id}/roster",
                        params={"season": season, "rosterType": "active"},
                        headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    hitters = []
    for entry in resp.json().get("roster", []):
        if entry["position"].get("type") == "Pitcher":
            continue
        hitters.append({
            "id": entry["person"]["id"],
            "name": entry["person"]["fullName"],
            "position": entry["position"].get("abbreviation", ""),
            "number": entry.get("jerseyNumber", ""),
        })
    return hitters


def _cache_path(batter_id: int, season: int) -> Path:
    return CACHE_DIR / str(season) / f"{batter_id}.csv"


def fetch_batter_pitches(batter_id: int, season: int, max_age_hours: float = 24.0) -> pd.DataFrame:
    """Every regular-season pitch a hitter saw in `season` (Statcast columns).

    Uses the disk cache when it is younger than `max_age_hours`; pass
    `max_age_hours=float("inf")` to never re-download.
    """
    path = _cache_path(batter_id, season)
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        return pd.read_csv(path)

    params = {
        "all": "true",
        "hfGT": "R|",                # regular season
        "hfSea": f"{season}|",
        "player_type": "batter",
        "batters_lookup[]": batter_id,
        "type": "details",
    }
    resp = requests.get(SAVANT_CSV, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig")
    if not text.lstrip().startswith('"pitch_type"'):
        raise ValueError(f"Savant returned unexpected content for batter {batter_id}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return pd.read_csv(io.StringIO(text))

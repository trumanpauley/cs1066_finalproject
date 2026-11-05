"""MLB opponent scouting from public Baseball Savant / MLB Stats API data.

sources      -> fetch teams, rosters, and per-hitter Statcast pitches (disk-cached)
hitter_profile -> turn a hitter's pitches into tendencies vs. one pitcher hand
game_plan    -> match those tendencies against the user's arsenal
"""

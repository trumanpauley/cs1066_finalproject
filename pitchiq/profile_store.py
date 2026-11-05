"""Save/load the pitcher profile so uploads and notes survive a page refresh.

Layout (inside the gitignored data/ folder — reports are confidential):
    data/profile/profile.json      name, hand, arsenal + notes, approach, outings, notes docs
    data/profile/uploads/<file>    the original uploaded files, kept for future re-processing

Single-user local storage. A deployed, multi-user app would need per-user
storage (accounts) instead — see Journal02 "Expand the Application".
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "profile"

# Session-state keys that make up the saved profile.
PERSISTED_KEYS = (
    "pitcher_name", "throwing_hand", "arsenal",
    "strengths", "weaknesses", "preferences", "approach",
    "outings", "notes_docs",
)


def _profile_file(base: Path) -> Path:
    return base / "profile.json"


def load_profile(base: Path | None = None) -> dict:
    base = base or PROFILE_DIR
    path = _profile_file(base)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k in PERSISTED_KEYS}


def save_profile(profile: dict, base: Path | None = None) -> None:
    """Atomic write: a crash mid-save can't leave a half-written profile."""
    base = base or PROFILE_DIR
    base.mkdir(parents=True, exist_ok=True)
    data = {k: profile.get(k) for k in PERSISTED_KEYS}
    tmp = _profile_file(base).with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(_profile_file(base))


def content_id(data: bytes) -> str:
    """Stable id for an uploaded file, so the same file is never added twice."""
    return hashlib.sha1(data).hexdigest()[:12]


def save_upload(file_id: str, filename: str, data: bytes, base: Path | None = None) -> Path:
    folder = (base or PROFILE_DIR) / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{file_id}_{Path(filename).name}"
    path.write_bytes(data)
    return path


def delete_upload(file_id: str, base: Path | None = None) -> None:
    for path in ((base or PROFILE_DIR) / "uploads").glob(f"{file_id}_*"):
        path.unlink()

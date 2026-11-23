"""The app's pages, so one page can link to another (e.g. Game Plan -> Simulate).

app.py fills PAGES when it builds the navigation; pages look them up by url_path.
"""

from __future__ import annotations

PAGES: dict = {}  # url_path -> st.Page

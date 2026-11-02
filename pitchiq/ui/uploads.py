"""Upload sections: pitcher's own report + opponent scouting reports.

V0.2: two distinct upload cards with per-file rows (name, size, status).
Functionality is unchanged — files are validated and their metadata stored
in session state for future PDF extraction.
"""

from __future__ import annotations

import streamlit as st

from pitchiq.config import ACCEPTED_UPLOAD_TYPES, MAX_UPLOAD_MB
from pitchiq.services.pdf_service import summarize_upload, validate_upload


def render_uploads() -> None:
    st.markdown("### 📄 Scouting Report Uploads")
    st.caption(
        f"PDFs up to {MAX_UPLOAD_MB} MB. Files are kept for this session only — "
        "V0.3 will extract pitch-level data from them automatically."
    )

    col_mine, col_opp = st.columns(2, gap="medium")

    with col_mine:
        _upload_card(
            accent_class="upload-accent-mine",
            icon="🧾",
            title="My Pitching Report",
            subtitle="Your own process/pitching report (e.g., a Sockeye or TruMedia export).",
            key="pitcher_report_uploader",
            state_key="pitcher_reports",
            label="Upload your pitching report (PDF)",
            multiple=False,
            empty_hint="Drop your pitching report here to unlock personalized analysis.",
        )

    with col_opp:
        _upload_card(
            accent_class="upload-accent-opp",
            icon="🎯",
            title="Opponent Reports",
            subtitle="Opposing team hitting reports — upload one or several.",
            key="opponent_report_uploader",
            state_key="opponent_reports",
            label="Upload opponent scouting reports (PDF)",
            multiple=True,
            empty_hint="Drop opponent hitting reports here to scout their lineup.",
        )


def _upload_card(
    accent_class: str,
    icon: str,
    title: str,
    subtitle: str,
    key: str,
    state_key: str,
    label: str,
    multiple: bool,
    empty_hint: str,
) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="{accent_class}"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="upload-card-header">
                <span class="upload-icon">{icon}</span>
                <span>
                    <span class="upload-title">{title}</span><br>
                    <span class="upload-sub">{subtitle}</span>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            label,
            type=ACCEPTED_UPLOAD_TYPES,
            accept_multiple_files=multiple,
            key=key,
            label_visibility="collapsed",
        )

        files = uploaded if isinstance(uploaded, list) else ([uploaded] if uploaded else [])

        records = []
        for f in files:
            ok, message = validate_upload(f)
            if ok:
                records.append(summarize_upload(f))
            else:
                st.error(f"**{f.name}** — {message}")
        st.session_state[state_key] = records

        if records:
            st.success(
                f"✅ {len(records)} file{'s' if len(records) != 1 else ''} "
                "uploaded successfully."
            )
            for r in records:
                st.markdown(
                    f"""
                    <div class="file-row">
                        <span class="file-name">📎 {r["name"]}</span>
                        <span class="file-size">{r["size_kb"]} KB</span>
                        <span class="file-status">{r["status"]}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info(empty_hint)

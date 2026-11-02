"""Custom CSS theme for PitchIQ — consistent, high-contrast dark theme.

Pairs with .streamlit/config.toml (base = "dark") so native widgets and
custom cards share one professional palette.
"""

CUSTOM_CSS = """
<style>
/* ---------- Palette ----------
   bg:        #0d1b2a   card bg:   #152a3f
   border:    #2a4663   accent:    #4da3ff
   text:      #e8f1f9   muted:     #9fb6c9
--------------------------------- */

/* ---------- Global ---------- */
.block-container {
    padding-top: 2.2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* ---------- Hero banner ---------- */
.pitchiq-hero {
    background: linear-gradient(135deg, #10263d 0%, #1d4e79 55%, #2a6f97 100%);
    border: 1px solid #2a4663;
    border-radius: 14px;
    padding: 1.8rem 2.2rem;
    margin-bottom: 1.4rem;
    color: #ffffff;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.45);
}
.pitchiq-hero h1 {
    margin: 0;
    font-size: 2.1rem;
    letter-spacing: 0.5px;
    color: #ffffff;
}
.pitchiq-hero p {
    margin: 0.35rem 0 0 0;
    font-size: 1.02rem;
    color: #cfe3f5;
}
.pitchiq-hero .version-badge {
    display: inline-block;
    margin-top: 0.7rem;
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.4);
    border-radius: 999px;
    padding: 0.15rem 0.8rem;
    font-size: 0.78rem;
    letter-spacing: 1px;
    color: #ffffff;
}

/* ---------- Section cards ---------- */
.pitchiq-card {
    background: #152a3f;
    border: 1px solid #2a4663;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
    color: #e8f1f9;
}
.pitchiq-card h4 { margin-top: 0; color: #f2f7fc; }
.pitchiq-card p { color: #c3d6e6; }

/* ---------- Hitter report cards ---------- */
.hitter-header {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    border-left: 5px solid #4da3ff;
    padding-left: 0.8rem;
    margin: 0.4rem 0 0.6rem 0;
}
.hitter-header .hitter-name {
    font-size: 1.18rem;
    font-weight: 700;
    color: #f2f7fc;
}
.hitter-header .hitter-meta {
    font-size: 0.88rem;
    color: #9fb6c9;
}

/* ---------- Threat badges ---------- */
.badge {
    display: inline-block;
    border-radius: 999px;
    padding: 0.12rem 0.7rem;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge-high   { background: rgba(244, 98, 98, 0.18);  color: #ff8a8a; border: 1px solid #a14040; }
.badge-medium { background: rgba(255, 190, 70, 0.16); color: #ffcf70; border: 1px solid #9a7a2e; }
.badge-low    { background: rgba(80, 200, 120, 0.16); color: #7fe0a2; border: 1px solid #3e7d57; }

/* ---------- Recommendation box ---------- */
.rec-box {
    background: #11314d;
    border: 1px solid #2a4663;
    border-left: 5px solid #4da3ff;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0 0.9rem 0;
    color: #d9e9f8;
    font-size: 0.95rem;
}
.rec-box .rec-label {
    font-weight: 700;
    font-size: 0.78rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #7cc0ff;
}

/* ---------- Upload cards ---------- */
.upload-card-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.2rem;
}
.upload-card-header .upload-icon {
    font-size: 1.6rem;
    background: #11314d;
    border: 1px solid #2a4663;
    border-radius: 10px;
    padding: 0.35rem 0.55rem;
}
.upload-card-header .upload-title {
    font-size: 1.08rem;
    font-weight: 700;
    color: #f2f7fc;
}
.upload-card-header .upload-sub {
    font-size: 0.85rem;
    color: #9fb6c9;
}
.upload-accent-mine { border-top: 4px solid #4da3ff; border-radius: 4px 4px 0 0; }
.upload-accent-opp  { border-top: 4px solid #2ec4b6; border-radius: 4px 4px 0 0; }

.file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    background: #11314d;
    border: 1px solid #2a4663;
    border-radius: 8px;
    padding: 0.5rem 0.9rem;
    margin: 0.35rem 0;
}
.file-row .file-name {
    font-weight: 600;
    color: #e8f1f9;
    font-size: 0.92rem;
    overflow-wrap: anywhere;
}
.file-row .file-size {
    color: #9fb6c9;
    font-size: 0.82rem;
    white-space: nowrap;
}
.file-row .file-status {
    background: rgba(80, 200, 120, 0.16);
    border: 1px solid #3e7d57;
    color: #7fe0a2;
    border-radius: 999px;
    padding: 0.1rem 0.65rem;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    white-space: nowrap;
}

/* ---------- Sidebar polish ---------- */
section[data-testid="stSidebar"] {
    background: #0a1622;
    border-right: 1px solid #2a4663;
}
section[data-testid="stSidebar"] * {
    color: #e8f1f9;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.18);
}

/* ---------- Footer ---------- */
.pitchiq-footer {
    text-align: center;
    color: #9fb6c9;
    font-size: 0.82rem;
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid #2a4663;
}
</style>
"""


def inject_css() -> None:
    """Inject the PitchIQ theme into the current Streamlit page."""
    import streamlit as st

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

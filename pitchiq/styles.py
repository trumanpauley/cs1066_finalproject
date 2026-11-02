"""Custom CSS for PitchIQ — minimal, modern dark theme.

Pairs with .streamlit/config.toml (base = "dark"). Design goals: generous
whitespace, clean typography, subtle borders, no visual clutter.
"""

CUSTOM_CSS = """
<style>
/* ---------- Palette ----------
   bg:      #0e1117    surface:  #181c25
   border:  #262b36    accent:   #7aa2f7
   text:    #e6e9ef    muted:    #8b93a3
--------------------------------- */

/* ---------- Global ---------- */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 880px;
}
h1, h2, h3, h4 {
    letter-spacing: -0.01em;
}

/* ---------- Scout hero (empty state) ---------- */
.scout-hero {
    text-align: center;
    margin: 14vh 0 2.5rem 0;
}
.scout-hero h1 {
    font-size: 2.3rem;
    font-weight: 700;
    color: #f2f4f8;
    margin: 0 0 0.6rem 0;
}
.scout-hero p {
    font-size: 1.05rem;
    color: #8b93a3;
    margin: 0;
}

/* ---------- Tags on assistant messages ---------- */
.depth-tag {
    display: inline-block;
    background: rgba(122, 162, 247, 0.12);
    border: 1px solid rgba(122, 162, 247, 0.35);
    color: #9db8f9;
    border-radius: 999px;
    padding: 0.08rem 0.65rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
.demo-tag {
    display: inline-block;
    background: rgba(139, 147, 163, 0.1);
    border: 1px solid #333945;
    color: #8b93a3;
    border-radius: 999px;
    padding: 0.08rem 0.65rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    margin-left: 0.3rem;
}

/* ---------- Composer context line ---------- */
.context-line {
    color: #8b93a3;
    font-size: 0.8rem;
    margin: 0.15rem 0 0.4rem 0;
}
.context-line b { color: #aeb6c4; font-weight: 600; }

/* ---------- Cards ---------- */
.pitchiq-card {
    background: #181c25;
    border: 1px solid #262b36;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    color: #e6e9ef;
}
.pitchiq-card h4 { margin-top: 0; color: #f2f4f8; }
.pitchiq-card p { color: #aeb6c4; }

/* ---------- Hitter report cards ---------- */
.hitter-header {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    border-left: 3px solid #7aa2f7;
    padding-left: 0.8rem;
    margin: 0.4rem 0 0.6rem 0;
}
.hitter-header .hitter-name {
    font-size: 1.12rem;
    font-weight: 700;
    color: #f2f4f8;
}
.hitter-header .hitter-meta {
    font-size: 0.86rem;
    color: #8b93a3;
}

/* ---------- Threat badges ---------- */
.badge {
    display: inline-block;
    border-radius: 999px;
    padding: 0.1rem 0.65rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
.badge-high   { background: rgba(240, 100, 100, 0.12); color: #f28b8b; border: 1px solid #5c3434; }
.badge-medium { background: rgba(240, 190, 90, 0.1);   color: #e5c07b; border: 1px solid #574a2c; }
.badge-low    { background: rgba(110, 200, 140, 0.1);  color: #8fd4a8; border: 1px solid #2f4d3a; }

/* ---------- Recommendation box ---------- */
.rec-box {
    background: #161a22;
    border: 1px solid #262b36;
    border-left: 3px solid #7aa2f7;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0 0.9rem 0;
    color: #ccd3de;
    font-size: 0.94rem;
}
.rec-box .rec-label {
    font-weight: 600;
    font-size: 0.74rem;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #9db8f9;
}

/* ---------- Upload file rows ---------- */
.file-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    background: #161a22;
    border: 1px solid #262b36;
    border-radius: 8px;
    padding: 0.5rem 0.9rem;
    margin: 0.35rem 0;
}
.file-row .file-name {
    font-weight: 500;
    color: #e6e9ef;
    font-size: 0.9rem;
    overflow-wrap: anywhere;
}
.file-row .file-size {
    color: #8b93a3;
    font-size: 0.8rem;
    white-space: nowrap;
}
.file-row .file-status {
    background: rgba(110, 200, 140, 0.1);
    border: 1px solid #2f4d3a;
    color: #8fd4a8;
    border-radius: 999px;
    padding: 0.08rem 0.6rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    white-space: nowrap;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: #0b0e14;
    border-right: 1px solid #1d222c;
}

/* ---------- Footer ---------- */
.pitchiq-footer {
    text-align: center;
    color: #5f6774;
    font-size: 0.8rem;
    margin-top: 3rem;
    padding-top: 1.2rem;
    border-top: 1px solid #1d222c;
}
</style>
"""


def inject_css() -> None:
    """Inject the PitchIQ theme into the current Streamlit page."""
    import streamlit as st

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

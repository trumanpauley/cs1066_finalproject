"""Zone heatmaps for a hitter (catcher's view), built from Statcast pitch rows.

5x5 grid: the inner 3x3 is the strike zone, the outer ring is just off the
plate. Height is normalized to each pitch's own strike zone (sz_bot..sz_top),
so tall and short hitters line up.

Color is single-hue sequential on the dark app surface: low values recede
into the background, high values are bright. Damage (good for the hitter)
is orange; whiff and swing rates are blue, so the two never read alike.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SURFACE = "#181c25"
TEXT = "#e6e9ef"
MUTED = "#8b93a3"

BLUE = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"]
ORANGE = ["#3b1d10", "#6b2c12", "#a33f17", "#d95926", "#ef8a5a", "#f8c3a5"]

# Plate half-width incl. ball radius ~0.83 ft; outer cells extend to +/-1.5 ft.
X_EDGES = [-1.5, -0.83, -0.277, 0.277, 0.83, 1.5]
Z_EDGES = [-0.5, 0.0, 1 / 3, 2 / 3, 1.0, 1.5]   # fraction of the strike zone height

METRICS = {
    "Damage (xwOBA on contact)": {"colors": ORANGE, "range": (0.200, 0.600), "fmt": ".3f", "min_n": 5},
    "Whiff %": {"colors": BLUE, "range": (0, 50), "fmt": ".0f", "min_n": 8},
    "Swing %": {"colors": BLUE, "range": (0, 100), "fmt": ".0f", "min_n": 10},
}


def _scale(colors: list[str]) -> list[list]:
    return [[i / (len(colors) - 1), c] for i, c in enumerate(colors)]


def zone_grid(pitches: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray]:
    """(values, sample sizes) on the 5x5 grid; rows run bottom -> top."""
    df = pitches.dropna(subset=["plate_x", "plate_z", "sz_top", "sz_bot"]).copy()
    height = (df["sz_top"] - df["sz_bot"]).where(lambda h: h > 0)
    df["zn"] = (df["plate_z"] - df["sz_bot"]) / height
    df["xi"] = pd.cut(df["plate_x"], X_EDGES, labels=False)
    df["zi"] = pd.cut(df["zn"], Z_EDGES, labels=False)
    df = df.dropna(subset=["xi", "zi"])

    values = np.full((5, 5), np.nan)
    counts = np.zeros((5, 5), dtype=int)
    min_n = METRICS[metric]["min_n"]
    for (zi, xi), cell in df.groupby(["zi", "xi"]):
        if metric.startswith("Damage"):
            sample = cell[cell["bip"]]
            n, v = len(sample), sample["xwoba"].mean()
        elif metric == "Whiff %":
            n = int(cell["swing"].sum())
            v = 100 * cell["whiff"].sum() / n if n else np.nan
        else:
            n = len(cell)
            v = 100 * cell["swing"].mean()
        counts[int(zi), int(xi)] = n
        if n >= min_n:
            values[int(zi), int(xi)] = v
    return values, counts


def zone_heatmap(pitches: pd.DataFrame, metric: str, stand: str) -> go.Figure:
    spec = METRICS[metric]
    values, counts = zone_grid(pitches, metric)
    unit = "contact" if metric.startswith("Damage") else "swings" if metric == "Whiff %" else "pitches"
    text = [[("" if np.isnan(v) else format(v, spec["fmt"]).lstrip("0") if spec["fmt"] == ".3f"
              else format(v, spec["fmt"])) for v in row] for row in values]

    fig = go.Figure(go.Heatmap(
        z=values, x=list(range(5)), y=list(range(5)),
        zmin=spec["range"][0], zmax=spec["range"][1],
        colorscale=_scale(spec["colors"]), showscale=False,
        xgap=2, ygap=2,
        text=text, texttemplate="%{text}", textfont={"size": 12, "color": TEXT},
        customdata=counts,
        hovertemplate=f"{metric}: %{{text}}<br>%{{customdata}} {unit}<extra></extra>",
    ))
    # Strike zone outline (inner 3x3).
    fig.add_shape(type="rect", x0=0.5, x1=3.5, y0=0.5, y1=3.5,
                  line={"color": TEXT, "width": 2})

    # Catcher's view: left side is the 3B side = inside to a right-handed hitter.
    left, right = ("In", "Away") if stand == "R" else ("Away", "In")
    fig.update_xaxes(tickvals=[0, 4], ticktext=[left, right], showgrid=False,
                     zeroline=False, tickfont={"color": MUTED})
    fig.update_yaxes(tickvals=[0, 4], ticktext=["Low", "High"], showgrid=False,
                     zeroline=False, tickfont={"color": MUTED}, scaleanchor="x")
    fig.update_layout(
        height=300, margin={"l": 40, "r": 10, "t": 30, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=SURFACE,
        title={"text": f"Catcher's view · bats {stand}", "font": {"size": 12, "color": MUTED}},
        font={"color": TEXT},
    )
    return fig

"""Streamlit proof-of-concept for the SL1 dashboard (look-and-feel comparison only).

Reads the same JSON sidecar that build_dashboard.py writes, so the numbers are
identical to the public Cloudflare page. Run with:

    PYTHONPATH= ../hermes-agent/venv/bin/python -m streamlit run streamlit_app.py

The point of this file is a like-for-like visual comparison, not a replacement.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_HERE = pathlib.Path(__file__).resolve().parent
DATA = _HERE / "data" / "sl1_dashboard.json"
if not DATA.exists():  # local fallback when running from the scripts folder
    DATA = _HERE.parent / "workspace" / "dashboard" / "sl1_dashboard.json"
GREEN, RED, CYAN = "#4ade80", "#f87171", "#38bdf8"

st.set_page_config(page_title="SL1 · xG vs xGA", page_icon="⚽", layout="wide")

d = json.loads(DATA.read_text())
df = pd.DataFrame(d["xg_rows"])
season = d.get("season", "2026/27")

st.title("Super League 1 · xG vs xGA")
st.caption(f"{season} · xG model · built {d.get('generated_at', '')[:16].replace('T', ' ')}")

per_match = st.radio("Scale", ["Per match", "Totals"], horizontal=True) == "Per match"
xf = "xga_pg" if per_match else "xga"
yf = "xgf_pg" if per_match else "xgf"

avg_x = float(df[xf].mean())
avg_y = float(df[yf].mean())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Teams", len(df))
k2.metric("Games each", f"{int(df['P'].min())}-{int(df['P'].max())}")
best_att = df.loc[df[yf].idxmax()]
best_def = df.loc[df[xf].idxmin()]
k3.metric("Best attack", best_att["name"].split()[0], f"{best_att[yf]:.2f} xG")
k4.metric("Best defence", best_def["name"].split()[0], f"{best_def[xf]:.2f} xGA")


def colour(r: pd.Series) -> str:
    good = r[yf] > avg_y and r[xf] < avg_x
    bad = r[yf] < avg_y and r[xf] > avg_x
    return GREEN if good else RED if bad else CYAN


df["colour"] = df.apply(colour, axis=1)

fig = go.Figure()
x0, x1 = df[xf].min(), df[xf].max()
y0, y1 = df[yf].min(), df[yf].max()
pad_x, pad_y = (x1 - x0) * 0.22, (y1 - y0) * 0.22

# quadrants, then the average crosshair
quad = dict(line=dict(width=0), layer="below")
fig.add_shape(type="rect", x0=x0 - pad_x, x1=avg_x, y0=y0 - pad_y, y1=avg_y, fillcolor="rgba(248,113,113,0.05)", **quad)
fig.add_shape(type="rect", x0=x0 - pad_x, x1=avg_x, y0=avg_y, y1=y1 + pad_y, fillcolor="rgba(74,222,128,0.08)", **quad)
fig.add_shape(type="rect", x0=avg_x, x1=x1 + pad_x, y0=avg_y, y1=y1 + pad_y, fillcolor="rgba(56,189,248,0.05)", **quad)
fig.add_shape(type="rect", x0=avg_x, x1=x1 + pad_x, y0=y0 - pad_y, y1=avg_y, fillcolor="rgba(56,189,248,0.05)", **quad)
fig.add_shape(type="line", x0=avg_x, x1=avg_x, y0=y0 - pad_y, y1=y1 + pad_y,
              line=dict(color="#3d4f66", width=1, dash="dash"), layer="below")
fig.add_shape(type="line", x0=x0 - pad_x, x1=x1 + pad_x, y0=avg_y, y1=avg_y,
              line=dict(color="#3d4f66", width=1, dash="dash"), layer="below")

SPREAD = {"OFI": "middle left", "Kalamata": "middle right", "Levadiakos": "middle right"}
for col, name in ((GREEN, "elite"), (CYAN, "one-way"), (RED, "struggling")):
    sub = df[df["colour"] == col]
    pos = [SPREAD.get(n.split()[0], "top center") for n in sub["name"]]
    fig.add_trace(go.Scatter(
        x=sub[xf], y=sub[yf], mode="markers+text", name=name,
        text=sub["name"].str.split().str[0], textposition=pos,
        textfont=dict(size=11, color="#c7d4e4"),
        marker=dict(size=13, color=col, line=dict(width=1.4, color="#080d15")),
        customdata=sub[["name", "xgf", "xga", "P"]],
        hovertemplate="<b>%{customdata[0]}</b><br>xG %{customdata[1]:.1f} · xGA %{customdata[2]:.1f}<br>"
                      "%{customdata[3]} games<extra></extra>",
    ))

fig.update_xaxes(title="xGA per match · better defence to the right →", autorange="reversed",
                 showgrid=True, gridcolor="#1b2736", zeroline=False)
fig.update_yaxes(title="xG per match · better attack ↓", autorange="reversed",
                 showgrid=True, gridcolor="#1b2736", zeroline=False)
fig.update_layout(
    template="plotly_dark", height=520, paper_bgcolor="#0e1621", plot_bgcolor="#0e1621",
    margin=dict(l=10, r=10, t=10, b=10), showlegend=True,
    legend=dict(orientation="h", y=-0.18, x=0, bgcolor="rgba(0,0,0,0)"),
    font=dict(family="Inter, system-ui, sans-serif", size=12, color="#c7d4e4"),
    hoverlabel=dict(bgcolor="#16202e", font_size=12),
)
fig.add_annotation(x=x0 - pad_x * 0.45, y=y1 + pad_y * 0.45, text="ELITE", showarrow=False,
                   font=dict(size=11, color=GREEN), opacity=0.75)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})
st.caption("Hover a marker for the exact numbers. Axes reversed on purpose: best attack bottom, best defence right.")

with st.expander("Table", expanded=False):
    table = df.assign(xG=df["xgf"].round(1), xGA=df["xga"].round(1))[
        ["name", "P", "xG", "xGA", "xgf_pg", "xga_pg"]
    ].sort_values("xgf_pg", ascending=False)
    st.dataframe(
        table.rename(columns={"name": "Team", "P": "P", "xgf_pg": "xG/g", "xga_pg": "xGA/g"}),
        use_container_width=True, hide_index=True,
        column_config={
            "xG/g": st.column_config.NumberColumn(format="%.2f"),
            "xGA/g": st.column_config.NumberColumn(format="%.2f"),
        },
    )

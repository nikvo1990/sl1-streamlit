"""Streamlit mirror of the SL1 dashboard: team xG map plus player analytics.

Reads the same JSON sidecars that the static build uses, so every number here
matches the public Cloudflare page. Run locally with:

    PYTHONPATH= ~/.hermes/hermes-agent/venv/bin/python -m streamlit run streamlit_app.py --server.port 8533

Team map: xG vs xGA quadrant, axes inverted so the best team sits bottom-right.
Players: finishing, chance creation, per-90 percentiles and goalkeepers.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_HERE = pathlib.Path(__file__).resolve().parent
DATA = _HERE / "data" / "sl1_dashboard.json"
PDATA = _HERE / "data" / "sl1_players.json"
RDATA = _HERE / "data" / "sl1_rounds.json"
if not DATA.exists():  # local fallback when running from the scripts folder
    DATA = _HERE.parent / "workspace" / "dashboard" / "sl1_dashboard.json"
if not PDATA.exists():
    PDATA = _HERE.parent / "workspace" / "sl1_players.json"
if not RDATA.exists():
    RDATA = _HERE.parent / "workspace" / "sl1_rounds.json"

GREEN, RED, CYAN, AMBER, PURPLE = "#4ade80", "#f87171", "#38bdf8", "#fbbf24", "#a78bfa"
ROLE_COL = {"GK": PURPLE, "DEF": CYAN, "MID": GREEN, "FWD": AMBER}
FONT = dict(family="Inter, system-ui, sans-serif", size=12, color="#c7d4e4")
GRID = "#1b2736"
BG = "#0e1621"

st.set_page_config(page_title="SL1 · team xG and player analytics", page_icon="⚽", layout="wide")


@st.cache_data(show_spinner=False)
def load_team(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


@st.cache_data(show_spinner=False)
def load_players(path: str) -> pd.DataFrame:
    raw = json.loads(pathlib.Path(path).read_text())
    df = pd.DataFrame(raw["players"])
    df["team_games"] = df.groupby("team")["apps"].transform("max").clip(lower=1)
    for col in ("goals", "xg", "xa", "sca", "vaep", "xt", "xg", "xgot"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["gmxg"] = df["goals"] - df["xg"]
    df["dev"] = df["xgot"] - df["xg"]
    df["prog"] = df["progressive_passes"] + df["progressive_carries"]
    mins = df["minutes"].where(df["minutes"] > 0)
    for col in ("goals", "xg", "xa", "sca", "vaep", "xt", "prog", "shots", "key_passes"):
        df[f"{col}_90"] = df[col] / mins * 90
    df["gc90"] = df["goals_conceded"] / mins * 90
    return df


@st.cache_data(show_spinner=False)
def load_rounds_raw(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text())


@st.cache_data(show_spinner=False)
def load_rounds(path: str) -> pd.DataFrame:
    raw = load_rounds_raw(path)
    rows = []
    for m in raw["matches"]:
        row = {k: v for k, v in m.items() if k not in ("players", "goals")}
        row["players"] = len(m.get("players", []))
        rows.append(row)
    return pd.DataFrame(rows)


def base_layout(fig: go.Figure, height: int = 520, legend: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_dark", height=height, paper_bgcolor=BG, plot_bgcolor=BG,
        margin=dict(l=10, r=10, t=10, b=10), showlegend=legend,
        legend=dict(orientation="h", y=-0.16, x=0, bgcolor="rgba(0,0,0,0)"),
        font=FONT, hoverlabel=dict(bgcolor="#16202e", font_size=12),
    )
    return fig


d = load_team(str(DATA))
df = pd.DataFrame(d["xg_rows"])
season = d.get("season", "2026/27")

st.title("Super League 1 · team xG and player analytics")
st.caption(
    f"{season} · {len(df)} teams · built {str(d.get('generated_at', '')[:16]).replace('T', ' ')}"
)

tab_team, tab_players, tab_days = st.tabs(["Team map · xG vs xGA", "Players", "Match days"])

# --------------------------------------------------------------------------- #
# Team map
# --------------------------------------------------------------------------- #
with tab_team:
    per_match = st.radio("Scale", ["Per match", "Totals"], horizontal=True, key="scale") == "Per match"
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

    quad = dict(line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x0 - pad_x, x1=avg_x, y0=y0 - pad_y, y1=avg_y,
                  fillcolor="rgba(248,113,113,0.05)", **quad)
    fig.add_shape(type="rect", x0=x0 - pad_x, x1=avg_x, y0=avg_y, y1=y1 + pad_y,
                  fillcolor="rgba(74,222,128,0.08)", **quad)
    fig.add_shape(type="rect", x0=avg_x, x1=x1 + pad_x, y0=avg_y, y1=y1 + pad_y,
                  fillcolor="rgba(56,189,248,0.05)", **quad)
    fig.add_shape(type="rect", x0=avg_x, x1=x1 + pad_x, y0=y0 - pad_y, y1=avg_y,
                  fillcolor="rgba(56,189,248,0.05)", **quad)
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
                     showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(title="xG per match · better attack ↓", autorange="reversed",
                     showgrid=True, gridcolor=GRID, zeroline=False)
    base_layout(fig, 520)
    fig.add_annotation(x=x0 - pad_x * 0.45, y=y1 + pad_y * 0.45, text="ELITE", showarrow=False,
                       font=dict(size=11, color=GREEN), opacity=0.75)

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "scrollZoom": False})
    st.caption("Hover a marker for the exact numbers. Axes reversed on purpose: best attack bottom, best defence right.")

    with st.expander("Table", expanded=False):
        table = df.assign(xG=df["xgf"].round(1), xGA=df["xga"].round(1))[
            ["name", "P", "xG", "xGA", "xgf_pg", "xga_pg"]
        ].sort_values("xgf_pg", ascending=False)
        st.dataframe(
            table.rename(columns={"name": "Team", "xgf_pg": "xG/g", "xga_pg": "xGA/g"}),
            width="stretch", hide_index=True,
            column_config={
                "xG/g": st.column_config.NumberColumn(format="%.2f"),
                "xGA/g": st.column_config.NumberColumn(format="%.2f"),
            },
        )

# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #
with tab_players:
    pdx = load_players(str(PDATA))

    c1, c2, c3 = st.columns([1.1, 1, 1.3])
    gate = c1.slider("Minimum minutes", 90, 720, 300, step=30, key="gate")
    roles = c2.multiselect("Position", ["GK", "DEF", "MID", "FWD"], default=["DEF", "MID", "FWD"],
                           key="roles")
    clubs = c3.multiselect("Club", sorted(pdx["team"].unique()), default=[], key="clubs")

    view = pdx[(pdx["minutes"] >= gate) & (pdx["role"].isin(roles))]
    if clubs:
        view = view[view["team"].isin(clubs)]

    if view.empty:
        st.info("No player clears that filter. Lower the minutes gate or widen the position filter.")
    else:
        top_scorer = view.loc[view["goals"].idxmax()]
        top_over = view.loc[view["gmxg"].idxmax()]
        top_vaep = view.loc[view["vaep_90"].idxmax()]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Players in view", len(view))
        m2.metric("Top scorer", top_scorer["name"].split()[-1], f"{int(top_scorer['goals'])} goals")
        m3.metric("Best vs xG", top_over["name"].split()[-1], f"{top_over['gmxg']:+.2f}")
        m4.metric("Best VAEP/90", top_vaep["name"].split()[-1], f"{top_vaep['vaep_90']:.2f}")

        st.subheader("Finishing: goals against expected goals")
        st.caption("Above the diagonal means clinical, below means wasteful. Marker size is minutes played; "
                   "hover for the full line.")

        lim = float(max(view["xg"].max(), view["goals"].max())) * 1.08 + 0.5
        fig2 = go.Figure()
        fig2.add_shape(type="line", x0=0, y0=0, x1=lim, y1=lim,
                       line=dict(color="#3d4f66", width=1, dash="dash"), layer="below")
        for role in ("DEF", "MID", "FWD", "GK"):
            sub = view[view["role"] == role]
            if sub.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=sub["xg"], y=sub["goals"], mode="markers", name=role,
                marker=dict(size=(sub["minutes"] / 12).clip(6, 26), color=ROLE_COL[role],
                            opacity=0.85, line=dict(width=1, color="#080d15")),
                customdata=sub[["name", "team", "minutes", "shots", "sot", "gmxg"]],
                hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                              "goals %{y:.0f} · xG %{x:.2f}<br>%{customdata[2]:.0f} min · "
                              "%{customdata[3]:.0f} shots · %{customdata[4]:.0f} on target<br>"
                              "G−xG %{customdata[5]:+.2f}<extra></extra>",
            ))
        fig2.update_xaxes(title="Expected goals", showgrid=True, gridcolor=GRID, zeroline=False)
        fig2.update_yaxes(title="Goals", showgrid=True, gridcolor=GRID, zeroline=False)
        base_layout(fig2, 470)
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

        st.subheader("Percentile profile against positional peers")
        st.caption("100 means best in his position group, 0 means worst. Everyone shown clears the minutes gate.")

        METRICS = [("goals_90", "G/90"), ("xg_90", "xG/90"), ("xa_90", "xA/90"),
                   ("sca_90", "SCA/90"), ("prog_90", "Prog/90"), ("vaep_90", "VAEP/90")]
        pv = view.copy()
        for key, _lab in METRICS:
            pv[f"pct_{key}"] = pv.groupby("role")[key].rank(pct=True) * 100

        leaders = pv.nlargest(16, "vaep_90")
        z = leaders[[f"pct_{k}" for k, _ in METRICS]].to_numpy()
        fig3 = go.Figure(go.Heatmap(
            z=z, x=[lab for _k, lab in METRICS], y=leaders["name"] + " · " + leaders["team"].str.split().str[0],
            colorscale=[[0, "#16202e"], [0.5, "#1e6b45"], [1, GREEN]],
            zmin=0, zmax=100, text=z.round(0).astype(int), texttemplate="%{text}",
            textfont=dict(size=10, color="#dbe7f3"), showscale=False, xgap=2, ygap=2,
            hovertemplate="%{y}<br>%{x}: %{z:.0f}<extra></extra>",
        ))
        fig3.update_yaxes(autorange="reversed", tickfont=dict(size=10))
        fig3.update_xaxes(side="top", tickangle=-45, tickfont=dict(size=9), automargin=True)
        base_layout(fig3, 520, legend=False)
        fig3.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})

        st.subheader("Goalkeepers: goals prevented")
        st.caption("Positive means saving more than the shots faced were worth. Unassisted by shot quality models, "
                   "so read it with the minutes.")
        gk = pdx[(pdx["role"] == "GK") & (pdx["minutes"] >= min(gate, 180))]
        if clubs:
            gk = gk[gk["team"].isin(clubs)]
        if gk.empty:
            st.info("No goalkeeper clears the minutes gate.")
        else:
            gk = gk.sort_values("goals_prevented")
            saves_rate = (gk["saves"] / (gk["saves"] + gk["goals_conceded"]).replace(0, pd.NA) * 100).fillna(0)
            fig4 = go.Figure(go.Bar(
                x=gk["goals_prevented"], y=gk["name"] + " · " + gk["team"].str.split().str[0],
                orientation="h",
                marker=dict(color=[GREEN if v >= 0 else RED for v in gk["goals_prevented"]]),
                customdata=gk[["minutes", "saves", "goals_conceded", "goals_prevented"]],
                hovertemplate="<b>%{y}</b><br>%{customdata[0]:.0f} min · %{customdata[1]:.0f} saves · "
                              "%{customdata[2]:.0f} conceded<br>goals prevented %{customdata[3]:+.2f}<extra></extra>",
            ))
            fig4.update_xaxes(title="Goals prevented", showgrid=True, gridcolor=GRID, zeroline=True,
                              zerolinecolor="#3d4f66")
            fig4.update_yaxes(tickfont=dict(size=10))
            base_layout(fig4, max(260, 26 * len(gk) + 60), legend=False)
            st.plotly_chart(fig4, width="stretch", config={"displayModeBar": False})

        with st.expander("Full player table", expanded=False):
            show = pd.DataFrame({
                "Player": view["name"], "Club": view["team"], "Pos": view["role"],
                "Min": view["minutes"].round(0), "Apps": view["apps"],
                "Gls": view["goals"].round(0), "xG": view["xg"].round(2),
                "G−xG": view["gmxg"].round(2), "Ast": view["assists"].round(0),
                "xA": view["xa"].round(2), "SCA/90": view["sca_90"].round(2),
                "Prog/90": view["prog_90"].round(2), "VAEP/90": view["vaep_90"].round(3),
            }).sort_values("VAEP/90", ascending=False)
            st.dataframe(show, width="stretch", hide_index=True, height=420)

        st.caption(
            f"Rate stats gated at {gate}+ minutes, so {len(view)} players qualify. "
            "Roles come from matchday line-ups. 143 of the 152 league goals are credited to a player; "
            "the other nine are own goals. Eight games is a small sample: treat per-90 extremes as noise."
        )

# --------------------------------------------------------------------------- #
# Match days
# --------------------------------------------------------------------------- #
with tab_days:
    raw = load_rounds_raw(str(RDATA))
    matches = raw["matches"]
    rdf = load_rounds(str(RDATA))
    round_list = sorted(rdf["round"].unique(), key=lambda r: float(r))
    names = [f"MD {r}" for r in round_list]

    c1, c2 = st.columns([1, 3])
    pick = c1.selectbox("Match day", names, index=len(names) - 1, key="md_pick")
    rnd = round_list[names.index(pick)]
    rms = [m for m in matches if str(m["round"]) == str(rnd)]

    goals = sum(m["hg"] + m["ag"] for m in rms)
    xg_pairs = [(m["xgh"], m["xga"]) for m in rms if m["xgh"] is not None]
    xg_tot = sum(h + a for h, a in xg_pairs) if xg_pairs else None

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Matches", len(rms))
    k2.metric("Goals", goals)
    k3.metric("Goals per match", f"{goals / max(1, len(rms)):.1f}")
    k4.metric("Total xG", "not published" if xg_tot is None else f"{xg_tot:.1f}")

    # spotlight on the widest win, ties to the most recent kickoff
    margin_max = max(abs(m["hg"] - m["ag"]) for m in rms)
    cands = [m for m in rms if abs(m["hg"] - m["ag"]) == margin_max]
    gmax = max(m["hg"] + m["ag"] for m in cands)
    cands = [m for m in cands if m["hg"] + m["ag"] == gmax]
    spot = max(cands, key=lambda m: m["date"])

    st.caption(f"Biggest win of the round: {margin_max} goal margin")
    st.markdown(f"### {spot['home']} {spot['hg']} – {spot['ag']} {spot['away']}")
    st.caption(
        " · ".join(x for x in [spot.get("stadium"), spot.get("referee"), spot.get("date")] if x)
        + ("" if spot["xgh"] is not None else "  ·  xG not published for this match yet")
    )

    duel_defs = [
        ("Possession", spot.get("posh"), spot.get("posa"), "{:.0f}%"),
        ("Shots", spot.get("shh"), spot.get("sha"), "{:.0f}"),
        ("Expected goals", spot.get("xgh"), spot.get("xga"), "{:.2f}"),
        ("Team VAEP", spot.get("vaeph"), spot.get("vaepa"), "{:.2f}"),
    ]
    duel_defs = [d for d in duel_defs if d[1] is not None and d[2] is not None]

    if duel_defs:
        labs = [d[0] for d in duel_defs]
        hs = [d[1] / ((d[1] + d[2]) or 1) * 100 for d in duel_defs]
        as_ = [100 - h for h in hs]
        figd = go.Figure()
        figd.add_trace(go.Bar(y=labs, x=hs, orientation="h", name=spot["home"],
                              marker_color=GREEN, text=[d[3].format(d[1]) for d in duel_defs],
                              textposition="inside", insidetextanchor="middle",
                              hovertemplate="%{y}: %{text}<extra></extra>"))
        figd.add_trace(go.Bar(y=labs, x=as_, orientation="h", name=spot["away"],
                              marker_color=AMBER, text=[d[3].format(d[2]) for d in duel_defs],
                              textposition="inside", insidetextanchor="middle",
                              hovertemplate="%{y}: %{text}<extra></extra>"))
        figd.update_layout(barmode="stack")
        figd.update_xaxes(range=[0, 100], visible=False)
        figd.update_yaxes(autorange="reversed", tickfont=dict(size=11))
        base_layout(figd, 240)
        figd.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figd, use_container_width=True, config={"displayModeBar": False})

    if spot.get("goals"):
        chips = []
        for g in sorted(spot["goals"], key=lambda g: (g.get("minute") or 0)):
            tag = " (pen)" if g.get("penalty") else (" (og)" if g.get("own_goal") else "")
            chips.append(f"{g.get('minute')}' {g.get('player')}{tag}")
        st.caption("Goals: " + " · ".join(chips))

    # fixtures and the round's own table
    def _num(v):
        return "—" if v is None else f"{v:.2f}"

    fx = pd.DataFrame({
        "Home": [m["home"] for m in rms],
        "Score": [f'{m["hg"]}-{m["ag"]}' for m in rms],
        "Away": [m["away"] for m in rms],
        "xG home": [_num(m["xgh"]) for m in rms],
        "xG away": [_num(m["xga"]) for m in rms],
    })

    rows = []
    for m in rms:
        if m["hg"] > m["ag"]:
            rows += [(m["home"], "W", m["hg"], m["ag"], m["xgh"], m["xga"]),
                     (m["away"], "L", m["ag"], m["hg"], m["xga"], m["xgh"])]
        elif m["hg"] < m["ag"]:
            rows += [(m["home"], "L", m["hg"], m["ag"], m["xgh"], m["xga"]),
                     (m["away"], "W", m["ag"], m["hg"], m["xga"], m["xgh"])]
        else:
            rows += [(m["home"], "D", m["hg"], m["ag"], m["xgh"], m["xga"]),
                     (m["away"], "D", m["ag"], m["hg"], m["xga"], m["xgh"])]
    tdf = pd.DataFrame(rows, columns=["Club", "R", "GF", "GA", "xG", "xGA"])
    tdf["Δ xG"] = (tdf["xG"] - tdf["xGA"]).round(2)
    tdf = tdf.sort_values(["Δ xG"], ascending=False, na_position="last")
    tdf["xG"] = tdf["xG"].map(_num)
    tdf["xGA"] = tdf["xGA"].map(_num)

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Fixtures and expected goals")
        st.dataframe(fx, width="stretch", hide_index=True)
    with right:
        st.subheader("This round's table")
        st.dataframe(tdf, width="stretch", hide_index=True, height=380,
                     column_config={
                         "Δ xG": st.column_config.NumberColumn(format="%+.2f"),
                     })

    # player comparison for the round
    rows_p = [p for m in rms for p in m["players"]]
    pdf = pd.DataFrame(rows_p)
    scored = pdf[pdf["gls"].notna()].copy() if "gls" in pdf else pd.DataFrame()

    st.subheader("Finishing against expectation, this round")
    if scored.empty:
        st.info("No box-score data published for this round yet.")
    else:
        scored["diff"] = scored["gls"] - scored["xg"]
        ranked = scored.sort_values("diff", ascending=False)
        pick_rows = pd.concat([ranked.head(8), ranked.tail(4)]).drop_duplicates(subset=["name"])
        pick_rows = pick_rows.sort_values("diff", ascending=False)
        figf = go.Figure(go.Bar(
            y=pick_rows["name"] + " · " + pick_rows["team"].str.split().str[0],
            x=pick_rows["diff"], orientation="h",
            marker_color=[GREEN if v >= 0 else RED for v in pick_rows["diff"]],
            text=[f"{int(g)} goal{'' if g == 1 else 's'} · xG {x:.2f}" if v >= 0 else ""
                  for g, x, v in zip(pick_rows["gls"], pick_rows["xg"], pick_rows["diff"])],
            textposition="outside",
            cliponaxis=False,
            customdata=pick_rows[["min", "sh"]],
            hovertemplate="<b>%{y}</b><br>goals minus xG %{x:+.2f}<br>"
                          "%{customdata[0]:.0f} min · %{customdata[1]:.0f} shots<extra></extra>",
        ))
        figf.update_xaxes(title="Goals minus xG", zeroline=True, zerolinecolor="#3d4f66",
                          showgrid=True, gridcolor=GRID)
        figf.update_yaxes(autorange="reversed", tickfont=dict(size=10))
        base_layout(figf, max(300, 26 * len(pick_rows) + 60), legend=False)
        figf.update_layout(margin=dict(l=10, r=90, t=10, b=10))
        st.plotly_chart(figf, use_container_width=True, config={"displayModeBar": False})

    st.subheader("Chance creation, this round")
    if pdf.empty:
        st.info("No player data for this round yet.")
    else:
        creat = pdf[pdf["min"] >= 20].nlargest(12, "sca")
        figc = go.Figure(go.Bar(
            y=creat["name"] + " · " + creat["team"].str.split().str[0], x=creat["sca"],
            orientation="h", marker_color=AMBER,
            customdata=creat[["kp", "min"]],
            text=creat["sca"].astype(int), textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>SCA %{x:.0f} · %{customdata[0]:.0f} key passes · "
                          "%{customdata[1]:.0f} min<extra></extra>",
        ))
        figc.update_xaxes(title="Shot-creating actions", showgrid=True, gridcolor=GRID,
                          zeroline=False)
        figc.update_yaxes(autorange="reversed", tickfont=dict(size=10))
        base_layout(figc, 420, legend=False)
        figc.update_layout(margin=dict(l=10, r=40, t=10, b=10))
        st.plotly_chart(figc, use_container_width=True, config={"displayModeBar": False})

    missing = [m for m in rms if m["xgh"] is None or not m["players"]]
    if missing:
        st.warning(
            "Full player numbers are not published yet for "
            + ", ".join(f'{m["home"]} {m["hg"]}-{m["ag"]} {m["away"]}' for m in missing)
            + ". The provider posts the box score a day or two after the final whistle; "
              "the scoreline, goal events and value numbers above are live."
        )

    st.caption(
        "Rounds are the provider's own match day numbering, taken from the match detail "
        "endpoint. One match per club per round, so the table is a single gameweek."
    )

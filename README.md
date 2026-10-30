# Super League 1 · xG vs xGA (Streamlit)

Interactive cut of the Greek Super League dashboard: every team plotted on expected goals
scored versus expected goals conceded, with the axes reversed so the **best attack sits at
the bottom** and the **best defence sits on the right**. The bottom-right quadrant is elite.

- Hover any marker for exact totals and games played
- Toggle between per-match and season totals
- Table expands under the chart, sortable

Data comes from `data/sl1_dashboard.json`, the same sidecar that feeds the static dashboard,
built from PitchAPI match data. Refresh the JSON and push, and Community Cloud redeploys.

Static version: https://sl1-dashboard.pages.dev

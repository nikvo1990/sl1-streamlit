# Super League 1 · team xG and player analytics (Streamlit)

Interactive cut of the Greek Super League dashboard. Three tabs:

**Team map · xG vs xGA.** Every team plotted on expected goals scored versus expected goals
conceded, with both axes reversed so the **best attack sits at the bottom** and the **best
defence sits on the right**. The bottom-right quadrant is elite.

**Players.** Four views over the same match data:

- Finishing: goals against expected goals, marker size is minutes, diagonal is par
- Percentile profile: goals, xG, xA, shot-creating actions, progression and VAEP per 90,
  ranked inside each position group
- Goalkeepers: goals prevented, from saves against post-shot expectation
- Full sortable table with the underlying per-90 numbers

Filters: minimum minutes (default 300 of a possible 720), position group and club. Rate
stats are gated because eight games is a small sample; below 300 minutes a single brace
swings a per-90 number by half a goal.

**Match days.** One match day at a time, from a round selector:

- Round totals: matches, goals, goals per match, total xG
- Spotlight on the widest win of the round (ties go to the latest kickoff), with a
  possession / shots / xG / team VAEP duel, the goal timeline and the scoreline
- Fixtures with both xG values, plus the round's own 14-club table sorted by xG difference
- Finishing against expectation: goals minus xG for the eight best and four most wasteful
  players of the round, hover shows minutes and shots
- Chance creation: shot-creating actions and key passes for the round's top twelve

Rounds come from the provider's own match day numbering on the match detail endpoint, not
from guesswork over dates. Matches whose box score is not published yet keep a null xG
rather than a zero, and the tab says so instead of charting a fake number.

## Data

- `data/sl1_dashboard.json` - team aggregates, the same sidecar that feeds the static dashboard
- `data/sl1_players.json` - 406 players flattened from one basic and one advanced call per
  played match, with club and position taken from the matchday line-ups
- `data/sl1_rounds.json` - all 55 played matches keyed by match day, carrying the scoreline,
  xG, referee, goal events and the per-match player lines

Both are built from PitchAPI event data. 143 of the 152 league goals are credited to a
player; the other nine are own goals. Refresh the JSON, push, and Community Cloud redeploys.

Static version with ten player panels and the Match Days tab: https://sl1-dashboard.pages.dev

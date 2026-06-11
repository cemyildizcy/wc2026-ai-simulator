"""Generate top scoreline distributions for most-likely tournament matches."""
from pathlib import Path
import sys
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from simulate_tournament import WorldCupSimulator, OUTPUTS
from generate_most_likely_path import outcome_probabilities


def top_scores(hxg, axg, n=5):
    op = outcome_probabilities(hxg, axg)
    scores = sorted(op['matrix'].items(), key=lambda kv: kv[1], reverse=True)[:n]
    return '; '.join([f"{h}-{a} ({p:.1%})" for (h,a), p in scores]), op


def main():
    sim = WorldCupSimulator(seed=42)
    matches = pd.read_csv(OUTPUTS / 'most_likely_tournament_matches.csv')
    rows = []
    for _, r in matches.iterrows():
        hxg, axg = sim.expected_goals(r['home'], r['away'], knockout=(r['stage'] != 'Group Stage'))
        top, op = top_scores(hxg, axg, n=5)
        rows.append({
            'match_number': r['match_number'],
            'stage': r['stage'],
            'home': r['home'],
            'away': r['away'],
            'central_score': f"{int(r['home_goals'])}-{int(r['away_goals'])}",
            'home_xg': round(hxg, 2),
            'away_xg': round(axg, 2),
            'home_win_prob': round(op['home'], 3),
            'draw_prob': round(op['draw'], 3),
            'away_win_prob': round(op['away'], 3),
            'top_5_scorelines': top,
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUTS / 'most_likely_match_score_distributions.csv', index=False)
    print(out[out.stage != 'Group Stage'].tail(15).to_string(index=False))

if __name__ == '__main__':
    main()

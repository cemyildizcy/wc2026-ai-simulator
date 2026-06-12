"""Generate a deterministic most-likely 2026 World Cup path.

Uses the calibrated simulator's expected goals and team_power, but avoids single-run
Monte Carlo randomness. This is the bracket to present as the model's central forecast.
"""

from pathlib import Path
import math
import pandas as pd

from simulate_tournament import WorldCupSimulator, OUTPUTS, match_results_to_df, MatchResult, PLAYED_MATCH_RESULTS


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def outcome_probabilities(hxg: float, axg: float, max_goals: int = 7) -> dict:
    """Return home/draw/away probabilities from a Poisson score matrix."""
    probs = {(i, j): poisson_pmf(i, hxg) * poisson_pmf(j, axg) for i in range(max_goals + 1) for j in range(max_goals + 1)}
    total = sum(probs.values())
    # normalize because matrix truncates 8+ goal tail
    probs = {k: v / total for k, v in probs.items()}
    return {
        'home': sum(v for (i, j), v in probs.items() if i > j),
        'draw': sum(v for (i, j), v in probs.items() if i == j),
        'away': sum(v for (i, j), v in probs.items() if i < j),
        'matrix': probs,
    }


def most_likely_scoreline(hxg: float, axg: float, desired_outcome: str | None = None, max_goals: int = 7) -> tuple[int, int, float]:
    """Most probable scoreline, optionally constrained to home/draw/away result."""
    op = outcome_probabilities(hxg, axg, max_goals=max_goals)
    matrix = op['matrix']
    if desired_outcome is None:
        desired_outcome = max(['home', 'draw', 'away'], key=lambda x: op[x])

    def ok(score):
        i, j = score
        return (desired_outcome == 'home' and i > j) or (desired_outcome == 'draw' and i == j) or (desired_outcome == 'away' and i < j)
    candidates = {s: p for s, p in matrix.items() if ok(s)}
    if not candidates:
        candidates = matrix
    (hg, ag), prob = max(candidates.items(), key=lambda kv: kv[1])
    return hg, ag, prob


def choose_group_outcome(sim: WorldCupSimulator, home: str, away: str, hxg: float, axg: float) -> tuple[str, dict]:
    """Calibrated central W/D/L choice for group-stage presentation.

    Pure modal scoreline creates too many 1-1 draws. Pure max W/D/L creates no
    draws. This middle rule only selects a draw when the teams are close and the
    draw probability is competitive with the strongest win probability.
    """
    op = outcome_probabilities(hxg, axg)
    best_win = max(op['home'], op['away'])
    xg_gap = abs(hxg - axg)
    power_gap = abs(sim.team[home]['team_power'] - sim.team[away]['team_power'])
    elo_gap = abs(sim.team[home]['elo_rating'] - sim.team[away]['elo_rating'])

    draw_is_competitive = (
        op['draw'] >= 0.255
        and (best_win - op['draw']) <= 0.165
        and xg_gap <= 0.28
        and power_gap <= 0.13
        and elo_gap <= 190
    )
    if draw_is_competitive:
        return 'draw', op
    return ('home' if op['home'] >= op['away'] else 'away'), op


def deterministic_winner(sim: WorldCupSimulator, home: str, away: str, hg: int, ag: int) -> str | None:
    if hg > ag:
        return home
    if ag > hg:
        return away
    # Central forecast tie-breaker: team_power, not random penalties.
    return home if sim.team[home]['team_power'] >= sim.team[away]['team_power'] else away


def simulate_group_stage_deterministic(sim: WorldCupSimulator):
    match_results = []
    standings = {
        team: {"team": team, "group": group, "played": 0, "wins": 0, "draws": 0, "losses": 0,
               "gf": 0, "ga": 0, "gd": 0, "points": 0}
        for group, teams in sim.groups.items() for team in teams
    }
    for m in sim.bracket['group_stage']['matches']:
        home, away = m['home_team'], m['away_team']
        match_number = m['match_number']
        hxg, axg = sim.expected_goals(home, away)
        if match_number in PLAYED_MATCH_RESULTS:
            expected_home, expected_away, hg, ag = PLAYED_MATCH_RESULTS[match_number]
            if (home, away) != (expected_home, expected_away):
                raise ValueError(
                    f"Played result mismatch for match {match_number}: "
                    f"bracket has {home} vs {away}, fixed result has {expected_home} vs {expected_away}"
                )
            score_prob = None
            decided = 'played_result'
        else:
            desired_outcome, op = choose_group_outcome(sim, home, away, hxg, axg)
            hg, ag, score_prob = most_likely_scoreline(hxg, axg, desired_outcome)
            decided = (
                f'calibrated_group_outcome={desired_outcome}; '
                f'most_likely_score_prob={score_prob:.3f}; '
                f'W/D/L={op["home"]:.2f}/{op["draw"]:.2f}/{op["away"]:.2f}'
            )
        winner = None if hg == ag else (home if hg > ag else away)
        match_results.append(MatchResult(home, away, hg, ag, winner, 'Group Stage', match_number, decided, hxg, axg))
        h, a = standings[home], standings[away]
        h['played'] += 1; a['played'] += 1
        h['gf'] += hg; h['ga'] += ag; a['gf'] += ag; a['ga'] += hg
        h['gd'] = h['gf'] - h['ga']; a['gd'] = a['gf'] - a['ga']
        if hg > ag:
            h['wins'] += 1; a['losses'] += 1; h['points'] += 3
        elif ag > hg:
            a['wins'] += 1; h['losses'] += 1; a['points'] += 3
        else:
            h['draws'] += 1; a['draws'] += 1; h['points'] += 1; a['points'] += 1
    table = pd.DataFrame(standings.values())
    table['team_power'] = table['team'].map(lambda t: sim.team[t]['team_power'])
    ranked = []
    for group, gdf in table.groupby('group'):
        gdf = gdf.sort_values(['points','gd','gf','team_power'], ascending=[False,False,False,False]).copy()
        gdf['rank'] = range(1, len(gdf)+1)
        ranked.append(gdf)
    return match_results, pd.concat(ranked, ignore_index=True)


def simulate_knockout_deterministic(sim: WorldCupSimulator, qualifier_slots):
    results = []
    winners = {}
    r32 = sim.resolve_round_of_32_slots(qualifier_slots)
    for match_id, home, away, hs, aws in r32:
        hxg, axg = sim.expected_goals(home, away, knockout=True)
        op = outcome_probabilities(hxg, axg)
        desired = max(['home', 'draw', 'away'], key=lambda x: op[x])
        hg, ag, score_prob = most_likely_scoreline(hxg, axg, desired)
        winner = deterministic_winner(sim, home, away, hg, ag)
        decided = f"most_likely_score_prob={score_prob:.3f}; W/D/L={op['home']:.2f}/{op['draw']:.2f}/{op['away']:.2f}; slots {hs} vs {aws}"
        results.append(MatchResult(home, away, hg, ag, winner, 'Round of 32', match_id, decided, hxg, axg))
        winners[f'W{match_id}'] = winner
    for stage_key, stage_name in [
        ('round_of_16','Round of 16'), ('quarter_finals','Quarter-final'), ('semi_finals','Semi-final'),
        ('third_place_match','Third-place Match'), ('final','Final')
    ]:
        stage_matches = sim.bracket['knockout_stage'][stage_key]
        if isinstance(stage_matches, dict):
            stage_matches = [stage_matches]
        for m in stage_matches:
            home, away = winners[m['home']], winners[m['away']]
            hxg, axg = sim.expected_goals(home, away, knockout=True)
            op = outcome_probabilities(hxg, axg)
            desired = max(['home', 'draw', 'away'], key=lambda x: op[x])
            hg, ag, score_prob = most_likely_scoreline(hxg, axg, desired)
            winner = deterministic_winner(sim, home, away, hg, ag)
            decided = f"most_likely_score_prob={score_prob:.3f}; W/D/L={op['home']:.2f}/{op['draw']:.2f}/{op['away']:.2f}"
            results.append(MatchResult(home, away, hg, ag, winner, stage_name, m['match'], decided, hxg, axg))
            winners[f"W{m['match']}"] = winner
            if stage_name == 'Semi-final':
                winners[f"L{m['match']}"] = away if winner == home else home
    return results


def main():
    sim = WorldCupSimulator(seed=42)
    gm, standings = simulate_group_stage_deterministic(sim)
    slots = sim.qualifiers_from_groups(standings)
    km = simulate_knockout_deterministic(sim, slots)
    all_matches = gm + km
    match_results_to_df(all_matches).to_csv(OUTPUTS / 'most_likely_tournament_matches.csv', index=False)
    standings.to_csv(OUTPUTS / 'most_likely_group_standings.csv', index=False)
    final = [m for m in km if m.stage == 'Final'][0]
    print('Most likely champion:', final.winner)
    print('Final:', final.home, final.home_goals, '-', final.away_goals, final.away)
    print(match_results_to_df(km)[['match_number','stage','home','away','home_goals','away_goals','winner']].to_string(index=False))


if __name__ == '__main__':
    main()

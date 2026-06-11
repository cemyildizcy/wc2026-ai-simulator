# WC 2026 AI Simulator — Final Modeling Report

## Model Status

Final calibrated V1 model completed and reproducible.

Run command:

```bash
python src/run_final_pipeline.py
```

## Inputs

Final modeling table:

```text
data/final/team_features_2026_enriched.csv
```

Shape:

```text
48 teams × 55 columns
```

Main data sources:

- User-provided 2026 World Cup archive data
- EA FC 25 male player ratings
- StatsBomb Open Data: World Cup 2018/2022 event data
- International historical results/form features
- Existing FIFA rank/ELO/team metadata from archive

## Feature Families

- Ranking strength: FIFA rank, ELO
- Current squad strength: EA FC top 11/top 23, attack/midfield/defense/GK, star player, depth
- Recent form: last 10/20 results, goals for/against, competitive win rate
- Tournament experience: WC titles, appearances, best finish, all-time win rate
- Event-level style: xG, xGA, shots, pass completion from StatsBomb WC 2018/2022
- Context: host, confederation, group difficulty, coach experience

## Calibration Choices

User feedback: single random run produced an unrealistic Uruguay–Ecuador final. Root cause was not data failure alone; single-run Poisson simulation over-emphasized variance.

Fixes:

1. Main output changed from single random tournament to probability-based Monte Carlo + central most-likely path.
2. EA FC country mapping fixed: `Netherlands` in project equals `Holland` in EA FC dataset.
3. Current form and EA FC current squad quality weighted higher.
4. Historical success weight reduced.
5. Match score presentation changed from single rounded xG score to Poisson scoreline distribution.

## Score Model

Expected goals are computed from:

- attack strength
- opponent defense strength
- team power difference
- ELO difference
- host bonus

Scores use Poisson distribution.

For match reporting, model now exports:

- central score
- xG for both teams
- home/draw/away probability
- top 5 most likely scorelines

Output:

```text
outputs/most_likely_match_score_distributions.csv
```

## Tournament Model

- 72 group matches
- group ranking: points, goal difference, goals scored, team power fallback
- 32-team knockout bracket
- extra-time / penalties in random simulations
- 10,000 Monte Carlo runs

Important limitation:

FIFA public sources provide Round-of-32 third-place slot candidate pools, but not the full 495-combination allocation table. The project uses FIFA public slot pools plus a documented compatible fallback. This should be updated if FIFA releases the full table.

## Final Monte Carlo Top Champion Probabilities

- Argentina: 10.27%
- Germany: 9.70%
- Brazil: 9.28%
- Spain: 8.76%
- France: 8.47%
- England: 7.98%
- Portugal: 6.82%
- Belgium: 4.77%
- Netherlands: 3.24%
- Uruguay: 2.51%
- Croatia: 2.48%
- United States: 2.26%

Output:

```text
outputs/monte_carlo_team_probabilities.csv
```

## Central Most-Likely Bracket

Champion:

```text
Brazil
```

Final:

```text
Brazil 1-0 Argentina
```

Final distribution:

- Brazil xG: 1.36
- Argentina xG: 1.28
- Brazil win probability: 38.7%
- Draw probability: 26.1%
- Argentina win probability: 35.2%

Top final scorelines:

- 1-1: 12.4%
- 1-0: 9.7%
- 0-1: 9.1%
- 2-1: 8.4%
- 1-2: 8.0%

Output:

```text
outputs/most_likely_tournament_matches.csv
```

## Interpretation

The model does not claim one deterministic truth. It provides:

1. probability-based tournament outcomes from Monte Carlo
2. a central bracket path for storytelling
3. match-level score distributions for uncertainty

This is better for a realistic sports analytics project than claiming exact scores.

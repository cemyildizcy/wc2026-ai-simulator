# 2026 FIFA World Cup AI Simulator

Interactive data science project that simulates the 2026 FIFA World Cup with 48 teams using team-strength features, a Poisson expected-goals model, and 10,000 Monte Carlo tournament runs.

The project includes:

- End-to-end data preparation scripts
- EA FC 25 squad-strength feature engineering
- StatsBomb World Cup xG/style features
- 48-team group and knockout tournament simulation
- Monte Carlo champion/stage probabilities
- Most-likely bracket path generation
- Match scoreline probability distributions
- Turkish Streamlit dashboard for interactive exploration

> This is a probability model, not a betting tool or a claim of certain predictions.

---

## Dashboard

Run the dashboard locally:

```bash
streamlit run dashboard/app.py
```

Dashboard pages:

- Genel Bakış — tournament summary and top probabilities
- Takım İnceleme — team-level probabilities, strengths, squad details
- Maç İnceleme — W/D/L probabilities, xG, top scorelines
- Grup Aşaması — 12 group tables and group strength comparison
- Eleme Turu — most-likely knockout path
- Metodoloji — data sources, model logic, limitations

---

## Project Structure

```text
dashboard/
  app.py                              # Streamlit dashboard

src/
  pipeline.py                         # Full data preparation pipeline
  add_eafc25_features.py              # EA FC squad feature builder
  simulate_tournament.py              # Monte Carlo simulator
  generate_most_likely_path.py        # Central bracket path
  generate_match_score_distributions.py
  create_eda_figures.py
  run_final_pipeline.py               # Final reproducible run script

data/
  raw/                                # Raw/local source data
  processed/                          # Processed intermediate data
  final/                              # Final model-ready datasets

outputs/
  *.csv                               # Generated simulation outputs
  figures/                            # Generated charts

reports/
  *.md                                # Data/model/simulation reports
```

---

## Installation

Recommended Python version: 3.10+

```bash
git clone https://github.com/cemyildizcy/wc2026-ai-simulator.git
cd wc2026-ai-simulator
python -m venv .venv
source .venv/bin/activate  # Windows Git Bash
pip install -r requirements.txt
```

---

## How to Run

Run the final model pipeline:

```bash
python src/run_final_pipeline.py
```

This executes:

1. EA FC 25 team feature generation
2. Final enriched dataset refresh
3. Calibrated Monte Carlo tournament simulation
4. Most-likely bracket path generation
5. Match scoreline distribution generation
6. EDA/chart output generation

Then run the dashboard:

```bash
streamlit run dashboard/app.py
```

Note: `src/run_final_pipeline.py` assumes the required local source datasets already exist under `data/`. Use `src/pipeline.py` for the broader data preparation workflow.

---

## Data Sources

Feature families used by the model:

- FIFA ranking / snapshot features
- ELO-style team rating proxy
- EA FC 25 player ratings and squad structure
- StatsBomb open World Cup 2018/2022 match features
- World Cup historical performance
- Recent international form
- Qualification and group-difficulty features
- Coach experience proxy

EA FC 25 player files are large and are not committed to GitHub. Download them locally and place them under:

```text
data/raw/external/eafc25/
```

---

## Model Summary

### Team Power Score

The team power score combines:

- FIFA rank
- ELO rating
- EA FC 25 squad strength
- Recent international form
- World Cup historical pedigree
- Squad market value
- StatsBomb xG/xGA indicators
- Coach World Cup experience

### Match Model

Match scores are generated using a Poisson expected-goals model.

For each matchup:

- Home/away expected goals are calculated from relative team strength
- Scorelines are sampled from Poisson distributions
- Win/draw/loss probabilities are aggregated from the score distribution
- Knockout draws are resolved with extra-time/penalty logic

### Tournament Model

The tournament format follows the expanded 48-team structure:

- 12 groups × 4 teams
- Top 2 from each group advance
- Best 8 third-place teams advance
- 32-team knockout bracket
- 104 total matches

Monte Carlo simulation runs the tournament 10,000 times and estimates:

- Champion probability
- Runner-up probability
- Third-place probability
- Knockout/quarter/semi/final reach probabilities
- Final matchup probabilities

---

## Current Results

Top champion probabilities from the current run:

```text
Argentina      10.27%
Germany         9.70%
Brazil          9.28%
Spain           8.76%
France          8.47%
England         7.98%
Portugal        6.82%
Belgium         4.77%
Netherlands     3.24%
Uruguay         2.51%
```

Central most-likely final:

```text
Brazil 1-0 Argentina
```

But the final is highly uncertain. Top scoreline distribution:

```text
1-1: 12.4%
1-0: 9.7%
0-1: 9.1%
2-1: 8.4%
1-2: 8.0%
```

This means the model should be read as a probability distribution, not as one exact-score prediction.

---

## Key Output Files

```text
outputs/monte_carlo_team_probabilities.csv
outputs/monte_carlo_final_pair_probabilities.csv
outputs/most_likely_tournament_matches.csv
outputs/most_likely_group_standings.csv
outputs/most_likely_match_score_distributions.csv
outputs/team_power_rankings.csv
```

Figures:

```text
outputs/figures/champion_probabilities_top15.png
outputs/figures/team_power_top15.png
outputs/figures/stage_reach_probabilities_top10.png
outputs/figures/final_scoreline_distribution.png
outputs/figures/most_likely_knockout_path.png
```

Reports:

```text
reports/data_quality_report.md
reports/eafc25_feature_report.md
reports/final_model_report.md
reports/simulation_report.md
```

---

## Limitations

Important limitations:

- The full official FIFA 2026 third-place allocation matrix was not publicly accessible during this build. The simulator uses public slot pools plus a documented compatible fallback.
- Group tie-breakers approximate FIFA logic with points, goal difference, goals for, and model power fallback. Exact head-to-head, fair-play, and drawing-of-lots logic is not fully modeled.
- EA FC 25 ratings are game-derived proxies and may not reflect real 2025/2026 player form.
- The Poisson model assumes independent goal scoring and does not model tactical game state, red cards, injuries, weather, travel, fatigue, or lineup changes.
- StatsBomb open data is limited to recent World Cup editions.
- Model probabilities are sensitive to feature weighting and data quality.
- This project is for portfolio/data-science demonstration, not gambling or financial decision-making.

---

## Author

Built by [Cem Yıldız](https://github.com/cemyildizcy) — Data Science & AI.

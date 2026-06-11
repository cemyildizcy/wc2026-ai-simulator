# 2026 FIFA World Cup AI Simulator — Data Quality Report

Generated: 2026-06-10 21:33

## 1. Data Sources

- **Archive data**: 12 CSV files in data/raw/archive/
- **StatsBomb WC data**: ✅ Downloaded
- **International Results**: ✅ Downloaded
- **FIFA Rankings Historical**: ❌ Not available
- **EA FC 25 Players**: ❌ Not available (needs Kaggle)

## 2. Row Counts per File

### Raw Archive Files
- `wc_2026_group_difficulty.csv`: 48 rows × 15 cols
- `wc_2026_groups.csv`: 48 rows × 13 cols
- `wc_2026_qualifying_summary.csv`: 47 rows × 18 cols
- `wc_2026_teams_snapshot.csv`: 50 rows × 11 cols
- `wc_coaches_2026.csv`: 48 rows × 13 cols
- `wc_head_to_head.csv`: 61 rows × 16 cols
- `wc_matches_historical.csv`: 117 rows × 18 cols
- `wc_prediction_features_2026.csv`: 48 rows × 23 cols
- `wc_team_alltime_stats.csv`: 43 rows × 22 cols
- `wc_team_appearances.csv`: 193 rows × 20 cols
- `wc_top_scorers_by_edition.csv`: 71 rows × 12 cols
- `wc_tournaments.csv`: 22 rows × 15 cols

### External Downloads
- `international_results.csv`: ~49472 rows × 9 cols
- `statsbomb_wc2018_matches.csv`: ~64 rows × 55 cols
- `statsbomb_wc2022_matches.csv`: ~64 rows × 55 cols
- `statsbomb_wc_team_stats.csv`: ~256 rows × 11 cols

### Processed Files
- `alltime_stats_clean.csv`: 43 rows × 22 cols
- `appearances_clean.csv`: 193 rows × 20 cols
- `coaches_clean.csv`: 48 rows × 13 cols
- `group_difficulty_clean.csv`: 48 rows × 15 cols
- `groups_clean.csv`: 48 rows × 13 cols
- `head_to_head_clean.csv`: 61 rows × 16 cols
- `prediction_features_clean.csv`: 48 rows × 23 cols
- `qualifying_clean.csv`: 47 rows × 18 cols
- `recent_form_features.csv`: 48 rows × 10 cols
- `statsbomb_team_features.csv`: 48 rows × 9 cols
- `teams_snapshot_clean.csv`: 48 rows × 11 cols
- `top_scorers_clean.csv`: 71 rows × 12 cols
- `tournaments_clean.csv`: 22 rows × 15 cols
- `wc_matches_historical_clean.csv`: 117 rows × 18 cols

### Final Output
- `team_features_2026.csv`: 48 rows × 37 cols
- `historical_matches.csv`: 49472 rows
- `wc2026_bracket.json`: 72 group + 32 knockout matches

## 3. Team Name Standardization Mapping

```
  Antigua and Barbuda → Antigua & Barbuda
  Bosnia Herzegovina → Bosnia-Herzegovina
  Bosnia and Herzegovina → Bosnia-Herzegovina
  Cabo Verde → Cape Verde
  China PR → China
  Congo DR → DR Congo
  Cote d'Ivoire → Ivory Coast
  Czech Republic → Czechia
  Czechia → Czechia
  Côte d'Ivoire → Ivory Coast
  Dem. Rep. of the Congo → DR Congo
  Eswatini → Eswatini
  IR Iran → Iran
  Islamic Republic of Iran → Iran
  Korea DPR → North Korea
  Korea Republic → South Korea
  Republic of Korea → South Korea
  Saint Kitts and Nevis → St. Kitts and Nevis
  Swaziland → Eswatini
  São Tomé and Príncipe → São Tomé e Príncipe
  Trinidad and Tobago → Trinidad & Tobago
  Turkiye → Turkey
  Türkiye → Turkey
  USA → United States
  United States of America → United States
```

## 4. Missing Values in Final Dataset

No missing values in final dataset (all filled with confederation/global median)

## 5. Duplicate Team Fix

- Fixed duplicate entries for: ['Morocco', 'Senegal']
- Kept first occurrence, removed 2 duplicate rows

## 6. Summary Statistics (Key Features)

### fifa_rank
  - Mean: 33.58, Std: 24.26
  - Min: 1.00, Max: 88.00
  - Median: 28.50
### elo_rating
  - Mean: 1756.04, Std: 138.67
  - Min: 1480.00, Max: 2030.00
  - Median: 1740.00
### wc_titles
  - Mean: 0.38, Std: 1.06
  - Min: 0.00, Max: 5.00
  - Median: 0.00
### wc_appearances
  - Mean: 7.21, Std: 5.95
  - Min: 0.00, Max: 22.00
  - Median: 6.00
### squad_market_value_eur_m
  - Mean: 445.42, Std: 379.29
  - Min: 35.00, Max: 1350.00
  - Median: 280.00
### alltime_win_rate
  - Mean: 0.34, Std: 0.15
  - Min: 0.00, Max: 0.67
  - Median: 0.29

## 7. Feature Filling Strategy

For features with missing values (e.g., StatsBomb data for teams not in WC 2018/2022):
1. First attempt: confederation median (e.g., UEFA median for UEFA teams)
2. Fallback: global median across all 48 teams
3. Final fallback: 0 (only if all values missing)

## 8. Files Generated

### data/processed/
- `alltime_stats_clean.csv`
- `appearances_clean.csv`
- `coaches_clean.csv`
- `group_difficulty_clean.csv`
- `groups_clean.csv`
- `head_to_head_clean.csv`
- `prediction_features_clean.csv`
- `qualifying_clean.csv`
- `recent_form_features.csv`
- `statsbomb_team_features.csv`
- `teams_snapshot_clean.csv`
- `top_scorers_clean.csv`
- `tournaments_clean.csv`
- `wc2026_bracket.json`
- `wc_matches_historical_clean.csv`

### data/final/
- `historical_matches.csv`
- `team_features_2026.csv`
- `wc2026_bracket.json`
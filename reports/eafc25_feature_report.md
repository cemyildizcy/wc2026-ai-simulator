# EA FC 25 Feature Report

Generated EA FC 25 team-strength features from `male_players.csv`.

## Input
- Raw players: `C:\Users\cemyi\Desktop\wc2026-ai-simulator\data\raw\external\eafc25\male_players.csv`
- Player rows: 16,161
- Project teams: 48

## Output
- Processed EA FC features: `C:\Users\cemyi\Desktop\wc2026-ai-simulator\data\processed\eafc25_team_features.csv`
- Enriched final dataset: `C:\Users\cemyi\Desktop\wc2026-ai-simulator\data\final\team_features_2026_enriched.csv`
- Shape: 48 rows × 70 columns

## Nation Mapping Used
- Bosnia-Herzegovina → Bosnia and Herzegovina
- Cape Verde → Cape Verde Islands
- Czechia → Czech Republic
- DR Congo → Congo DR
- Ivory Coast → Côte d'Ivoire
- South Korea → Korea Republic
- Netherlands → Holland

## Teams unavailable in EA FC 25
- Qatar

Missing numeric EA FC values were filled by confederation median, then global median.

## EA FC Feature Columns
- `eafc_player_count`
- `eafc_top11_avg_ovr`
- `eafc_top23_avg_ovr`
- `eafc_attack_rating`
- `eafc_midfield_rating`
- `eafc_defense_rating`
- `eafc_goalkeeper_rating`
- `eafc_squad_depth`
- `eafc_star_player_rating`
- `eafc_star_player`
- `eafc_avg_age_top23`
- `eafc_young_talent_score`
- `eafc_pace_avg_top11`
- `eafc_shooting_avg_top11`
- `eafc_passing_avg_top11`
- `eafc_dribbling_avg_top11`
- `eafc_defending_avg_top11`
- `eafc_physical_avg_top11`

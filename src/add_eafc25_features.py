import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
players_path = ROOT / 'data/raw/external/eafc25/male_players.csv'
team_path = ROOT / 'data/final/team_features_2026.csv'
processed_out = ROOT / 'data/processed/eafc25_team_features.csv'
final_out = ROOT / 'data/final/team_features_2026_enriched.csv'
report_path = ROOT / 'reports/eafc25_feature_report.md'

players = pd.read_csv(players_path)
teams = pd.read_csv(team_path)

# Normalize relevant numeric columns
rating_cols = ['OVR','PAC','SHO','PAS','DRI','DEF','PHY','Age','Acceleration','Sprint Speed','Finishing','Shot Power','Vision','Short Passing','Long Passing','Ball Control','Interceptions','Def Awareness','Standing Tackle','Sliding Tackle','Stamina','Strength','GK Diving','GK Handling','GK Kicking','GK Positioning','GK Reflexes']
for c in rating_cols:
    if c in players.columns:
        players[c] = pd.to_numeric(players[c], errors='coerce')

# Map project team names -> EA FC Nation names
nation_map = {
    'Bosnia-Herzegovina': 'Bosnia and Herzegovina',
    'Cape Verde': 'Cape Verde Islands',
    'Czechia': 'Czech Republic',
    'DR Congo': 'Congo DR',
    'Ivory Coast': "Côte d'Ivoire",
    'South Korea': 'Korea Republic',
    'Netherlands': 'Holland',
    # Qatar absent from EA FC 25 male player dataset; filled later.
}

def team_players(team):
    nation = nation_map.get(team, team)
    return players[players['Nation'] == nation].copy()

attack_positions = {'ST','CF','LW','RW','LM','RM'}
mid_positions = {'CM','CDM','CAM','LM','RM'}
def_positions = {'CB','LB','RB','LWB','RWB'}
gk_positions = {'GK'}

def pos_base(pos):
    if pd.isna(pos):
        return ''
    return str(pos).split(',')[0].strip()

def mean_top(df, col, n):
    vals = df[col].dropna().sort_values(ascending=False).head(n)
    return vals.mean() if len(vals) else np.nan

def feature_row(team):
    df = team_players(team)
    if df.empty:
        return {'team': team, 'eafc_player_count': 0}
    df['pos_base'] = df['Position'].apply(pos_base)
    df = df.sort_values('OVR', ascending=False)
    top11 = df.head(11)
    top23 = df.head(23)
    attack = df[df['pos_base'].isin(attack_positions)]
    midfield = df[df['pos_base'].isin(mid_positions)]
    defense = df[df['pos_base'].isin(def_positions)]
    gk = df[df['pos_base'].isin(gk_positions)]
    u23 = df[df['Age'] <= 23]
    starters_avg = top11['OVR'].mean()
    bench_avg = df.iloc[11:23]['OVR'].mean() if len(df) > 11 else np.nan
    star = df.iloc[0]
    return {
        'team': team,
        'eafc_player_count': len(df),
        'eafc_top11_avg_ovr': starters_avg,
        'eafc_top23_avg_ovr': top23['OVR'].mean(),
        'eafc_attack_rating': mean_top(attack, 'OVR', 4),
        'eafc_midfield_rating': mean_top(midfield, 'OVR', 4),
        'eafc_defense_rating': mean_top(defense, 'OVR', 4),
        'eafc_goalkeeper_rating': mean_top(gk, 'OVR', 2),
        'eafc_squad_depth': starters_avg - bench_avg if pd.notna(starters_avg) and pd.notna(bench_avg) else np.nan,
        'eafc_star_player_rating': star['OVR'],
        'eafc_star_player': star['Name'],
        'eafc_avg_age_top23': top23['Age'].mean(),
        'eafc_young_talent_score': mean_top(u23, 'OVR', 5),
        'eafc_pace_avg_top11': top11['PAC'].mean(),
        'eafc_shooting_avg_top11': top11['SHO'].mean(),
        'eafc_passing_avg_top11': top11['PAS'].mean(),
        'eafc_dribbling_avg_top11': top11['DRI'].mean(),
        'eafc_defending_avg_top11': top11['DEF'].mean(),
        'eafc_physical_avg_top11': top11['PHY'].mean(),
    }

rows = [feature_row(t) for t in teams['team']]
eafc = pd.DataFrame(rows)

# Fill numeric missing with confederation median then global median after joining confed
feature_numeric = [c for c in eafc.columns if c not in ['team','eafc_star_player']]
tmp = teams[['team','confederation']].merge(eafc, on='team', how='left')
for c in feature_numeric:
    tmp[c] = pd.to_numeric(tmp[c], errors='coerce')
    tmp[c] = tmp.groupby('confederation')[c].transform(lambda s: s.fillna(s.median()))
    tmp[c] = tmp[c].fillna(tmp[c].median())
# star player string fill
players_by_team = eafc.set_index('team')['eafc_star_player'].to_dict()
tmp['eafc_star_player'] = tmp['team'].map(players_by_team).fillna('Unavailable in EA FC 25')

eafc_final = tmp.drop(columns=['confederation'])
eafc_final.to_csv(processed_out, index=False)

# Merge with final existing dataset
merged = teams.merge(eafc_final, on='team', how='left')
merged.to_csv(final_out, index=False)

unavailable = eafc[eafc['eafc_player_count'].fillna(0).eq(0)]['team'].tolist()
report = f"""# EA FC 25 Feature Report

Generated EA FC 25 team-strength features from `male_players.csv`.

## Input
- Raw players: `{players_path}`
- Player rows: {len(players):,}
- Project teams: {len(teams)}

## Output
- Processed EA FC features: `{processed_out}`
- Enriched final dataset: `{final_out}`
- Shape: {merged.shape[0]} rows × {merged.shape[1]} columns

## Nation Mapping Used
"""
for k,v in nation_map.items():
    report += f"- {k} → {v}\n"
report += f"\n## Teams unavailable in EA FC 25\n- {', '.join(unavailable) if unavailable else 'None'}\n"
report += "\nMissing numeric EA FC values were filled by confederation median, then global median.\n"
report += "\n## EA FC Feature Columns\n"
for c in eafc_final.columns:
    if c != 'team':
        report += f"- `{c}`\n"

report_path.write_text(report, encoding='utf-8')

print('EA FC features saved:', processed_out)
print('Enriched final dataset saved:', final_out)
print('Report saved:', report_path)
print('Shape:', merged.shape)
print('Unavailable teams:', unavailable)
print('\nTop 10 by EA FC top11 average:')
print(merged.sort_values('eafc_top11_avg_ovr', ascending=False)[['team','eafc_player_count','eafc_top11_avg_ovr','eafc_star_player','eafc_star_player_rating']].head(10).to_string(index=False))

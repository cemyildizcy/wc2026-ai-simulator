#!/usr/bin/env python3
"""
Complete data pipeline for 2026 FIFA World Cup AI Simulator.
Steps: Download external data → Clean → Process → Build bracket → Merge → Report
"""

import os
import sys
import json
import warnings
import traceback
from pathlib import Path

import pandas as pd
import numpy as np
import requests

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
RAW_ARCHIVE = ROOT / "data" / "raw" / "archive"
RAW_EXT = ROOT / "data" / "raw" / "external"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
FINAL = ROOT / "data" / "final"
REPORTS = ROOT / "reports"

for d in [RAW_EXT, INTERIM, PROCESSED, FINAL, REPORTS]:
    d.mkdir(parents=True, exist_ok=True)

report_lines = []
def log(msg):
    print(msg)
    report_lines.append(msg)

# ============================================================
# TEAM NAME STANDARDIZATION
# ============================================================
TEAM_NAME_MAP = {
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Korea DPR": "North Korea",
    "IR Iran": "Iran",
    "Islamic Republic of Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Congo DR": "DR Congo",
    "Dem. Rep. of the Congo": "DR Congo",
    "United States of America": "United States",
    "USA": "United States",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Czechia": "Czechia",
    "Czech Republic": "Czechia",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Bosnia Herzegovina": "Bosnia-Herzegovina",
    "Trinidad and Tobago": "Trinidad & Tobago",
    "Antigua and Barbuda": "Antigua & Barbuda",
    "Saint Kitts and Nevis": "St. Kitts and Nevis",
    "São Tomé and Príncipe": "São Tomé e Príncipe",
    "Cabo Verde": "Cape Verde",
    "China PR": "China",
    "Eswatini": "Eswatini",
    "Swaziland": "Eswatini",
}

def standardize_name(name):
    if pd.isna(name):
        return name
    name = str(name).strip()
    return TEAM_NAME_MAP.get(name, name)

def standardize_col(df, col='team'):
    if col in df.columns:
        df[col] = df[col].apply(standardize_name)
    return df

# ============================================================
# STEP 1: Download StatsBomb WC data
# ============================================================
log("\n" + "="*60)
log("STEP 1: StatsBomb World Cup Data")
log("="*60)

statsbomb_ok = False
try:
    from statsbombpy import sb
    
    # WC 2018 matches
    log("Fetching WC 2018 matches (comp=43, season=3)...")
    wc2018_matches = sb.matches(competition_id=43, season_id=3)
    log(f"  Got {len(wc2018_matches)} WC 2018 matches")
    wc2018_matches.to_csv(RAW_EXT / "statsbomb_wc2018_matches.csv", index=False)
    
    # WC 2022 matches
    log("Fetching WC 2022 matches (comp=43, season=106)...")
    wc2022_matches = sb.matches(competition_id=43, season_id=106)
    log(f"  Got {len(wc2022_matches)} WC 2022 matches")
    wc2022_matches.to_csv(RAW_EXT / "statsbomb_wc2022_matches.csv", index=False)
    
    all_matches = pd.concat([wc2018_matches, wc2022_matches], ignore_index=True)
    
    # Aggregate team-level stats from events
    log("Fetching event-level data for team stats aggregation...")
    team_stats_rows = []
    
    for idx, match in all_matches.iterrows():
        match_id = match['match_id']
        season = match.get('season', '')
        wc_year = 2018 if match.get('season_id', match.get('season', '')) in [3, '3', '2017/2018', '2018'] else 2022
        # Determine year from season_id if available
        if 'season_id' in match.index:
            wc_year = 2018 if match['season_id'] == 3 else 2022
        
        try:
            events = sb.events(match_id=match_id)
        except Exception as e:
            log(f"  Skipping match {match_id}: {e}")
            continue
        
        home_team = match['home_team']
        away_team = match['away_team']
        
        for team in [home_team, away_team]:
            team_events = events[events['team'] == team] if 'team' in events.columns else pd.DataFrame()
            opp_team = away_team if team == home_team else home_team
            
            shots = team_events[team_events['type'] == 'Shot'] if 'type' in team_events.columns else pd.DataFrame()
            passes = team_events[team_events['type'] == 'Pass'] if 'type' in team_events.columns else pd.DataFrame()
            pressures = team_events[team_events['type'] == 'Pressure'] if 'type' in team_events.columns else pd.DataFrame()
            
            goals = len(shots[shots['shot_outcome'] == 'Goal']) if 'shot_outcome' in shots.columns and len(shots) > 0 else 0
            xg = shots['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in shots.columns and len(shots) > 0 else np.nan
            
            pass_complete = len(passes[passes['pass_outcome'].isna()]) if 'pass_outcome' in passes.columns and len(passes) > 0 else 0
            pass_total = len(passes)
            pass_pct = (pass_complete / pass_total * 100) if pass_total > 0 else np.nan
            
            team_stats_rows.append({
                'match_id': match_id,
                'wc_year': wc_year,
                'team': standardize_name(team),
                'opponent': standardize_name(opp_team),
                'shots': len(shots),
                'goals': goals,
                'xG': xg,
                'passes_total': pass_total,
                'passes_completed': pass_complete,
                'pass_completion_pct': pass_pct,
                'pressures': len(pressures),
            })
        
        if (idx + 1) % 10 == 0:
            log(f"  Processed {idx+1}/{len(all_matches)} matches...")
    
    sb_team_stats = pd.DataFrame(team_stats_rows)
    sb_team_stats.to_csv(RAW_EXT / "statsbomb_wc_team_stats.csv", index=False)
    log(f"  Saved {len(sb_team_stats)} team-match rows to statsbomb_wc_team_stats.csv")
    statsbomb_ok = True

except Exception as e:
    log(f"  StatsBomb download FAILED: {e}")
    log(f"  {traceback.format_exc()}")
    log("  Will continue without StatsBomb data")

# ============================================================
# STEP 2: Download International Football Results
# ============================================================
log("\n" + "="*60)
log("STEP 2: International Football Results")
log("="*60)

intl_results_ok = False
intl_url = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
try:
    log(f"Downloading from {intl_url}...")
    r = requests.get(intl_url, timeout=30)
    r.raise_for_status()
    with open(RAW_EXT / "international_results.csv", 'wb') as f:
        f.write(r.content)
    intl_df = pd.read_csv(RAW_EXT / "international_results.csv")
    log(f"  Downloaded {len(intl_df)} rows, columns: {list(intl_df.columns)}")
    intl_results_ok = True
except Exception as e:
    log(f"  Download failed: {e}")
    # Try alternative URL
    alt_url = "https://raw.githubusercontent.com/martj42/international_results/refs/heads/master/results.csv"
    try:
        log(f"  Trying alternative: {alt_url}")
        r = requests.get(alt_url, timeout=30)
        r.raise_for_status()
        with open(RAW_EXT / "international_results.csv", 'wb') as f:
            f.write(r.content)
        intl_df = pd.read_csv(RAW_EXT / "international_results.csv")
        log(f"  Downloaded {len(intl_df)} rows")
        intl_results_ok = True
    except Exception as e2:
        log(f"  Alternative also failed: {e2}")

# ============================================================
# STEP 3: Download FIFA Rankings Historical
# ============================================================
log("\n" + "="*60)
log("STEP 3: FIFA Rankings Historical")
log("="*60)

rankings_ok = False
rankings_urls = [
    "https://raw.githubusercontent.com/cnc-club/fifa-rankings/master/ranking.csv",
    "https://raw.githubusercontent.com/cnc-club/fifa-rankings/refs/heads/master/ranking.csv",
]
for url in rankings_urls:
    try:
        log(f"Trying {url}...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(RAW_EXT / "fifa_rankings_historical.csv", 'wb') as f:
            f.write(r.content)
        rank_df = pd.read_csv(RAW_EXT / "fifa_rankings_historical.csv")
        log(f"  Downloaded {len(rank_df)} rows, columns: {list(rank_df.columns)}")
        rankings_ok = True
        break
    except Exception as e:
        log(f"  Failed: {e}")

# ============================================================
# STEP 4: EA FC 25 Player Data
# ============================================================
log("\n" + "="*60)
log("STEP 4: EA FC 25 Player Data")
log("="*60)

eafc_ok = False
eafc_urls = [
    "https://raw.githubusercontent.com/stefanoleone992/EA-Sports-FC-2025-Complete-Player-Dataset/refs/heads/master/data/male_players.csv",
    "https://raw.githubusercontent.com/stefanoleone992/EA-Sports-FC-2025-Complete-Player-Dataset/master/data/male_players.csv",
]

for url in eafc_urls:
    try:
        log(f"Trying {url}...")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(RAW_EXT / "eafc25_players.csv", 'wb') as f:
            f.write(r.content)
        eafc_df = pd.read_csv(RAW_EXT / "eafc25_players.csv", low_memory=False)
        log(f"  Downloaded {len(eafc_df)} rows")
        eafc_ok = True
        break
    except Exception as e:
        log(f"  Failed: {e}")

if not eafc_ok:
    log("  EA FC 25 data not available without Kaggle auth.")
    with open(RAW_EXT / "EAFC25_MANUAL_DOWNLOAD_NEEDED.txt", 'w') as f:
        f.write("EA FC 25 player data requires Kaggle authentication.\n")
        f.write("Download from: https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-2025-complete-player-dataset\n")
        f.write("Place male_players.csv in this directory as eafc25_players.csv\n")
    log("  Created placeholder note file")

# ============================================================
# STEP 5: Clean and Process All Data
# ============================================================
log("\n" + "="*60)
log("STEP 5a: Archive Data Cleaning")
log("="*60)

# Load all archive files
groups = pd.read_csv(RAW_ARCHIVE / "wc_2026_groups.csv")
difficulty = pd.read_csv(RAW_ARCHIVE / "wc_2026_group_difficulty.csv")
qualifying = pd.read_csv(RAW_ARCHIVE / "wc_2026_qualifying_summary.csv")
snapshot = pd.read_csv(RAW_ARCHIVE / "wc_2026_teams_snapshot.csv")
coaches = pd.read_csv(RAW_ARCHIVE / "wc_coaches_2026.csv")
h2h = pd.read_csv(RAW_ARCHIVE / "wc_head_to_head.csv")
hist_matches = pd.read_csv(RAW_ARCHIVE / "wc_matches_historical.csv")
pred_features = pd.read_csv(RAW_ARCHIVE / "wc_prediction_features_2026.csv")
alltime = pd.read_csv(RAW_ARCHIVE / "wc_team_alltime_stats.csv")
appearances = pd.read_csv(RAW_ARCHIVE / "wc_team_appearances.csv")
scorers = pd.read_csv(RAW_ARCHIVE / "wc_top_scorers_by_edition.csv")
tournaments = pd.read_csv(RAW_ARCHIVE / "wc_tournaments.csv")

# Fix duplicates in snapshot
log(f"  snapshot rows before dedup: {len(snapshot)}")
dup_teams = snapshot[snapshot.duplicated(subset=['team'], keep=False)]['team'].unique()
log(f"  Duplicate teams: {list(dup_teams)}")
snapshot = snapshot.drop_duplicates(subset=['team'], keep='first')
log(f"  snapshot rows after dedup: {len(snapshot)}")

# Standardize team names across all files
for df_name, df in [('groups', groups), ('difficulty', difficulty), ('qualifying', qualifying),
                     ('snapshot', snapshot), ('coaches', coaches), ('alltime', alltime),
                     ('pred_features', pred_features)]:
    standardize_col(df, 'team')

for col in ['home_team', 'away_team', 'winning_team']:
    if col in hist_matches.columns:
        hist_matches[col] = hist_matches[col].apply(standardize_name)

for col in ['team_a', 'team_b']:
    if col in h2h.columns:
        h2h[col] = h2h[col].apply(standardize_name)

# Get canonical 48 team list from groups
teams_48 = sorted(groups['team'].unique())
log(f"  48 WC teams: {len(teams_48)}")
assert len(teams_48) == 48, f"Expected 48 teams, got {len(teams_48)}"

# Handle N/A for host nations in qualifying
host_teams = groups[groups['is_host'] == 'Yes']['team'].tolist() if groups['is_host'].dtype == 'object' else groups[groups['is_host'] == True]['team'].tolist()
log(f"  Host teams: {host_teams}")

# Save cleaned archive files
groups.to_csv(PROCESSED / "groups_clean.csv", index=False)
difficulty.to_csv(PROCESSED / "group_difficulty_clean.csv", index=False)
qualifying.to_csv(PROCESSED / "qualifying_clean.csv", index=False)
snapshot.to_csv(PROCESSED / "teams_snapshot_clean.csv", index=False)
coaches.to_csv(PROCESSED / "coaches_clean.csv", index=False)
h2h.to_csv(PROCESSED / "head_to_head_clean.csv", index=False)
hist_matches.to_csv(PROCESSED / "wc_matches_historical_clean.csv", index=False)
pred_features.to_csv(PROCESSED / "prediction_features_clean.csv", index=False)
alltime.to_csv(PROCESSED / "alltime_stats_clean.csv", index=False)
appearances.to_csv(PROCESSED / "appearances_clean.csv", index=False)
scorers.to_csv(PROCESSED / "top_scorers_clean.csv", index=False)
tournaments.to_csv(PROCESSED / "tournaments_clean.csv", index=False)
log("  Saved all cleaned archive files to data/processed/")

# ============================================================
# STEP 5b: StatsBomb Processing
# ============================================================
log("\n" + "="*60)
log("STEP 5b: StatsBomb Processing")
log("="*60)

if statsbomb_ok:
    sb_stats = pd.read_csv(RAW_EXT / "statsbomb_wc_team_stats.csv")
    sb_stats['team'] = sb_stats['team'].apply(standardize_name)
    
    # Aggregate per team across all WC matches
    sb_agg = sb_stats.groupby('team').agg(
        wc_matches_sb=('match_id', 'count'),
        wc_goals_total=('goals', 'sum'),
        wc_xG_total=('xG', 'sum'),
        wc_xG_per_game=('xG', 'mean'),
        wc_shots_per_game=('shots', 'mean'),
        wc_pass_completion=('pass_completion_pct', 'mean'),
        wc_pressures_per_game=('pressures', 'mean'),
    ).reset_index()
    
    # Calculate xGA (opponent's xG)
    sb_stats_opp = sb_stats.rename(columns={'team': 'opponent_orig', 'opponent': 'team_orig'})
    xga = sb_stats.groupby('opponent').agg(wc_xGA_total=('xG', 'sum')).reset_index()
    xga.columns = ['team', 'wc_xGA_total']
    match_counts = sb_stats.groupby('opponent')['match_id'].count().reset_index()
    match_counts.columns = ['team', 'opp_matches']
    xga = xga.merge(match_counts, on='team')
    xga['wc_xGA_per_game'] = xga['wc_xGA_total'] / xga['opp_matches']
    
    sb_agg = sb_agg.merge(xga[['team', 'wc_xGA_per_game']], on='team', how='left')
    
    # Filter to 48 teams
    sb_features = pd.DataFrame({'team': teams_48})
    sb_features = sb_features.merge(sb_agg, on='team', how='left')
    
    sb_features.to_csv(PROCESSED / "statsbomb_team_features.csv", index=False)
    sb_available = sb_features[sb_features['wc_xG_per_game'].notna()]['team'].tolist()
    log(f"  StatsBomb features for {len(sb_available)}/{len(teams_48)} teams")
else:
    log("  Skipping StatsBomb processing (data not available)")
    sb_features = pd.DataFrame({'team': teams_48})

# ============================================================
# STEP 5c: International Results Processing
# ============================================================
log("\n" + "="*60)
log("STEP 5c: International Results Processing")
log("="*60)

if intl_results_ok:
    intl = pd.read_csv(RAW_EXT / "international_results.csv")
    intl['home_team'] = intl['home_team'].apply(standardize_name)
    intl['away_team'] = intl['away_team'].apply(standardize_name)
    intl['date'] = pd.to_datetime(intl['date'])
    
    # Save cleaned version for model training
    intl.to_csv(FINAL / "historical_matches.csv", index=False)
    log(f"  Total international results: {len(intl)}")
    
    form_rows = []
    cutoff_date = pd.Timestamp('2024-06-01')  # ~2 years before WC
    
    for team in teams_48:
        # Get all matches for this team
        home = intl[intl['home_team'] == team].copy()
        home['gf'] = home['home_score']
        home['ga'] = home['away_score']
        home['is_home'] = True
        home['opponent'] = home['away_team']
        
        away = intl[intl['away_team'] == team].copy()
        away['gf'] = away['away_score']
        away['ga'] = away['home_score']
        away['is_home'] = False
        away['opponent'] = away['home_team']
        
        tm = pd.concat([home, away]).sort_values('date', ascending=False)
        
        if len(tm) == 0:
            form_rows.append({'team': team})
            continue
        
        # Result
        tm['result'] = np.where(tm['gf'] > tm['ga'], 'W',
                        np.where(tm['gf'] == tm['ga'], 'D', 'L'))
        
        # Last 10 matches
        last10 = tm.head(10)
        last_10_wins = (last10['result'] == 'W').sum()
        last_10_draws = (last10['result'] == 'D').sum()
        last_10_losses = (last10['result'] == 'L').sum()
        last_10_gf = last10['gf'].sum()
        last_10_ga = last10['ga'].sum()
        
        # Last 20 win rate
        last20 = tm.head(20)
        last_20_win_rate = (last20['result'] == 'W').mean() if len(last20) > 0 else np.nan
        
        # Goals per game last 2 years
        recent = tm[tm['date'] >= cutoff_date]
        goals_per_game_2yr = recent['gf'].mean() if len(recent) > 0 else np.nan
        
        # Neutral ground win rate
        neutral = tm[tm.get('neutral', pd.Series(dtype=bool)) == True] if 'neutral' in tm.columns else pd.DataFrame()
        neutral_ground_win_rate = (neutral['result'] == 'W').mean() if len(neutral) > 5 else np.nan
        
        # Competitive match win rate (exclude friendlies)
        competitive = tm[~tm['tournament'].str.contains('Friendly', case=False, na=False)] if 'tournament' in tm.columns else tm
        competitive_win_rate = (competitive['result'] == 'W').mean() if len(competitive) > 0 else np.nan
        
        form_rows.append({
            'team': team,
            'last_10_wins': int(last_10_wins),
            'last_10_draws': int(last_10_draws),
            'last_10_losses': int(last_10_losses),
            'last_10_gf': int(last_10_gf),
            'last_10_ga': int(last_10_ga),
            'last_20_win_rate': round(last_20_win_rate, 3) if not pd.isna(last_20_win_rate) else np.nan,
            'goals_per_game_2yr': round(goals_per_game_2yr, 2) if not pd.isna(goals_per_game_2yr) else np.nan,
            'neutral_ground_win_rate': round(neutral_ground_win_rate, 3) if not pd.isna(neutral_ground_win_rate) else np.nan,
            'competitive_win_rate': round(competitive_win_rate, 3) if not pd.isna(competitive_win_rate) else np.nan,
        })
    
    form_df = pd.DataFrame(form_rows)
    form_df.to_csv(PROCESSED / "recent_form_features.csv", index=False)
    log(f"  Form features computed for {form_df['last_10_wins'].notna().sum()}/{len(teams_48)} teams")
else:
    log("  Skipping (no international results data)")
    form_df = pd.DataFrame({'team': teams_48})

# ============================================================
# STEP 5d: FIFA Rankings Processing
# ============================================================
log("\n" + "="*60)
log("STEP 5d: FIFA Rankings Processing")
log("="*60)

if rankings_ok:
    rank_raw = pd.read_csv(RAW_EXT / "fifa_rankings_historical.csv")
    log(f"  Raw rankings: {len(rank_raw)} rows, columns: {list(rank_raw.columns)}")
    
    # Identify column names (varies by source)
    # Common patterns: country_full/team, rank/ranking, rank_date/date, total_points
    team_col = None
    rank_col = None
    date_col = None
    
    for c in rank_raw.columns:
        cl = c.lower()
        if cl in ['country_full', 'team', 'country', 'team_name']:
            team_col = c
        elif cl in ['rank', 'ranking', 'position']:
            rank_col = c
        elif cl in ['rank_date', 'date', 'ranking_date']:
            date_col = c
    
    log(f"  Detected columns: team={team_col}, rank={rank_col}, date={date_col}")
    
    if team_col and rank_col and date_col:
        rank_raw[team_col] = rank_raw[team_col].apply(standardize_name)
        rank_raw[date_col] = pd.to_datetime(rank_raw[date_col])
        
        ranking_rows = []
        for team in teams_48:
            team_data = rank_raw[rank_raw[team_col] == team].sort_values(date_col, ascending=False)
            
            if len(team_data) == 0:
                ranking_rows.append({'team': team})
                continue
            
            current_rank = team_data.iloc[0][rank_col]
            
            # Rank 1 year ago
            one_yr = team_data[team_data[date_col] <= (team_data.iloc[0][date_col] - pd.DateOffset(years=1))]
            rank_1yr_ago = one_yr.iloc[0][rank_col] if len(one_yr) > 0 else np.nan
            rank_change_1yr = (rank_1yr_ago - current_rank) if not pd.isna(rank_1yr_ago) else np.nan
            
            # Rank 3 years ago
            three_yr = team_data[team_data[date_col] <= (team_data.iloc[0][date_col] - pd.DateOffset(years=3))]
            rank_3yr_ago = three_yr.iloc[0][rank_col] if len(three_yr) > 0 else np.nan
            rank_change_3yr = (rank_3yr_ago - current_rank) if not pd.isna(rank_3yr_ago) else np.nan
            
            best_rank = team_data[rank_col].min()
            
            # Volatility last 3 years
            recent_3y = team_data[team_data[date_col] >= (team_data.iloc[0][date_col] - pd.DateOffset(years=3))]
            rank_volatility = recent_3y[rank_col].std() if len(recent_3y) > 2 else np.nan
            
            ranking_rows.append({
                'team': team,
                'historical_rank_latest': int(current_rank),
                'rank_change_1yr': round(rank_change_1yr, 1) if not pd.isna(rank_change_1yr) else np.nan,
                'rank_change_3yr': round(rank_change_3yr, 1) if not pd.isna(rank_change_3yr) else np.nan,
                'best_rank_ever': int(best_rank),
                'rank_volatility': round(rank_volatility, 2) if not pd.isna(rank_volatility) else np.nan,
            })
        
        ranking_features = pd.DataFrame(ranking_rows)
        ranking_features.to_csv(PROCESSED / "ranking_momentum_features.csv", index=False)
        log(f"  Ranking features for {ranking_features['best_rank_ever'].notna().sum()}/{len(teams_48)} teams")
    else:
        log("  Could not identify ranking columns, skipping")
        rankings_ok = False
        ranking_features = pd.DataFrame({'team': teams_48})
else:
    log("  Skipping (no FIFA rankings data)")
    ranking_features = pd.DataFrame({'team': teams_48})

# ============================================================
# STEP 6: Build Tournament Bracket Structure
# ============================================================
log("\n" + "="*60)
log("STEP 6: Tournament Bracket Structure")
log("="*60)

# Group stage matches
group_matches = []
match_num = 1
for grp in sorted(groups['group'].unique()):
    grp_teams = groups[groups['group'] == grp]['team'].tolist()
    # Round-robin: each pair plays once
    for i in range(len(grp_teams)):
        for j in range(i+1, len(grp_teams)):
            group_matches.append({
                'match_number': match_num,
                'stage': 'Group Stage',
                'group': grp,
                'home_team': grp_teams[i],
                'away_team': grp_teams[j],
            })
            match_num += 1

bracket = {
    "tournament": "2026 FIFA World Cup",
    "hosts": ["United States", "Mexico", "Canada"],
    "format": {
        "groups": 12,
        "teams_per_group": 4,
        "advance_per_group": "Top 2 + 8 best 3rd-place teams",
        "total_teams": 48,
        "total_matches": 104
    },
    "group_stage": {
        "matches": group_matches,
        "total_matches": len(group_matches),
        "third_place_ranking_criteria": [
            "1. Points",
            "2. Goal difference",
            "3. Goals scored",
            "4. Fair play points",
            "5. Drawing of lots"
        ]
    },
    "knockout_stage": {
        "round_of_32": [
            {"match": 73, "home": "2A", "away": "2B", "description": "Runner-up A vs Runner-up B"},
            {"match": 74, "home": "1E", "away": "2F", "description": "Winner E vs Runner-up F"},
            {"match": 75, "home": "1F", "away": "2C", "description": "Winner F vs Runner-up C"},
            {"match": 76, "home": "1C", "away": "3D/E/F/I/J", "description": "Winner C vs Best 3rd"},
            {"match": 77, "home": "1I", "away": "3C/D/F/G/H", "description": "Winner I vs Best 3rd"},
            {"match": 78, "home": "2E", "away": "2I", "description": "Runner-up E vs Runner-up I"},
            {"match": 79, "home": "1A", "away": "3C/E/F/H/I", "description": "Winner A vs Best 3rd"},
            {"match": 80, "home": "1L", "away": "3E/H/I/J/K", "description": "Winner L vs Best 3rd"},
            {"match": 81, "home": "1D", "away": "3B/E/F/I/J", "description": "Winner D vs Best 3rd"},
            {"match": 82, "home": "1G", "away": "2H", "description": "Winner G vs Runner-up H"},
            {"match": 83, "home": "2K", "away": "2L", "description": "Runner-up K vs Runner-up L"},
            {"match": 84, "home": "1H", "away": "2J", "description": "Winner H vs Runner-up J"},
            {"match": 85, "home": "1B", "away": "3E/F/G/I/J", "description": "Winner B vs Best 3rd"},
            {"match": 86, "home": "1J", "away": "3C/D/F/G/H", "description": "Winner J vs Best 3rd"},
            {"match": 87, "home": "1K", "away": "3D/E/I/J/L", "description": "Winner K vs Best 3rd"},
            {"match": 88, "home": "2D", "away": "2G", "description": "Runner-up D vs Runner-up G"},
        ],
        "round_of_16": [
            {"match": 89, "home": "W73", "away": "W74"},
            {"match": 90, "home": "W75", "away": "W76"},
            {"match": 91, "home": "W77", "away": "W78"},
            {"match": 92, "home": "W79", "away": "W80"},
            {"match": 93, "home": "W81", "away": "W82"},
            {"match": 94, "home": "W83", "away": "W84"},
            {"match": 95, "home": "W85", "away": "W86"},
            {"match": 96, "home": "W87", "away": "W88"},
        ],
        "quarter_finals": [
            {"match": 97, "home": "W89", "away": "W90"},
            {"match": 98, "home": "W91", "away": "W92"},
            {"match": 99, "home": "W93", "away": "W94"},
            {"match": 100, "home": "W95", "away": "W96"},
        ],
        "semi_finals": [
            {"match": 101, "home": "W97", "away": "W98"},
            {"match": 102, "home": "W99", "away": "W100"},
        ],
        "third_place_match": {
            "match": 103, "home": "L101", "away": "L102"
        },
        "final": {
            "match": 104, "home": "W101", "away": "W102"
        }
    }
}

with open(PROCESSED / "wc2026_bracket.json", 'w') as f:
    json.dump(bracket, f, indent=2)
with open(FINAL / "wc2026_bracket.json", 'w') as f:
    json.dump(bracket, f, indent=2)
log(f"  Bracket: {len(group_matches)} group matches + 32 knockout = {len(group_matches)+32} total matches")
log(f"  Saved to data/processed/ and data/final/")

# ============================================================
# STEP 7: Merge Everything into Final Dataset
# ============================================================
log("\n" + "="*60)
log("STEP 7: Merge into Final Dataset")
log("="*60)

# Start with groups as base (has team, group, confederation, etc.)
master = groups[['team', 'confederation', 'group', 'fifa_rank_apr2026', 'wc_titles',
                 'best_finish', 'wc_appearances', 'is_host', 'is_debut', 
                 'elo_rating_2026', 'squad_market_value_eur_millions']].copy()

master.columns = ['team', 'confederation', 'group', 'fifa_rank', 'wc_titles',
                   'best_finish', 'wc_appearances', 'is_host', 'is_debut',
                   'elo_rating', 'squad_market_value_eur_m']

# Encode is_host and is_debut as binary
master['is_host'] = master['is_host'].map({'Yes': 1, 'No': 0, True: 1, False: 0}).fillna(0).astype(int)
master['is_debut'] = master['is_debut'].map({'Yes': 1, 'No': 0, True: 1, False: 0}).fillna(0).astype(int)

# Encode best_finish
finish_encoding = {
    'Winner': 7, 'Runner-up': 6, 'Third place': 5, 'Semi-finals': 5,
    'Quarter-finals': 4, 'Round of 16': 3, 'Second round': 3,
    'Group stage': 2, 'First round': 1
}
# Handle variations
def encode_finish(val):
    if pd.isna(val):
        return 0
    val = str(val)
    for k, v in finish_encoding.items():
        if k.lower() in val.lower():
            return v
    # Check for year-based formats like "Runner-up (1934/62)"
    for k, v in finish_encoding.items():
        if k.lower().split('(')[0].strip() in val.lower().split('(')[0].strip():
            return v
    return 1  # default

master['best_finish_encoded'] = master['best_finish'].apply(encode_finish)

# Merge alltime stats
alltime_merge = alltime[['team', 'win_rate', 'finals_reached', 'semis_reached']].copy()
alltime_merge.columns = ['team', 'alltime_win_rate', 'finals_reached', 'semis_reached']
master = master.merge(alltime_merge, on='team', how='left')

# Merge qualifying stats
qual_cols = ['team', 'qualifying_gf', 'qualifying_ga', 'qualifying_gd', 
             'qualifying_pts', 'qualifying_win_rate']
qual_available = [c for c in qual_cols if c in qualifying.columns]
if len(qual_available) >= 2:
    master = master.merge(qualifying[qual_available], on='team', how='left')
    log(f"  Merged qualifying: {qual_available}")

# Merge difficulty
diff_cols = ['team', 'difficulty_index', 'qualification_probability_pct']
diff_available = [c for c in diff_cols if c in difficulty.columns]
if len(diff_available) >= 2:
    master = master.merge(difficulty[diff_available], on='team', how='left')
    log(f"  Merged difficulty: {diff_available}")

# Merge coaches
if 'wc_appearances_as_coach' in coaches.columns:
    coach_merge = coaches[['team', 'wc_appearances_as_coach']].copy()
    coach_merge.columns = ['team', 'coach_wc_experience']
    master = master.merge(coach_merge, on='team', how='left')
    log("  Merged coach WC experience")

# Merge prediction features
if 'prediction_win_probability_pct' in pred_features.columns:
    pred_merge = pred_features[['team', 'prediction_win_probability_pct']].copy()
    master = master.merge(pred_merge, on='team', how='left')
    log("  Merged prediction win probability")

# Merge form features
if intl_results_ok and 'last_10_wins' in form_df.columns:
    master = master.merge(form_df, on='team', how='left')
    log(f"  Merged form features: {list(form_df.columns)}")

# Merge ranking momentum
if rankings_ok and 'rank_change_1yr' in ranking_features.columns:
    master = master.merge(ranking_features, on='team', how='left')
    log(f"  Merged ranking momentum features")

# Merge StatsBomb features
if statsbomb_ok:
    sb_merge_cols = ['team', 'wc_xG_per_game', 'wc_xGA_per_game', 'wc_shots_per_game', 'wc_pass_completion']
    sb_available_cols = [c for c in sb_merge_cols if c in sb_features.columns]
    if len(sb_available_cols) >= 2:
        master = master.merge(sb_features[sb_available_cols], on='team', how='left')
        log(f"  Merged StatsBomb features: {sb_available_cols}")

# Fill missing values with confederation median or global median
log("\n  Filling missing values...")
numeric_cols = master.select_dtypes(include=[np.number]).columns
for col in numeric_cols:
    missing = master[col].isna().sum()
    if missing > 0:
        # Try confederation median first
        for conf in master['confederation'].unique():
            mask = (master['confederation'] == conf) & master[col].isna()
            conf_median = master[master['confederation'] == conf][col].median()
            if not pd.isna(conf_median):
                master.loc[mask, col] = conf_median
        # Fill remaining with global median
        remaining = master[col].isna().sum()
        if remaining > 0:
            global_median = master[col].median()
            if not pd.isna(global_median):
                master[col] = master[col].fillna(global_median)
            else:
                master[col] = master[col].fillna(0)
        filled = missing - master[col].isna().sum()
        if filled > 0:
            log(f"    {col}: filled {filled}/{missing} missing values")

master.to_csv(FINAL / "team_features_2026.csv", index=False)
log(f"\n  FINAL DATASET: {master.shape[0]} rows × {master.shape[1]} columns")
log(f"  Columns: {list(master.columns)}")

# ============================================================
# STEP 8: Data Quality Report
# ============================================================
log("\n" + "="*60)
log("STEP 8: Data Quality Report")
log("="*60)

report = []
report.append("# 2026 FIFA World Cup AI Simulator — Data Quality Report\n")
report.append(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")

report.append("## 1. Data Sources\n")
report.append(f"- **Archive data**: 12 CSV files in data/raw/archive/")
report.append(f"- **StatsBomb WC data**: {'✅ Downloaded' if statsbomb_ok else '❌ Not available'}")
report.append(f"- **International Results**: {'✅ Downloaded' if intl_results_ok else '❌ Not available'}")
report.append(f"- **FIFA Rankings Historical**: {'✅ Downloaded' if rankings_ok else '❌ Not available'}")
report.append(f"- **EA FC 25 Players**: {'✅ Downloaded' if eafc_ok else '❌ Not available (needs Kaggle)'}")

report.append("\n## 2. Row Counts per File\n")
report.append("### Raw Archive Files")
for fname in sorted(os.listdir(RAW_ARCHIVE)):
    if fname.endswith('.csv'):
        df_temp = pd.read_csv(RAW_ARCHIVE / fname)
        report.append(f"- `{fname}`: {len(df_temp)} rows × {len(df_temp.columns)} cols")

report.append("\n### External Downloads")
for fname in sorted(os.listdir(RAW_EXT)):
    if fname.endswith('.csv'):
        try:
            df_temp = pd.read_csv(RAW_EXT / fname, nrows=0)
            n = sum(1 for _ in open(RAW_EXT / fname)) - 1
            report.append(f"- `{fname}`: ~{n} rows × {len(df_temp.columns)} cols")
        except:
            report.append(f"- `{fname}`: (could not read)")

report.append("\n### Processed Files")
for fname in sorted(os.listdir(PROCESSED)):
    if fname.endswith('.csv'):
        df_temp = pd.read_csv(PROCESSED / fname)
        report.append(f"- `{fname}`: {len(df_temp)} rows × {len(df_temp.columns)} cols")

report.append(f"\n### Final Output")
report.append(f"- `team_features_2026.csv`: {master.shape[0]} rows × {master.shape[1]} cols")
if (FINAL / "historical_matches.csv").exists():
    n = sum(1 for _ in open(FINAL / "historical_matches.csv")) - 1
    report.append(f"- `historical_matches.csv`: {n} rows")
report.append(f"- `wc2026_bracket.json`: {len(group_matches)} group + 32 knockout matches")

report.append("\n## 3. Team Name Standardization Mapping\n")
report.append("```")
for orig, std in sorted(TEAM_NAME_MAP.items()):
    report.append(f"  {orig} → {std}")
report.append("```")

report.append("\n## 4. Missing Values in Final Dataset\n")
missing_report = master.isnull().sum()
missing_report = missing_report[missing_report > 0]
if len(missing_report) > 0:
    for col, count in missing_report.items():
        pct = count / len(master) * 100
        flag = " ⚠️ >20%" if pct > 20 else ""
        report.append(f"- `{col}`: {count} missing ({pct:.1f}%){flag}")
else:
    report.append("No missing values in final dataset (all filled with confederation/global median)")

report.append("\n## 5. Duplicate Team Fix\n")
report.append(f"- Fixed duplicate entries for: {list(dup_teams)}")
report.append(f"- Kept first occurrence, removed {len(dup_teams)} duplicate rows")

report.append("\n## 6. Summary Statistics (Key Features)\n")
key_stats_cols = ['fifa_rank', 'elo_rating', 'wc_titles', 'wc_appearances', 
                  'squad_market_value_eur_m', 'alltime_win_rate']
key_stats_cols = [c for c in key_stats_cols if c in master.columns]
for col in key_stats_cols:
    s = master[col].describe()
    report.append(f"### {col}")
    report.append(f"  - Mean: {s['mean']:.2f}, Std: {s['std']:.2f}")
    report.append(f"  - Min: {s['min']:.2f}, Max: {s['max']:.2f}")
    report.append(f"  - Median: {s['50%']:.2f}")

report.append("\n## 7. Feature Filling Strategy\n")
report.append("For features with missing values (e.g., StatsBomb data for teams not in WC 2018/2022):")
report.append("1. First attempt: confederation median (e.g., UEFA median for UEFA teams)")
report.append("2. Fallback: global median across all 48 teams")
report.append("3. Final fallback: 0 (only if all values missing)")

report.append("\n## 8. Files Generated\n")
report.append("### data/processed/")
for f in sorted(os.listdir(PROCESSED)):
    report.append(f"- `{f}`")
report.append("\n### data/final/")
for f in sorted(os.listdir(FINAL)):
    report.append(f"- `{f}`")

report_text = "\n".join(report)
with open(REPORTS / "data_quality_report.md", 'w', encoding='utf-8') as f:
    f.write(report_text)

log(f"\n  Report saved to reports/data_quality_report.md")
log(f"\n{'='*60}")
log("PIPELINE COMPLETE")
log(f"{'='*60}")
print("\n\nDONE — All pipeline steps executed.")

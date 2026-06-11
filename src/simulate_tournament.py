"""2026 FIFA World Cup tournament simulator.

Uses team-level engineered features to build attack/defense strengths, simulate
match scores with a Poisson model, resolve knockout matches with extra-time / penalty
logic, and run Monte Carlo simulations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FINAL = ROOT / "data" / "final"
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"

TEAM_FEATURES = DATA_FINAL / "team_features_2026_enriched.csv"
BRACKET_JSON = DATA_FINAL / "wc2026_bracket.json"

RNG_SEED = 42
N_MONTE_CARLO = 10_000


@dataclass
class MatchResult:
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str | None
    stage: str
    match_number: int | None = None
    decided_by: str = "regular"
    home_xg: float | None = None
    away_xg: float | None = None


class WorldCupSimulator:
    def __init__(self, features_path: Path = TEAM_FEATURES, bracket_path: Path = BRACKET_JSON, seed: int = RNG_SEED):
        self.rng = np.random.default_rng(seed)
        self.features = pd.read_csv(features_path)
        with open(bracket_path, "r", encoding="utf-8") as f:
            self.bracket = json.load(f)
        self.features = self._prepare_features(self.features)
        self.team = self.features.set_index("team").to_dict(orient="index")
        self.groups = self._build_groups()

    @staticmethod
    def _minmax(s: pd.Series, invert: bool = False) -> pd.Series:
        s = pd.to_numeric(s, errors="coerce")
        if s.max() == s.min():
            out = pd.Series(0.5, index=s.index)
        else:
            out = (s - s.min()) / (s.max() - s.min())
        return 1 - out if invert else out

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Normalize core indicators. Higher = better.
        df["elo_n"] = self._minmax(df["elo_rating"])
        df["fifa_rank_n"] = self._minmax(df["fifa_rank"], invert=True)
        df["market_n"] = self._minmax(np.log1p(df["squad_market_value_eur_m"]))
        df["history_n"] = self._minmax(
            df["wc_titles"] * 3 + df["wc_appearances"] * 0.25 + df["alltime_win_rate"] * 10
        )
        df["form_n"] = self._minmax(
            df["last_20_win_rate"] * 10
            + (df["last_10_gf"] - df["last_10_ga"]) * 0.12
            + df["competitive_win_rate"] * 5
        )
        df["eafc_n"] = self._minmax(
            df["eafc_top11_avg_ovr"] * 0.35
            + df["eafc_top23_avg_ovr"] * 0.25
            + df["eafc_attack_rating"] * 0.15
            + df["eafc_midfield_rating"] * 0.10
            + df["eafc_defense_rating"] * 0.10
            + df["eafc_goalkeeper_rating"] * 0.05
        )
        df["statsbomb_attack_n"] = self._minmax(df["wc_xG_per_game"] * 0.7 + df["wc_shots_per_game"] * 0.3)
        df["statsbomb_defense_n"] = self._minmax(df["wc_xGA_per_game"], invert=True)
        df["coach_n"] = self._minmax(df["coach_wc_experience"])

        # Overall strength: deliberately transparent and stable.
        # Calibrated v2: current squad quality and recent WC event profile matter more.
        # This avoids over-trusting old historical reputation while still preserving ELO/FIFA signal.
        df["team_power"] = (
            0.20 * df["elo_n"]
            + 0.11 * df["fifa_rank_n"]
            + 0.27 * df["eafc_n"]
            + 0.08 * df["market_n"]
            + 0.16 * df["form_n"]
            + 0.03 * df["history_n"]
            + 0.08 * df["statsbomb_attack_n"]
            + 0.06 * df["statsbomb_defense_n"]
            + 0.01 * df["coach_n"]
        )

        # Attack/defense strengths separately for expected goals.
        df["attack_strength"] = (
            0.34 * df["eafc_attack_rating"] / 100
            + 0.22 * df["eafc_shooting_avg_top11"] / 100
            + 0.13 * df["eafc_passing_avg_top11"] / 100
            + 0.10 * df["elo_n"]
            + 0.09 * df["form_n"]
            + 0.08 * df["statsbomb_attack_n"]
            + 0.04 * df["market_n"]
        )
        df["defense_strength"] = (
            0.30 * df["eafc_defense_rating"] / 100
            + 0.23 * df["eafc_goalkeeper_rating"] / 100
            + 0.17 * df["eafc_defending_avg_top11"] / 100
            + 0.10 * df["elo_n"]
            + 0.09 * df["statsbomb_defense_n"]
            + 0.06 * df["form_n"]
            + 0.05 * df["market_n"]
        )

        # Calibrate ranges so average attack/defense around 1.
        for col in ["team_power", "attack_strength", "defense_strength"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(df[col].median())

        return df

    def _build_groups(self) -> Dict[str, List[str]]:
        return {
            g: list(grp["team"])
            for g, grp in self.features.sort_values(["group", "team"]).groupby("group")
        }

    def expected_goals(self, home: str, away: str, knockout: bool = False) -> Tuple[float, float]:
        h = self.team[home]
        a = self.team[away]
        base = 1.32  # World Cup-ish team goal average; match total around 2.6.

        home_host_bonus = 0.10 if h.get("is_host", 0) == 1 else 0.0
        away_host_bonus = 0.10 if a.get("is_host", 0) == 1 else 0.0

        power_diff = h["team_power"] - a["team_power"]
        elo_diff = (h["elo_rating"] - a["elo_rating"]) / 400.0

        h_lambda = base * np.exp(
            0.85 * (h["attack_strength"] - a["defense_strength"])
            + 0.28 * power_diff
            + 0.13 * elo_diff
            + home_host_bonus
        )
        a_lambda = base * np.exp(
            0.85 * (a["attack_strength"] - h["defense_strength"])
            - 0.28 * power_diff
            - 0.13 * elo_diff
            + away_host_bonus
        )

        # Avoid unrealistic tails.
        h_lambda = float(np.clip(h_lambda, 0.25, 3.40))
        a_lambda = float(np.clip(a_lambda, 0.25, 3.40))
        return h_lambda, a_lambda

    def simulate_match(self, home: str, away: str, stage: str, match_number: int | None = None, knockout: bool = False) -> MatchResult:
        hxg, axg = self.expected_goals(home, away, knockout=knockout)
        hg = int(self.rng.poisson(hxg))
        ag = int(self.rng.poisson(axg))
        decided_by = "regular"
        winner = None

        if hg > ag:
            winner = home
        elif ag > hg:
            winner = away
        elif knockout:
            # Extra time: low-scoring, strength-adjusted. If still tied, penalties.
            h_et_xg = hxg * 0.28
            a_et_xg = axg * 0.28
            h_et = int(self.rng.poisson(h_et_xg))
            a_et = int(self.rng.poisson(a_et_xg))
            hg += h_et
            ag += a_et
            if h_et > a_et:
                winner = home
                decided_by = "extra_time"
            elif a_et > h_et:
                winner = away
                decided_by = "extra_time"
            else:
                hp = self.penalty_win_probability(home, away)
                winner = home if self.rng.random() < hp else away
                decided_by = "penalties"
        else:
            winner = None

        return MatchResult(home, away, hg, ag, winner, stage, match_number, decided_by, hxg, axg)

    def penalty_win_probability(self, home: str, away: str) -> float:
        h = self.team[home]
        a = self.team[away]
        # Penalties are noisy; only small edge from keeper + composure proxy.
        h_score = 0.55 * h["eafc_goalkeeper_rating"] + 0.45 * h["eafc_star_player_rating"]
        a_score = 0.55 * a["eafc_goalkeeper_rating"] + 0.45 * a["eafc_star_player_rating"]
        p = 0.5 + (h_score - a_score) / 400.0
        return float(np.clip(p, 0.40, 0.60))

    def simulate_group_stage(self) -> Tuple[List[MatchResult], pd.DataFrame, Dict[str, List[str]]]:
        rows = []
        group_results: Dict[str, List[str]] = {}
        match_results: List[MatchResult] = []

        standings = {
            team: {"team": team, "group": group, "played": 0, "wins": 0, "draws": 0, "losses": 0,
                   "gf": 0, "ga": 0, "gd": 0, "points": 0}
            for group, teams in self.groups.items() for team in teams
        }

        for m in self.bracket["group_stage"]["matches"]:
            home = m["home_team"]
            away = m["away_team"]
            group = m["group"]
            res = self.simulate_match(home, away, "Group Stage", m["match_number"], knockout=False)
            match_results.append(res)

            h, a = standings[home], standings[away]
            h["played"] += 1; a["played"] += 1
            h["gf"] += res.home_goals; h["ga"] += res.away_goals
            a["gf"] += res.away_goals; a["ga"] += res.home_goals
            h["gd"] = h["gf"] - h["ga"]; a["gd"] = a["gf"] - a["ga"]
            if res.home_goals > res.away_goals:
                h["wins"] += 1; a["losses"] += 1; h["points"] += 3
            elif res.away_goals > res.home_goals:
                a["wins"] += 1; h["losses"] += 1; a["points"] += 3
            else:
                h["draws"] += 1; a["draws"] += 1; h["points"] += 1; a["points"] += 1

        table = pd.DataFrame(standings.values())
        # Fair-play/lots not simulated. Tie fallback: team_power.
        table["team_power"] = table["team"].map(lambda t: self.team[t]["team_power"])
        ranked = []
        for group, gdf in table.groupby("group"):
            gdf = gdf.sort_values(["points", "gd", "gf", "team_power"], ascending=[False, False, False, False]).copy()
            gdf["rank"] = range(1, len(gdf) + 1)
            ranked.append(gdf)
            group_results[group] = list(gdf["team"])
        table = pd.concat(ranked, ignore_index=True)
        return match_results, table, group_results

    def qualifiers_from_groups(self, standings: pd.DataFrame) -> Dict[str, str]:
        slots = {}
        for _, row in standings.iterrows():
            group = row["group"]
            rank = int(row["rank"])
            if rank in (1, 2):
                slots[f"{rank}{group}"] = row["team"]

        thirds = standings[standings["rank"] == 3].sort_values(
            ["points", "gd", "gf", "team_power"], ascending=[False, False, False, False]
        ).head(8)
        for _, row in thirds.iterrows():
            slots[f"3{row['group']}"] = row["team"]
        return slots

    @staticmethod
    def _parse_third_slot(slot: str) -> List[str]:
        # slot like "3C/E/F/H/I"
        return ["3" + x for x in slot[1:].split("/")]

    def resolve_round_of_32_slots(self, qualifier_slots: Dict[str, str]) -> List[Tuple[int, str, str, str, str]]:
        # FIFA public schedule gives candidate pools for third-place opponents, not full allocation table.
        # Greedy authentic fallback: assign strongest available third-place team to first compatible slot,
        # while avoiding reuse. This is marked in output as fifa_public_slots_greedy_third_place.
        used_thirds = set()
        matches = []
        available_thirds = {k: v for k, v in qualifier_slots.items() if k.startswith("3")}

        for m in self.bracket["knockout_stage"]["round_of_32"]:
            home_slot = m["home"]
            away_slot = m["away"]
            home = qualifier_slots[home_slot]
            if away_slot.startswith("3") and "/" in away_slot:
                candidates = self._parse_third_slot(away_slot)
                valid = [s for s in candidates if s in available_thirds and s not in used_thirds]
                if not valid:
                    # Fallback if FIFA public candidate pools cannot place all 8 (e.g. 3A qualifies).
                    remaining = [s for s in available_thirds if s not in used_thirds]
                    if not remaining:
                        raise RuntimeError("No third-place teams left to assign")
                    valid = remaining
                # Prefer stronger team for deterministic-ish bracket realism.
                chosen_slot = max(valid, key=lambda s: self.team[available_thirds[s]]["team_power"])
                used_thirds.add(chosen_slot)
                away = available_thirds[chosen_slot]
                away_resolved_slot = chosen_slot
            else:
                away = qualifier_slots[away_slot]
                away_resolved_slot = away_slot
            matches.append((m["match"], home, away, home_slot, away_resolved_slot))
        return matches

    def simulate_knockout(self, qualifier_slots: Dict[str, str]) -> List[MatchResult]:
        results = []
        winners = {}
        r32_matches = self.resolve_round_of_32_slots(qualifier_slots)
        for match_id, home, away, hs, aways in r32_matches:
            res = self.simulate_match(home, away, "Round of 32", match_id, knockout=True)
            res.decided_by = res.decided_by + f"; slots {hs} vs {aways}"
            results.append(res)
            winners[f"W{match_id}"] = res.winner

        for stage_key, stage_name in [
            ("round_of_16", "Round of 16"),
            ("quarter_finals", "Quarter-final"),
            ("semi_finals", "Semi-final"),
            ("third_place_match", "Third-place Match"),
            ("final", "Final"),
        ]:
            stage_matches = self.bracket["knockout_stage"][stage_key]
            if isinstance(stage_matches, dict):
                stage_matches = [stage_matches]
            for m in stage_matches:
                home = winners[m["home"]]
                away = winners[m["away"]]
                res = self.simulate_match(home, away, stage_name, m["match"], knockout=True)
                results.append(res)
                winners[f"W{m['match']}"] = res.winner
                if stage_name == "Semi-final":
                    # Losers for third-place match.
                    loser = away if res.winner == home else home
                    winners[f"L{m['match']}"] = loser
        return results

    def simulate_tournament(self) -> Dict[str, Any]:
        group_matches, standings, _group_rankings = self.simulate_group_stage()
        qualifier_slots = self.qualifiers_from_groups(standings)
        knockout_matches = self.simulate_knockout(qualifier_slots)
        champion = [m for m in knockout_matches if m.stage == "Final"][0].winner
        runner_up = [m for m in knockout_matches if m.stage == "Final"][0].away
        final_match = [m for m in knockout_matches if m.stage == "Final"][0]
        if final_match.winner == final_match.away:
            runner_up = final_match.home
        third_place_match = [m for m in knockout_matches if m.stage == "Third-place Match"][0]
        third_place = third_place_match.winner
        return {
            "champion": champion,
            "runner_up": runner_up,
            "third_place": third_place,
            "group_matches": group_matches,
            "standings": standings,
            "qualifier_slots": qualifier_slots,
            "knockout_matches": knockout_matches,
        }


def match_results_to_df(matches: List[MatchResult]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "match_number": m.match_number,
            "stage": m.stage,
            "home": m.home,
            "away": m.away,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "winner": m.winner,
            "decided_by": m.decided_by,
            "home_xg": m.home_xg,
            "away_xg": m.away_xg,
        }
        for m in matches
    ])


def main():
    OUTPUTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    sim = WorldCupSimulator(seed=RNG_SEED)

    # Save team powers for transparency.
    power_cols = [
        "team", "group", "fifa_rank", "elo_rating", "team_power", "attack_strength", "defense_strength",
        "eafc_top11_avg_ovr", "eafc_star_player", "eafc_star_player_rating",
    ]
    sim.features.sort_values("team_power", ascending=False)[power_cols].to_csv(OUTPUTS / "team_power_rankings.csv", index=False)

    one = sim.simulate_tournament()
    all_matches = one["group_matches"] + one["knockout_matches"]
    match_results_to_df(all_matches).to_csv(OUTPUTS / "single_tournament_matches.csv", index=False)
    one["standings"].to_csv(OUTPUTS / "single_tournament_group_standings.csv", index=False)

    # Monte Carlo.
    stage_counts = {team: {"champion": 0, "runner_up": 0, "third_place": 0, "knockout": 0, "quarter_final": 0, "semi_final": 0, "final": 0} for team in sim.features["team"]}
    final_pair_counts = {}

    for i in range(N_MONTE_CARLO):
        # different RNG state each loop through same sim instance is fine.
        res = sim.simulate_tournament()
        champ, runner, third = res["champion"], res["runner_up"], res["third_place"]
        stage_counts[champ]["champion"] += 1
        stage_counts[runner]["runner_up"] += 1
        stage_counts[third]["third_place"] += 1

        # Qualified to R32.
        for team in res["qualifier_slots"].values():
            stage_counts[team]["knockout"] += 1

        # Stage participation from knockout winners/matches.
        km = match_results_to_df(res["knockout_matches"])
        for stage, col in [("Quarter-final", "quarter_final"), ("Semi-final", "semi_final"), ("Final", "final")]:
            participants = set(km[km["stage"] == stage]["home"]).union(set(km[km["stage"] == stage]["away"]))
            for team in participants:
                stage_counts[team][col] += 1

        pair = tuple(sorted([champ, runner]))
        final_pair_counts[pair] = final_pair_counts.get(pair, 0) + 1

        if (i + 1) % 1000 == 0:
            print(f"Monte Carlo progress: {i+1}/{N_MONTE_CARLO}")

    probs = pd.DataFrame([
        {"team": team, **{k + "_prob": v / N_MONTE_CARLO for k, v in counts.items()}}
        for team, counts in stage_counts.items()
    ])
    probs = probs.merge(sim.features[["team", "group", "fifa_rank", "elo_rating", "team_power"]], on="team", how="left")
    probs = probs.sort_values("champion_prob", ascending=False)
    probs.to_csv(OUTPUTS / "monte_carlo_team_probabilities.csv", index=False)

    final_pairs = pd.DataFrame([
        {"team_a": a, "team_b": b, "count": c, "probability": c / N_MONTE_CARLO}
        for (a, b), c in final_pair_counts.items()
    ]).sort_values("probability", ascending=False)
    final_pairs.to_csv(OUTPUTS / "monte_carlo_final_pair_probabilities.csv", index=False)

    report = []
    report.append("# 2026 FIFA World Cup Simulation Report\n")
    report.append(f"Monte Carlo runs: {N_MONTE_CARLO:,}\n")
    report.append("\n## Model Summary\n")
    report.append("- Score model: Poisson expected-goals simulation\n")
    report.append("- Strength inputs: ELO, FIFA rank, EA FC 25 squad quality, squad market value, recent international form, WC history, StatsBomb WC event features, coach WC experience\n")
    report.append("- Knockout draws: extra-time then penalties\n")
    report.append("- 3rd-place R32 allocation: FIFA public candidate slots + greedy compatible fallback; exact FIFA 495-combination table not public in accessible sources\n")
    report.append("\n## Single Seeded Simulation Result\n")
    report.append(f"- Champion: **{one['champion']}**\n")
    report.append(f"- Runner-up: **{one['runner_up']}**\n")
    report.append(f"- Third place: **{one['third_place']}**\n")
    report.append("\n## Top Champion Probabilities\n")
    for _, r in probs.head(12).iterrows():
        report.append(f"- {r['team']}: {r['champion_prob']:.2%} (final {r['final_prob']:.2%}, SF {r['semi_final_prob']:.2%})\n")
    report.append("\n## Most Likely Final Pairings\n")
    for _, r in final_pairs.head(10).iterrows():
        report.append(f"- {r['team_a']} vs {r['team_b']}: {r['probability']:.2%}\n")

    (REPORTS / "simulation_report.md").write_text("".join(report), encoding="utf-8")

    print("Done.")
    print("Single simulation champion:", one["champion"])
    print("Top champion probabilities:")
    print(probs[["team", "champion_prob", "final_prob", "semi_final_prob", "knockout_prob"]].head(12).to_string(index=False))
    print("Outputs written to", OUTPUTS)


if __name__ == "__main__":
    main()

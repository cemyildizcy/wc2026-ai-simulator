"""Fetch current World Football Elo ratings and merge them into team features.

Source: https://www.eloratings.net/

Outputs:
- data/raw/external/world_football_elo_current.tsv
- data/processed/world_football_elo_current.csv
- data/final/team_features_2026.csv (elo_rating refreshed)
- data/final/team_features_2026_enriched.csv if it already exists
- reports/elo_update_report.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_EXT = ROOT / "data" / "raw" / "external"
PROCESSED = ROOT / "data" / "processed"
FINAL = ROOT / "data" / "final"
REPORTS = ROOT / "reports"

WORLD_URL = "https://www.eloratings.net/World.tsv"
TEAM_NAMES_URL = "https://www.eloratings.net/en.teams.tsv"

RAW_WORLD_OUT = RAW_EXT / "world_football_elo_current.tsv"
PROCESSED_OUT = PROCESSED / "world_football_elo_current.csv"
FINAL_BASE = FINAL / "team_features_2026.csv"
FINAL_ENRICHED = FINAL / "team_features_2026_enriched.csv"
REPORT_OUT = REPORTS / "elo_update_report.md"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; wc2026-ai-simulator/1.0)"}

# Project team name -> eloratings.net English team name.
TEAM_NAME_MAP = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Czechia": "Czechia",
    "DR Congo": "DR Congo",
    "Ivory Coast": "Ivory Coast",
    "South Korea": "South Korea",
    "United States": "United States",
    "Curaçao": "Curaçao",
}


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def load_team_code_names() -> pd.DataFrame:
    text = fetch_text(TEAM_NAMES_URL)
    rows = []
    for line in text.splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            rows.append({"elo_code": parts[0], "elo_team_name": parts[1]})
    return pd.DataFrame(rows)


def load_world_rankings() -> pd.DataFrame:
    text = fetch_text(WORLD_URL)
    RAW_WORLD_OUT.write_text(text, encoding="utf-8")

    rows = []
    for line in text.splitlines():
        parts = line.strip().split("\t")
        if len(parts) < 4:
            continue
        rows.append(
            {
                "elo_rank": pd.to_numeric(parts[0], errors="coerce"),
                "elo_previous_rank": pd.to_numeric(parts[1], errors="coerce"),
                "elo_code": parts[2],
                "elo_rating_current": pd.to_numeric(parts[3], errors="coerce"),
                # Keep the raw row because eloratings.net contains many extra trend columns.
                "elo_raw_row": line,
            }
        )
    return pd.DataFrame(rows)


def build_current_elo_dataset() -> pd.DataFrame:
    names = load_team_code_names()
    world = load_world_rankings()
    elo = world.merge(names, on="elo_code", how="left")
    elo["elo_rank_change"] = elo["elo_previous_rank"] - elo["elo_rank"]
    elo["elo_source"] = WORLD_URL
    elo["elo_fetched_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elo.to_csv(PROCESSED_OUT, index=False)
    return elo


def merge_into_features(path: Path, elo: pd.DataFrame) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []

    df = pd.read_csv(path)
    original_cols = list(df.columns)
    # Make the script idempotent: remove previously merged current-ELO columns,
    # while keeping `elo_rating_project_estimate` if it already exists.
    current_elo_cols = [
        "elo_team_name",
        "elo_rank",
        "elo_previous_rank",
        "elo_rank_change",
        "elo_rating_current",
        "elo_fetched_at_utc",
        "elo_source",
    ]
    df = df.drop(columns=[c for c in current_elo_cols if c in df.columns], errors="ignore")

    df["elo_lookup_name"] = df["team"].map(TEAM_NAME_MAP).fillna(df["team"])
    df["elo_lookup_key"] = df["elo_lookup_name"].map(normalize_name)

    elo_small = elo[[
        "elo_team_name",
        "elo_rank",
        "elo_previous_rank",
        "elo_rank_change",
        "elo_rating_current",
        "elo_fetched_at_utc",
        "elo_source",
    ]].copy()
    elo_small["elo_lookup_key"] = elo_small["elo_team_name"].map(normalize_name)

    merged = df.merge(elo_small, on="elo_lookup_key", how="left", suffixes=("", "_new"))
    unmatched = merged.loc[merged["elo_rating_current"].isna(), "team"].tolist()

    # Preserve previous project estimate for comparison, then replace main elo_rating.
    if "elo_rating" in merged.columns and "elo_rating_project_estimate" not in merged.columns:
        merged["elo_rating_project_estimate"] = merged["elo_rating"]
    merged["elo_rating"] = merged["elo_rating_current"].fillna(merged.get("elo_rating"))

    # Drop helper columns but keep useful source/rank columns.
    merged = merged.drop(columns=["elo_lookup_name", "elo_lookup_key"], errors="ignore")

    # Keep original column order as much as possible; append new ELO metadata columns.
    append_cols = [
        "elo_team_name",
        "elo_rank",
        "elo_previous_rank",
        "elo_rank_change",
        "elo_rating_current",
        "elo_rating_project_estimate",
        "elo_fetched_at_utc",
        "elo_source",
    ]
    ordered = [c for c in original_cols if c in merged.columns]
    ordered += [c for c in append_cols if c in merged.columns and c not in ordered]
    ordered += [c for c in merged.columns if c not in ordered]
    merged = merged[ordered]

    merged.to_csv(path, index=False)
    return len(merged) - len(unmatched), unmatched


def main() -> None:
    RAW_EXT.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    elo = build_current_elo_dataset()
    base_matched, base_unmatched = merge_into_features(FINAL_BASE, elo)
    enriched_matched, enriched_unmatched = merge_into_features(FINAL_ENRICHED, elo)

    report = [
        "# World Football Elo Update Report",
        "",
        f"Source: `{WORLD_URL}`",
        f"Fetched at UTC: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`",
        "",
        "## Outputs",
        f"- Raw TSV: `{RAW_WORLD_OUT}`",
        f"- Processed CSV: `{PROCESSED_OUT}`",
        f"- Updated base features: `{FINAL_BASE}`",
    ]
    if FINAL_ENRICHED.exists():
        report.append(f"- Updated enriched features: `{FINAL_ENRICHED}`")
    report += [
        "",
        "## Merge Summary",
        f"- Base dataset matched teams: {base_matched}",
        f"- Base unmatched teams: {', '.join(base_unmatched) if base_unmatched else 'None'}",
        f"- Enriched dataset matched teams: {enriched_matched}",
        f"- Enriched unmatched teams: {', '.join(enriched_unmatched) if enriched_unmatched else 'None'}",
        "",
        "## Columns Added / Updated",
        "- `elo_rating`: replaced with current World Football Elo value when matched",
        "- `elo_rating_project_estimate`: previous project estimate kept for comparison",
        "- `elo_rank`",
        "- `elo_previous_rank`",
        "- `elo_rank_change`",
        "- `elo_rating_current`",
        "- `elo_team_name`",
        "- `elo_fetched_at_utc`",
        "- `elo_source`",
        "",
        "## Top 15 Current Elo Teams",
    ]
    top = elo.sort_values("elo_rank").head(15)
    for _, row in top.iterrows():
        report.append(f"- {int(row['elo_rank'])}. {row['elo_team_name']}: {int(row['elo_rating_current'])}")

    REPORT_OUT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print("World Football Elo data saved:", PROCESSED_OUT)
    print("Base features matched:", base_matched, "unmatched:", base_unmatched)
    print("Enriched features matched:", enriched_matched, "unmatched:", enriched_unmatched)
    print("Report saved:", REPORT_OUT)


if __name__ == "__main__":
    main()

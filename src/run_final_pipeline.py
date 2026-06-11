"""Run final modeling pipeline for WC 2026 AI Simulator.

Steps:
1. Fetch and merge current World Football Elo ratings.
2. Rebuild EA FC 25 team features.
3. Run calibrated Monte Carlo tournament simulator.
4. Generate deterministic most-likely path.
5. Generate scoreline distributions.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "update_elo_ratings.py",
    "add_eafc25_features.py",
    "simulate_tournament.py",
    "generate_most_likely_path.py",
    "generate_match_score_distributions.py",
    "create_eda_figures.py",
]


def run(script: str) -> None:
    print(f"\n=== Running {script} ===")
    result = subprocess.run([sys.executable, str(ROOT / "src" / script)], cwd=ROOT, text=True)
    if result.returncode != 0:
        raise SystemExit(f"Pipeline failed at {script} with exit code {result.returncode}")


def main() -> None:
    for script in SCRIPTS:
        run(script)
    print("\nFinal pipeline completed successfully.")
    print(f"Outputs: {ROOT / 'outputs'}")
    print(f"Reports: {ROOT / 'reports'}")


if __name__ == "__main__":
    main()

"""Create final EDA/model figures for WC 2026 AI Simulator."""
from pathlib import Path
import textwrap
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.style.use("dark_background")


def save_bar(df, x, y, title, xlabel, path, color="#4cc9f0", top_n=15):
    d = df.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(d[y], d[x], color=color)
    ax.set_title(title, fontsize=16, weight="bold")
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(d[x]):
        label = f"{v:.1%}" if "prob" in x else f"{v:.3f}"
        ax.text(v, i, "  " + label, va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def champion_probs():
    p = pd.read_csv(OUT / "monte_carlo_team_probabilities.csv")
    save_bar(
        p,
        "champion_prob",
        "team",
        "2026 World Cup Champion Probability — Monte Carlo (10,000 runs)",
        "Champion probability",
        FIG / "champion_probabilities_top15.png",
        "#ffd166",
        15,
    )


def team_power():
    p = pd.read_csv(OUT / "team_power_rankings.csv")
    save_bar(
        p,
        "team_power",
        "team",
        "Calibrated Team Power Ranking",
        "Team power score",
        FIG / "team_power_top15.png",
        "#06d6a0",
        15,
    )


def stage_probs():
    p = pd.read_csv(OUT / "monte_carlo_team_probabilities.csv").head(10)
    cols = ["quarter_final_prob", "semi_final_prob", "final_prob", "champion_prob"]
    labels = ["QF", "SF", "Final", "Champion"]
    fig, ax = plt.subplots(figsize=(11, 7))
    bottom = [0] * len(p)
    # Use grouped line plot rather than stacked, easier to read probabilities.
    for col, label in zip(cols, labels):
        ax.plot(p["team"], p[col], marker="o", linewidth=2, label=label)
    ax.set_title("Stage Reach Probabilities — Top 10 Champion Candidates", fontsize=16, weight="bold")
    ax.set_ylabel("Probability")
    ax.tick_params(axis="x", rotation=40)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "stage_reach_probabilities_top10.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def final_score_distribution():
    d = pd.read_csv(OUT / "most_likely_match_score_distributions.csv")
    final = d[d["stage"] == "Final"].iloc[0]
    parts = []
    for token in final["top_5_scorelines"].split("; "):
        score, prob = token.split(" ")
        parts.append((score, float(prob.strip("()%")) / 100))
    scores = [x[0] for x in parts]
    probs = [x[1] for x in parts]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(scores, probs, color="#ef476f")
    ax.set_title(f"Final Scoreline Distribution: {final['home']} vs {final['away']}", fontsize=14, weight="bold")
    ax.set_ylabel("Score probability")
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(probs):
        ax.text(i, v, f"{v:.1%}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIG / "final_scoreline_distribution.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def bracket_text_card():
    m = pd.read_csv(OUT / "most_likely_tournament_matches.csv")
    ko = m[m["stage"].isin(["Quarter-final", "Semi-final", "Final"])]
    lines = []
    for _, r in ko.iterrows():
        lines.append(f"M{int(r.match_number)} {r.stage}: {r.home} {int(r.home_goals)}-{int(r.away_goals)} {r.away} → {r.winner}")
    text = "\n".join(lines)
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis("off")
    ax.set_title("Most-Likely Knockout Path", fontsize=18, weight="bold", pad=20)
    ax.text(0.02, 0.95, text, va="top", ha="left", family="monospace", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "most_likely_knockout_path.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    champion_probs()
    team_power()
    stage_probs()
    final_score_distribution()
    bracket_text_card()
    print("Figures created:")
    for p in sorted(FIG.glob("*.png")):
        print(p)


if __name__ == "__main__":
    main()

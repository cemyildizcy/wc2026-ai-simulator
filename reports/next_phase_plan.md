# Next Phase Plan — Dashboard + GitHub + LinkedIn Package

## Phase 1 — Dashboard

Build a Streamlit dashboard around final outputs.

Pages:

1. Overview
   - champion probabilities
   - most-likely champion
   - central final
   - key caveats

2. Team Explorer
   - select team
   - show team power rank
   - EA FC top players/features
   - qualification/final/champion probabilities

3. Match Explorer
   - select any most-likely match
   - show xG
   - W/D/L probabilities
   - top 5 scorelines

4. Group Stage
   - show 12 group tables
   - group qualification probabilities if added later

5. Knockout Bracket
   - central most-likely path
   - final/semifinal pair probabilities

6. Methodology
   - data sources
   - feature families
   - Poisson model
   - Monte Carlo simulation
   - limitations

## Phase 2 — GitHub Polish

- Clean repo structure
- Add requirements.txt
- Add screenshots from `outputs/figures/`
- Add README with:
  - project goal
  - data sources
  - model design
  - results
  - how to run
  - limitations
- Add `.gitignore`
- Avoid committing Kaggle token or credentials

## Phase 3 — LinkedIn Post

Hook:

> 2026 Dünya Kupası tarihte ilk kez 48 takımla oynanacak. Ben de turnuvayı veri bilimiyle 10.000 kez simüle eden bir AI World Cup Simulator geliştirdim.

Core story:

- data fusion: EA FC 25 + StatsBomb + ELO/FIFA + historical results
- Poisson xG score model
- 10,000 Monte Carlo simulations
- probability-based predictions rather than exact-score claims
- central bracket: Brazil vs Argentina final
- uncertainty: Argentina highest Monte Carlo champion probability, Brazil central bracket champion

Visuals to include:

1. champion probabilities chart
2. most-likely knockout path
3. final scoreline distribution
4. team power ranking

## Phase 4 — Optional Model Improvements

- Add real 2025/2026 player season stats if available
- Add updated FIFA ranking historical trend
- Add betting odds only as benchmark, not as betting product
- Add calibration/backtest with 2018/2022 tournament outcomes
- Add group qualification probabilities from Monte Carlo
- Add interactive user-controlled assumptions

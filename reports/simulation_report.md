# 2026 FIFA World Cup Simulation Report
Monte Carlo runs: 10,000

## Model Summary
- Score model: Poisson expected-goals simulation
- Strength inputs: ELO, FIFA rank, EA FC 25 squad quality, squad market value, recent international form, WC history, StatsBomb WC event features, coach WC experience
- Group-stage draws: allowed and scored as 1 point per team
- Fixed played results: Mexico 2-0 South Africa; South Korea 2-1 Czechia
- Knockout draws: extra-time then penalties
- Third-place ranking: points, goal difference, goals scored, FIFA ranking fallback because fair-play cards are not simulated
- R32 third-place slots: Wikipedia/FIFA public candidate pools + greedy compatible fallback; exact full allocation table not encoded

## Single Seeded Simulation Result
- Champion: **Argentina**
- Runner-up: **Colombia**
- Third place: **Spain**

## Top Champion Probabilities
- Argentina: 11.48% (final 18.66%, SF 29.52%)
- Spain: 11.29% (final 18.51%, SF 29.21%)
- France: 8.87% (final 15.48%, SF 25.14%)
- England: 7.78% (final 13.49%, SF 23.21%)
- Brazil: 7.57% (final 13.67%, SF 24.02%)
- Germany: 7.51% (final 13.39%, SF 22.38%)
- Portugal: 5.99% (final 11.74%, SF 20.95%)
- Belgium: 3.88% (final 7.89%, SF 15.65%)
- Netherlands: 3.04% (final 5.94%, SF 12.91%)
- Turkey: 2.74% (final 6.01%, SF 12.48%)
- Croatia: 2.34% (final 5.15%, SF 11.35%)
- Switzerland: 2.11% (final 5.17%, SF 11.46%)

## Most Likely Final Pairings
- France vs Spain: 2.98%
- Argentina vs France: 2.60%
- Argentina vs Brazil: 2.59%
- Germany vs Spain: 2.38%
- Argentina vs Germany: 2.20%
- Brazil vs Spain: 2.12%
- Argentina vs England: 1.82%
- England vs Spain: 1.64%
- France vs Portugal: 1.58%
- Brazil vs Portugal: 1.45%

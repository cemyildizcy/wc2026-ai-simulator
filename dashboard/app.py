"""
2026 FIFA Dünya Kupası AI Simülatörü — İnteraktif Dashboard
Streamlit çok-sayfalı uygulama, koyu tema ve Plotly grafikleri.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import hashlib

# ─── Sayfa ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DK 2026 AI Simülatör",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Dosya yolları ────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
DATA = os.path.join(BASE, "data", "final")
FIG = os.path.join(OUT, "figures")


# ─── Veri yükleme (önbellek) ─────────────────────────────────────────────────
def data_version():
    """Create cache-busting version from file content, not mtimes.

    Streamlit Cloud can preserve cache across deploys while Git checkout mtimes may
    not reflect data changes reliably. Content hashes force fresh group/output data.
    """
    tracked_files = [
        os.path.join(OUT, "monte_carlo_team_probabilities.csv"),
        os.path.join(OUT, "most_likely_tournament_matches.csv"),
        os.path.join(OUT, "most_likely_group_standings.csv"),
        os.path.join(OUT, "most_likely_match_score_distributions.csv"),
        os.path.join(OUT, "team_power_rankings.csv"),
        os.path.join(OUT, "monte_carlo_final_pair_probabilities.csv"),
        os.path.join(DATA, "team_features_2026_enriched.csv"),
    ]
    digest = hashlib.sha256()
    for path in tracked_files:
        if os.path.exists(path):
            digest.update(os.path.basename(path).encode("utf-8"))
            with open(path, "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


@st.cache_data
def load_data(_version):
    mc = pd.read_csv(os.path.join(OUT, "monte_carlo_team_probabilities.csv"))
    matches = pd.read_csv(os.path.join(OUT, "most_likely_tournament_matches.csv"))
    groups = pd.read_csv(os.path.join(OUT, "most_likely_group_standings.csv"))
    scores = pd.read_csv(os.path.join(OUT, "most_likely_match_score_distributions.csv"))
    power = pd.read_csv(os.path.join(OUT, "team_power_rankings.csv"))
    finals = pd.read_csv(os.path.join(OUT, "monte_carlo_final_pair_probabilities.csv"))
    features = pd.read_csv(os.path.join(DATA, "team_features_2026_enriched.csv"))
    with open(os.path.join(DATA, "wc2026_bracket.json"), "r") as f:
        bracket = json.load(f)
    return mc, matches, groups, scores, power, finals, features, bracket


mc, matches, groups, scores, power, finals, features, bracket = load_data(data_version())

# ─── Aşama çevirisi ──────────────────────────────────────────────────────────
STAGE_TR = {
    "Group Stage": "Grup Aşaması",
    "Round of 32": "Son 32",
    "Round of 16": "Son 16",
    "Quarter-final": "Çeyrek Final",
    "Semi-final": "Yarı Final",
    "Third-place Match": "Üçüncülük Maçı",
    "Final": "Final",
}

BEST_FINISH_TR = {
    "Winner": "Şampiyon",
    "Runner-up": "Finalist",
    "Runner-up (1934/62)": "Finalist (1934/62)",
    "Third place": "Üçüncülük",
    "Semi-finals": "Yarı Final",
    "Quarter-finals": "Çeyrek Final",
    "Round of 16": "Son 16",
    "Group stage": "Grup Aşaması",
    "First appearance": "İlk Katılım",
}


def tr_stage(s):
    return STAGE_TR.get(s, s)


def tr_best_finish(s):
    return BEST_FINISH_TR.get(s, s)


def safe_depth_score(features_df, value):
    depth = pd.to_numeric(features_df.get("eafc_squad_depth"), errors="coerce")
    value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(value) or depth.isna().all():
        return 50
    min_v, max_v = depth.min(), depth.max()
    if max_v == min_v:
        return 50
    return float((value - min_v) / (max_v - min_v) * 100)

# ─── Sidebar navigasyon ──────────────────────────────────────────────────────
st.sidebar.title("⚽ DK 2026 AI Simülatör")
page = st.sidebar.radio(
    "Gezinme",
    ["🏠 Genel Bakış", "🔍 Takım İnceleme", "⚔️ Maç İnceleme",
     "📊 Grup Aşaması", "🏆 Eleme Turu", "📖 Metodoloji"],
)


# ─── Özel CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 5px 0;
    }
    .metric-card h2 {
        color: #e94560;
        margin: 0;
        font-size: 2.2rem;
    }
    .metric-card p {
        color: #a8a8b3;
        margin: 5px 0 0 0;
        font-size: 0.95rem;
    }
    .section-header {
        background: linear-gradient(90deg, #e94560 0%, #0f3460 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .match-card {
        background: #16213e;
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Renk paleti ──────────────────────────────────────────────────────────────
COLORS = px.colors.qualitative.Bold
PLOTLY_TEMPLATE = "plotly_dark"


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Genel Bakış
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Genel Bakış":
    st.markdown("# 🏆 2026 FIFA Dünya Kupası AI Simülatörü")
    st.markdown("*48 takım · 104 maç · 10.000 Monte Carlo simülasyonu*")
    st.info(
        "Bu dashboard, 2026 Dünya Kupası'nın 48 takımlı yeni formatını olasılıksal olarak simüle eder. "
        "Takım güçleri FIFA sıralaması, World Football Elo, kadro kalitesi, Dünya Kupası geçmişi ve xG göstergeleriyle modellenir. "
        "Sonuçlar kesin tahmin değil; 10.000 Monte Carlo senaryosundan çıkan veri bilimi analizidir."
    )
    st.caption(
        "Not: Bu proje FIFA ile resmi olarak ilişkili değildir ve bahis tavsiyesi değildir. "
        "İlk oynanan maçlar sabit sonuç olarak modele işlendi; grup aşamasında beraberlik serbesttir."
    )
    st.markdown("---")

    # Üst metrikler
    if mc.empty or matches[matches["stage"] == "Final"].empty:
        st.error("Gerekli sonuç dosyaları eksik veya boş. Lütfen final pipeline'ı yeniden çalıştırın.")
        st.stop()
    champion = mc.iloc[0]
    final_match = matches[matches["stage"] == "Final"].iloc[0]
    turkey_row = mc[mc["team"] == "Turkey"]
    turkey_row = turkey_row.iloc[0] if not turkey_row.empty else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <h2>🇦🇷</h2>
            <p>En Olası Şampiyon</p>
            <h2>{champion['champion_prob']*100:.1f}%</h2>
            <p>{champion['team']}</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <h2>🏟️</h2>
            <p>Merkezi Final</p>
            <h2>{final_match['home']} - {final_match['away']}</h2>
            <p>{final_match['home_goals']:.0f}–{final_match['away_goals']:.0f}</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <h2>48</h2>
            <p>Takım</p>
            <h2>104</h2>
            <p>Simüle Edilen Maç</p>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <h2>10K</h2>
            <p>Monte Carlo Simülasyonu</p>
            <h2>7</h2>
            <p>Veri Kaynağı</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    col_note1, col_note2 = st.columns(2)
    with col_note1:
        st.markdown("### 🧠 Skorlar neden sık 1-0 görünüyor?")
        st.write(
            "Futbolda tekil skor olasılıkları düşük ve birbirine yakındır. Poisson xG modelinde 1-0, 0-1 veya 1-1 gibi düşük skorlu sonuçlar çoğu dengeli maçta en yüksek tekil skor olabilir. "
            "Bu, modelin bütün maçlar kesin 1-0 biter dediği anlamına gelmez; skor dağılımında 1-1, 2-1, 0-0 gibi sonuçlar da yakın olasılıklardadır. "
            "Bu yüzden maç sayfalarında sadece merkezi skor değil, ilk 5 skor dağılımı ve kazanma/beraberlik/kaybetme olasılıkları birlikte verilmiştir."
        )
    with col_note2:
        st.markdown("### 🇹🇷 Türkiye Model Özeti")
        if turkey_row is not None:
            st.write(
                f"Türkiye'nin modelde Son 32'ye kalma olasılığı **%{turkey_row['knockout_prob']*100:.1f}**, "
                f"çeyrek final olasılığı **%{turkey_row['quarter_final_prob']*100:.1f}**, "
                f"final olasılığı **%{turkey_row['final_prob']*100:.1f}** ve şampiyonluk olasılığı **%{turkey_row['champion_prob']*100:.1f}**. "
                "Merkezi bracket'te Türkiye grup lideri çıkıp Son 32'de Ivory Coast ile eşleşiyor."
            )
        else:
            st.write("Türkiye verisi bulunamadı.")

    st.markdown("---")

    # Şampiyonluk olasılıkları grafiği
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('<p class="section-header">Şampiyonluk Olasılıkları (İlk 15)</p>',
                    unsafe_allow_html=True)
        top15 = mc.head(15).copy()
        top15["pct"] = top15["champion_prob"] * 100
        fig = px.bar(
            top15.sort_values("pct"),
            x="pct", y="team",
            orientation="h",
            color="pct",
            color_continuous_scale=["#0f3460", "#e94560"],
            template=PLOTLY_TEMPLATE,
            labels={"pct": "Olasılık (%)", "team": ""},
        )
        fig.update_layout(
            height=500,
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=20, t=10, b=10),
        )
        fig.update_traces(
            texttemplate="%{x:.1f}%", textposition="outside",
            textfont_size=12,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Favoriler birbirine yakın dağılıyor. En yüksek olasılığın %12 altında kalması, 48 takımlı formatta belirsizliğin yüksek olduğunu gösterir.")

    with col2:
        st.markdown('<p class="section-header">En Olası Final Eşleşmeleri</p>',
                    unsafe_allow_html=True)
        top_finals = finals.head(10).copy()
        top_finals["label"] = top_finals["team_a"] + " - " + top_finals["team_b"]
        top_finals["pct"] = top_finals["probability"] * 100
        fig2 = px.bar(
            top_finals.sort_values("pct"),
            x="pct", y="label",
            orientation="h",
            color="pct",
            color_continuous_scale=["#533483", "#e94560"],
            template=PLOTLY_TEMPLATE,
            labels={"pct": "Olasılık (%)", "label": ""},
        )
        fig2.update_layout(
            height=500,
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=20, t=10, b=10),
        )
        fig2.update_traces(
            texttemplate="%{x:.1f}%", textposition="outside",
            textfont_size=11,
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Final kombinasyonları tek bir eşleşmede yoğunlaşmıyor; turnuva yolu ve kura etkisi sonucu ciddi şekilde değiştiriyor.")

    # Aşama ulaşma olasılıkları
    st.markdown("---")
    st.markdown('<p class="section-header">Aşama Ulaşma Olasılıkları (İlk 10)</p>',
                unsafe_allow_html=True)
    top10 = mc.head(10).copy()
    stages = ["knockout_prob", "quarter_final_prob", "semi_final_prob", "final_prob", "champion_prob"]
    stage_labels = ["Son 32", "Çeyrek Final", "Yarı Final", "Final", "Şampiyon"]
    fig3 = go.Figure()
    for i, (col_name, label) in enumerate(zip(stages, stage_labels)):
        fig3.add_trace(go.Bar(
            name=label,
            x=top10["team"],
            y=top10[col_name] * 100,
            text=[f"{v:.0f}%" for v in top10[col_name] * 100],
            textposition="auto",
            textfont_size=9,
        ))
    fig3.update_layout(
        barmode="group",
        template=PLOTLY_TEMPLATE,
        height=450,
        yaxis_title="Olasılık (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Aşama olasılıkları 10.000 tam turnuva simülasyonunda takımların ilgili tura en az bir kez ulaşma oranlarından hesaplanır.")


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Takım İnceleme
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Takım İnceleme":
    st.markdown("# 🔍 Takım İnceleme")
    st.markdown("---")

    team_list = sorted(mc["team"].tolist())
    if not team_list:
        st.error("Takım verisi bulunamadı. Lütfen final pipeline'ı yeniden çalıştırın.")
        st.stop()
    default_team_idx = team_list.index("Brazil") if "Brazil" in team_list else 0
    selected = st.selectbox("Takım seçin", team_list, index=default_team_idx)
    if power[power["team"] == selected].empty or features[features["team"] == selected].empty:
        st.error(f"{selected} için detay verisi eksik.")
        st.stop()
    team_mc = mc[mc["team"] == selected].iloc[0]
    team_power_row = power[power["team"] == selected].iloc[0]
    team_feat = features[features["team"] == selected].iloc[0]

    # Ana metrikler
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🏆 Şampiyon", f"{team_mc['champion_prob']*100:.1f}%")
    with c2:
        st.metric("🥈 İkincilik", f"{team_mc['runner_up_prob']*100:.1f}%")
    with c3:
        st.metric("⚡ Takım Gücü", f"{team_mc['team_power']:.3f}")
    with c4:
        st.metric("🌍 FIFA Sırası", f"#{int(team_mc['fifa_rank'])}")
    with c5:
        st.metric("📊 ELO", f"{int(team_mc['elo_rating'])}")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Aşama Ulaşma Olasılıkları")
        stage_data = pd.DataFrame({
            "Aşama": ["Eleme", "Çeyrek Final", "Yarı Final", "Final", "Şampiyon"],
            "Olasılık": [
                team_mc["knockout_prob"],
                team_mc["quarter_final_prob"],
                team_mc["semi_final_prob"],
                team_mc["final_prob"],
                team_mc["champion_prob"],
            ]
        })
        stage_data["pct"] = stage_data["Olasılık"] * 100
        fig = px.bar(
            stage_data, x="Aşama", y="pct",
            color="pct",
            color_continuous_scale=["#0f3460", "#e94560"],
            template=PLOTLY_TEMPLATE,
            labels={"pct": "Olasılık (%)"},
        )
        fig.update_layout(
            height=350,
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig.update_traces(
            texttemplate="%{y:.1f}%", textposition="outside",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Takım Özellikleri")
        attr_names = ["Hücum", "Savunma", "EA FC İlk 11 OVR", "Kadro Derinliği"]
        attr_vals = [
            team_power_row.get("attack_strength", 0) * 100,
            team_power_row.get("defense_strength", 0) * 100,
            team_power_row.get("eafc_top11_avg_ovr", 0),
            safe_depth_score(features, team_feat.get("eafc_squad_depth", 0)),
        ]
        fig2 = go.Figure(data=go.Scatterpolar(
            r=attr_vals + [attr_vals[0]],
            theta=attr_names + [attr_names[0]],
            fill="toself",
            fillcolor="rgba(233, 69, 96, 0.2)",
            line_color="#e94560",
        ))
        fig2.update_layout(
            polar=dict(
                bgcolor="#16213e",
                radialaxis=dict(visible=True, range=[0, 100]),
            ),
            template=PLOTLY_TEMPLATE,
            height=350,
            margin=dict(l=40, r=40, t=10, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Takım bilgileri
    st.markdown("---")
    st.subheader("📋 Takım Detayları")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        - **Grup:** {team_mc['group']}
        - **Konfederasyon:** {team_feat.get('confederation', 'N/A')}
        - **DK Şampiyonlukları:** {int(team_feat.get('wc_titles', 0))}
        - **DK Katılımları:** {int(team_feat.get('wc_appearances', 0))}
        - **En İyi Derece:** {tr_best_finish(team_feat.get('best_finish', 'N/A'))}
        """)
    with c2:
        st.markdown(f"""
        - **⭐ Yıldız Oyuncu:** {team_power_row.get('eafc_star_player', 'N/A')}
        - **Yıldız Reytingi:** {team_power_row.get('eafc_star_player_rating', 'N/A')}
        - **Kadro Piyasa Değeri:** €{team_feat.get('squad_market_value_eur_m', 0):.0f}M
        - **Ev Sahibi:** {"✅" if team_feat.get('is_host', 0) else "❌"}
        - **İlk Katılım:** {"✅" if team_feat.get('is_debut', 0) else "❌"}
        """)
    with c3:
        st.markdown(f"""
        - **Son 10 Maç — G/B/M:** {int(team_feat.get('last_10_wins', 0))}/{int(team_feat.get('last_10_draws', 0))}/{int(team_feat.get('last_10_losses', 0))}
        - **Maç Başı Gol (2yıl):** {team_feat.get('goals_per_game_2yr', 0):.2f}
        - **Nötr Saha Kazanma:** {team_feat.get('neutral_ground_win_rate', 0):.1%}
        - **DK xG/maç:** {team_feat.get('wc_xG_per_game', 0):.2f}
        - **DK xGA/maç:** {team_feat.get('wc_xGA_per_game', 0):.2f}
        """)

    # Takımın maçları
    st.markdown("---")
    st.subheader("📅 Turnuva Yolu (En Olası Bracket)")
    team_matches = matches[
        (matches["home"] == selected) | (matches["away"] == selected)
    ].copy()
    if not team_matches.empty:
        team_matches["stage_tr"] = team_matches["stage"].map(tr_stage)
        display_cols = ["match_number", "stage_tr", "home", "away", "home_goals", "away_goals", "winner", "home_xg", "away_xg"]
        col_rename = {
            "match_number": "Maç No",
            "stage_tr": "Aşama",
            "home": "Ev Sahibi",
            "away": "Deplasman",
            "home_goals": "Ev Gol",
            "away_goals": "Dep Gol",
            "winner": "Kazanan",
            "home_xg": "Ev xG",
            "away_xg": "Dep xG",
        }
        available = [c for c in display_cols if c in team_matches.columns]
        disp = team_matches[available].rename(columns=col_rename).reset_index(drop=True)
        st.dataframe(
            disp,
            use_container_width=True,
            hide_index=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Maç İnceleme
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚔️ Maç İnceleme":
    st.markdown("# ⚔️ Maç İnceleme")
    st.markdown("---")

    # Aşama filtresi
    all_stages = scores["stage"].unique().tolist()
    stage_options = ["Tümü"] + [tr_stage(s) for s in all_stages]
    selected_stage_tr = st.selectbox("Aşamaya göre filtrele", stage_options)

    if selected_stage_tr == "Tümü":
        filtered = scores
    else:
        # Reverse lookup
        rev = {v: k for k, v in STAGE_TR.items()}
        filtered = scores[scores["stage"] == rev.get(selected_stage_tr, selected_stage_tr)]

    if filtered.empty:
        st.warning("Bu filtre için maç bulunamadı.")
        st.stop()
    match_labels = (filtered["home"] + " - " + filtered["away"] + " (" + filtered["stage"].map(tr_stage) + ")").tolist()
    match_idx = st.selectbox("Maç seçin", match_labels)

    if match_idx:
        idx = match_labels.index(match_idx)
        row = filtered.iloc[idx]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(f"🏠 {row['home']} Kazanır", f"{row['home_win_prob']*100:.1f}%")
        with c2:
            st.metric("🤝 Beraberlik", f"{row['draw_prob']*100:.1f}%")
        with c3:
            st.metric(f"✈️ {row['away']} Kazanır", f"{row['away_win_prob']*100:.1f}%")

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Maç Sonucu Olasılıkları")
            outcome_data = pd.DataFrame({
                "Sonuç": [f"{row['home']} Kazanır", "Beraberlik", f"{row['away']} Kazanır"],
                "Olasılık": [row["home_win_prob"]*100, row["draw_prob"]*100, row["away_win_prob"]*100],
            })
            fig = px.pie(
                outcome_data, values="Olasılık", names="Sonuç",
                color_discrete_sequence=["#e94560", "#533483", "#0f3460"],
                template=PLOTLY_TEMPLATE,
                hole=0.4,
            )
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("En Olası 5 Skor")
            # top_5_scorelines ayrıştır
            scorelines_raw = str(row.get("top_5_scorelines", ""))
            if scorelines_raw and scorelines_raw != "nan":
                parts = [s.strip() for s in scorelines_raw.split(";")]
                sc_data = []
                for p in parts:
                    try:
                        score_part = p.split("(")[0].strip()
                        pct_part = p.split("(")[1].replace(")", "").replace("%", "").strip()
                        sc_data.append({"Skor": score_part, "Olasılık": float(pct_part)})
                    except (IndexError, ValueError):
                        pass
                if sc_data:
                    sc_df = pd.DataFrame(sc_data)
                    fig2 = px.bar(
                        sc_df, x="Skor", y="Olasılık",
                        color="Olasılık",
                        color_continuous_scale=["#533483", "#e94560"],
                        template=PLOTLY_TEMPLATE,
                        labels={"Olasılık": "%"},
                    )
                    fig2.update_layout(
                        height=350,
                        coloraxis_showscale=False,
                        margin=dict(l=10, r=10, t=10, b=10),
                    )
                    fig2.update_traces(
                        texttemplate="%{y:.1f}%", textposition="outside",
                    )
                    st.plotly_chart(fig2, use_container_width=True)

        # xG karşılaştırması
        st.markdown("---")
        st.subheader("Beklenen Goller (xG)")
        xg_data = pd.DataFrame({
            "Takım": [row["home"], row["away"]],
            "xG": [row["home_xg"], row["away_xg"]],
        })
        fig3 = px.bar(
            xg_data, x="Takım", y="xG",
            color="Takım",
            color_discrete_sequence=["#e94560", "#0f3460"],
            template=PLOTLY_TEMPLATE,
        )
        fig3.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig3.update_traces(texttemplate="%{y:.2f}", textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Grup Aşaması
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Grup Aşaması":
    st.markdown("# 📊 Grup Aşaması — 12 Grup × 4 Takım")
    st.markdown("---")
    st.caption("Güncel veri: grup aşamasında beraberlik serbest; oynanan maçlar sabit sonuç olarak işlenir.")

    played = matches[matches["decided_by"] == "played_result"].copy()
    if not played.empty:
        st.markdown('<p class="section-header">Oynanan Maçlar</p>', unsafe_allow_html=True)
        played_display = played[["match_number", "home", "away", "home_goals", "away_goals", "winner"]].copy()
        played_display["Skor"] = played_display["home_goals"].astype(int).astype(str) + "-" + played_display["away_goals"].astype(int).astype(str)
        played_display = played_display[["match_number", "home", "away", "Skor", "winner"]]
        played_display.columns = ["Maç", "Ev", "Deplasman", "Skor", "Kazanan"]
        st.dataframe(played_display, use_container_width=True, hide_index=True)
        st.markdown("---")

    st.markdown('<p class="section-header">En İyi Üçüncüler</p>', unsafe_allow_html=True)
    thirds = groups[groups["rank"] == 3].copy()
    if not thirds.empty:
        fifa_lookup = features.set_index("team")["fifa_rank"].to_dict()
        thirds["fifa_rank"] = thirds["team"].map(fifa_lookup)
        thirds = thirds.sort_values(["points", "gd", "gf", "fifa_rank"], ascending=[False, False, False, True])
        thirds["Durum"] = ["Son 32" if i < 8 else "Elendi" for i in range(len(thirds))]
        thirds_display = thirds[["group", "team", "points", "gd", "gf", "fifa_rank", "Durum"]].copy()
        thirds_display.columns = ["Grup", "Takım", "Puan", "Averaj", "Atılan Gol", "FIFA Sırası", "Durum"]
        st.dataframe(thirds_display.reset_index(drop=True), use_container_width=True, hide_index=True)
        st.caption("2026 formatında 12 grup üçüncüsünden en iyi 8 takım Son 32'ye kalır. Sıralama: puan, averaj, atılan gol; fair-play verisi simüle edilmediği için eşitlikte FIFA sıralaması yedek kriterdir.")
        st.markdown("---")

    all_groups = sorted(groups["group"].unique())

    # 3 sütunlu grup grid'i
    for i in range(0, len(all_groups), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(all_groups):
                grp = all_groups[i + j]
                grp_data = groups[groups["group"] == grp].copy()
                with col:
                    st.markdown(f"### Grup {grp}")
                    display = grp_data[["team", "played", "wins", "draws", "losses", "gf", "ga", "gd", "points"]].copy()
                    display.columns = ["Takım", "O", "G", "B", "M", "AG", "YG", "Av", "P"]

                    st.dataframe(
                        display.reset_index(drop=True),
                        use_container_width=True,
                        hide_index=True,
                    )

    # Grup güç karşılaştırması
    st.markdown("---")
    st.markdown('<p class="section-header">Ortalama Grup Gücü</p>',
                unsafe_allow_html=True)
    group_avg = groups.groupby("group")["team_power"].mean().reset_index()
    group_avg.columns = ["Grup", "Ort. Güç"]
    group_avg = group_avg.sort_values("Ort. Güç", ascending=False)
    fig = px.bar(
        group_avg, x="Grup", y="Ort. Güç",
        color="Ort. Güç",
        color_continuous_scale=["#0f3460", "#e94560"],
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        height=350,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_traces(texttemplate="%{y:.3f}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Eleme Turu
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏆 Eleme Turu":
    st.markdown("# 🏆 Eleme Turu — En Olası Yol")
    st.markdown("---")
    st.write(
        "Bu sayfa tek bir kesin tahmin değil, modelin merkezi/en olası bracket yolunu gösterir. "
        "Eleme maçlarında 90 dakika beraberlik ihtimali ayrıca hesaplanır; tur atlayan takım uzatma/penaltı simülasyonu sonrası belirlenir."
    )
    knockout = matches[matches["stage"] != "Group Stage"].copy()

    st.markdown('<p class="section-header">Finale Giden Merkezi Yol</p>', unsafe_allow_html=True)
    path_matches = knockout[knockout["stage"].isin(["Quarter-final", "Semi-final", "Final"])].copy()
    path_order = ["Quarter-final", "Semi-final", "Final"]
    path_matches["stage_order"] = path_matches["stage"].map({s: i for i, s in enumerate(path_order)})
    path_matches = path_matches.sort_values(["stage_order", "match_number"])
    path_cols = st.columns(4)
    for idx, (_, m) in enumerate(path_matches.iterrows()):
        col = path_cols[idx % 4]
        with col:
            st.markdown(f"""
            <div class="match-card" style="min-height: 145px; border-left: 4px solid #e94560;">
                <div style="color:#e94560; font-size:0.78rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase;">
                    {tr_stage(m['stage'])} · Maç #{int(m['match_number'])}
                </div>
                <div style="margin-top:10px; font-size:1.05rem; color:white; line-height:1.55;">
                    {m['home']} <span style="color:#e94560; font-weight:800;">{int(m['home_goals'])}–{int(m['away_goals'])}</span> {m['away']}
                </div>
                <div style="margin-top:10px; color:#FFD700; font-weight:700;">
                    Kazanan: {m['winner']}
                </div>
                <div style="margin-top:6px; color:#a8a8b3; font-size:0.82rem;">
                    xG: {m['home_xg']:.2f} – {m['away_xg']:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.caption("Eski siyah bracket görseli yerine burası artık yayıncıya daha okunabilir kart görünümüyle merkezi yolu özetler.")
    st.markdown("---")

    # Aşama tab'ları
    ko_stages = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Third-place Match", "Final"]
    available_stages = [s for s in ko_stages if s in knockout["stage"].values]
    tab_labels = [tr_stage(s) for s in available_stages]

    tabs = st.tabs(tab_labels)
    for tab, stage_name in zip(tabs, available_stages):
        with tab:
            stage_matches = knockout[knockout["stage"] == stage_name].copy()
            for _, m in stage_matches.iterrows():
                is_winner_home = m["winner"] == m["home"]
                home_name = f"<b>{m['home']}</b>" if is_winner_home else m["home"]
                away_name = f"<b>{m['away']}</b>" if not is_winner_home else m["away"]

                # G/B/M çıkart
                wdl = ""
                decided = str(m.get("decided_by", ""))
                if "W/D/L=" in decided:
                    wdl_part = decided.split("W/D/L=")[1].split(";")[0]
                    wdl = f" | G/B/M: {wdl_part}"

                st.markdown(f"""
                <div class="match-card">
                    <span style="color: #a8a8b3; font-size: 0.8rem;">Maç #{int(m['match_number'])} — {tr_stage(stage_name)}</span><br>
                    <span style="font-size: 1.3rem;">
                        {home_name} 
                        <span style="color: #e94560; font-weight: 700;">{int(m['home_goals'])} – {int(m['away_goals'])}</span> 
                        {away_name}
                    </span><br>
                    <span style="color: #a8a8b3; font-size: 0.85rem;">
                        xG: {m['home_xg']:.2f} – {m['away_xg']:.2f}{wdl}
                    </span>
                </div>
                """, unsafe_allow_html=True)

    # Final vurgusu
    st.markdown("---")
    if knockout[knockout["stage"] == "Final"].empty:
        st.warning("Final maçı bulunamadı.")
        st.stop()
    final = knockout[knockout["stage"] == "Final"].iloc[0]
    st.markdown(f"""
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a2e, #16213e); border: 2px solid #e94560; border-radius: 15px;">
        <p style="color: #a8a8b3; font-size: 1rem;">🏆 FİNAL</p>
        <h1 style="color: white; margin: 10px 0;">{final['home']} {int(final['home_goals'])} – {int(final['away_goals'])} {final['away']}</h1>
        <p style="color: #e94560; font-size: 1.2rem;">xG: {final['home_xg']:.2f} – {final['away_xg']:.2f}</p>
        <p style="color: #a8a8b3;">🥇 Şampiyon: <span style="color: #FFD700; font-weight: 700;">{final['winner']}</span></p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA: Metodoloji
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Metodoloji":
    st.markdown("# 📖 Metodoloji")
    st.markdown("---")

    st.markdown("""
    ## Veri Kaynakları

    | Kaynak | Güncellik | Kullanım |
    |--------|-----------|----------|
    | **World Football Elo Ratings** | 2026 güncel veri, `eloratings.net/World.tsv` | Takım gücü, ELO sırası, önceki sıra ve sıra değişimi |
    | **FIFA Ranking** | Nisan 2026 sıralaması | Resmi takım sıralaması ve genel güç göstergesi |
    | **EA FC 25 oyuncu verisi** | 2024/25 oyun datası | İlk 11 OVR, ilk 23 OVR, hücum/orta saha/savunma/kaleci gücü, yıldız oyuncu, kadro derinliği |
    | **StatsBomb Open Data** | Dünya Kupası 2018/2022 açık verisi | xG/xGA geçmişi, şut ve maç içi performans göstergeleri |
    | **Dünya Kupası tarihçesi** | Tarihsel | Şampiyonluklar, katılımlar, en iyi derece, turnuva tecrübesi |
    | **Eleme / son form verileri** | Mevcut proje datası | Son maç performansı, gol ortalamaları, resmi/nötr maç kazanma oranları |
    | **Kadro piyasa değeri** | 2025/26 tahmini manuel değerler | Takım kalite ve kadro değeri göstergesi |

    ## Güncel ELO Entegrasyonu

    Bu versiyonda ELO değeri artık manuel tahmin değil. Pipeline başında:

    ```text
    src/update_elo_ratings.py
    ```

    çalışır ve `eloratings.net` üzerinden güncel dünya sıralamasını çeker. 48 takımın tamamı eşleşti:

    ```text
    Matched teams: 48 / 48
    Unmatched teams: 0
    ```

    Eski proje ELO tahmini kaybolmasın diye ayrı kolonda saklandı:

    ```text
    elo_rating_project_estimate
    ```

    Modelde kullanılan aktif değer:

    ```text
    elo_rating
    ```

    ## Model Mimarisi

    ### Takım Güç Skoru
    Birleşik takım gücü şu bileşenlerden oluşur:
    - Güncel World Football Elo puanı ve ELO sırası
    - FIFA sıralaması
    - EA FC 25 kadro kalitesi: ilk 11, ilk 23, pozisyon grupları, yıldız oyuncu, kadro derinliği
    - Son uluslararası form
    - Dünya Kupası tarihsel geçmişi
    - Kadro piyasa değeri
    - StatsBomb xG/xGA göstergeleri
    - Teknik direktör Dünya Kupası deneyimi

    ### Maç Simülasyonu
    - **Beklenen gol modeli:** Her maç için iki takımın hücum/savunma gücünden xG üretilir.
    - **Poisson skor dağılımı:** 0-0, 1-0, 1-1, 2-1 gibi tüm skorların olasılığı hesaplanır.
    - **Galibiyet/beraberlik/mağlubiyet:** Tek tek skor olasılıkları toplanarak bulunur.
    - **Skor dağılımı:** Dashboard'da her maç için en olası 5 skor gösterilir.

    ### Monte Carlo Simülasyonu
    - **10.000 tam turnuva simülasyonu** çalıştırılır.
    - Her simülasyonda maç sonuçları Poisson dağılımından örneklenir.
    - Takımların şampiyonluk, final, yarı final, çeyrek final ve eleme turuna ulaşma olasılıkları hesaplanır.
    - Final eşleşme kombinasyonları ayrıca takip edilir.
    - **Merkezi bracket**, en olası yolun okunabilir özetidir; tek kesin tahmin değildir.
    - İlk oynanan maçlar sabit sonuç olarak işlenir; kalan grup maçlarında beraberlik serbesttir.

    ### 2026 Üçüncü Takım Kuralı
    - 12 grup üçüncüsünden en iyi 8 takım Son 32 turuna kalır.
    - Sıralama puan, averaj ve atılan gole göre yapılır.
    - Fair-play kart verisi simüle edilmediği için eşitlikte FIFA sıralaması yedek kriter olarak kullanılır.
    - Üçüncü takımlar, FIFA/Wikipedia public candidate pool eşleşmelerine göre uygun grup liderleriyle eşleştirilir.

    ### Önemli Sınırlamalar
    - Merkezi bracket'teki skorlar, dağılımın en olası tekil skorudur. Futbolda bu değer çoğu maçta 1-0 / 0-1 çıkabilir; bu, modelin tüm maçları 1-0 beklediği anlamına gelmez.
    - Maç sayfalarında merkezi skorun yanında ilk 5 skor dağılımı ve kazanma/beraberlik/kaybetme olasılıkları birlikte verilmiştir.
    - FIFA üçüncü sıra dağılım tablosu için public candidate pool + uyumlu greedy fallback kullanılır; tam 495 kombinasyon tablosu uygulamaya kodlanmamıştır.
    - EA FC 25 reytingleri gerçek 2025/26 oyuncu formunun gerisinde kalabilir.
    - Model, turnuva sırasındaki sakatlıkları, cezaları veya taktiksel değişiklikleri hesaba katmaz.
    - Ev sahibi ülkeler için mevcut ELO/FIFA artışı dışında ayrı ev sahibi avantajı ayarlaması yoktur.
    - StatsBomb verisi Dünya Kupası 2018/2022 ile sınırlıdır.

    ## Yorumlama Rehberi

    ⚠️ **Bu bir olasılık modeli, kesin tahmin değil.**

    Simülatör tek cevap üretmez; olasılık dağılımı üretir. Örneğin merkezi final `France - Argentina 0-1` göründüğünde bu şunu ifade eder:

    ```text
    Argentina final için daha olası taraf.
    0-1, o eşleşmedeki en olası kazanan skorlarından biri.
    Ama 1-1, 1-2, 1-0, 2-1 gibi skorlar da yakın olasılıklara sahip.
    ```

    Güncel ELO entegrasyonu sonrası Monte Carlo favorisi:

    ```text
    Argentina ≈ %11.5
    Spain ≈ %11.3
    France ≈ %8.9
    ```

    Bu düşük yüzdeler normaldir: 48 takımlı formatta hiçbir takım turnuvayı domine etmiyor, belirsizlik yüksek kalıyor.

    > Bu proje FIFA ile resmi olarak ilişkili değildir. Sonuçlar bağımsız veri bilimi simülasyonudur; bahis tavsiyesi veya kesin tahmin değildir.
    """)

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #a8a8b3; padding: 20px;">
        <p>Geliştiren: <b>Cem Yıldız</b> — Veri Bilimi & Yapay Zeka</p>
        <p>Araçlar: Python · Pandas · Plotly · Streamlit · World Football Elo · StatsBomb · EA FC 25</p>
        <p>GitHub: <a href="https://github.com/cemyildizcy" style="color: #e94560;">@cemyildizcy</a></p>
    </div>
    """, unsafe_allow_html=True)


# ─── Alt bilgi ────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="color: #a8a8b3; font-size: 0.8rem;">
    <p>📊 Veri: FIFA, World Football Elo, EA FC 25, StatsBomb</p>
    <p>🔬 Model: Poisson xG + 10K Monte Carlo</p>
    <p>⚽ 10.000 simülasyon</p>
    <p>Geliştiren: Cem Yıldız</p>
</div>
""", unsafe_allow_html=True)

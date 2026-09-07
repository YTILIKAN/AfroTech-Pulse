# dashboard/app.py — Dashboard public AfroTech Pulse (V1) : carte, secteurs, timeline.
#
# Lancer : streamlit run dashboard/app.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

import database
from dashboard.aggregations import par_pays, par_secteur, par_semaine
from dashboard.data import charger_articles, fenetre_semaines, lundi_courant
from dashboard.enrichment import SECTEUR_DEFAUT, enrichir
from dashboard.theme import ACCENT, ECHELLE_SEQ, ENCRE_DOUCE, PLOTLY_CONFIG, styliser

N_SEMAINES = 4

st.set_page_config(
    page_title="AfroTech Pulse — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 3rem; padding-bottom: 4rem; max-width: 1100px;}
      [data-testid="stMetric"] {
          background: #F4F1EC; border: 1px solid #E7E2D9;
          border-radius: 12px; padding: 1rem 1.2rem;
      }
      [data-testid="stMetricValue"] {font-size: 2rem; font-weight: 700;}
      [data-testid="stMetricLabel"] {color: #6B655C;}
      h3 {margin-top: 0.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner="Chargement des articles…")
def _charger_periode():
    depuis = fenetre_semaines(semaines=N_SEMAINES)
    jusqua = lundi_courant()
    articles = enrichir(charger_articles(database.DB_PATH, depuis=depuis, jusqua=jusqua))
    return articles, depuis


def _legende(texte):
    st.markdown(
        f"<p style='color:{ENCRE_DOUCE};font-size:0.85rem;margin:-0.4rem 0 1.2rem'>{texte}</p>",
        unsafe_allow_html=True,
    )


articles, depuis = _charger_periode()

_nb = f"{len(articles):,}".replace(",", " ")

st.title("Le pouls de l'IA en Afrique")
st.markdown(
    f"<p style='color:{ENCRE_DOUCE};font-size:1rem;margin-top:-0.6rem'>"
    f"Ce que révèlent {_nb} articles mentionnant le continent, collectés sur 50+ sources "
    f"sur les {N_SEMAINES} dernières semaines complètes (depuis le "
    f"{depuis.strftime('%d/%m/%Y')}).</p>",
    unsafe_allow_html=True,
)

if not articles:
    st.warning(
        "Aucun article sur les 4 dernières semaines. "
        "Le pipeline de collecte a-t-il tourné récemment ?"
    )
    st.stop()

comptes_pays = par_pays(articles)
comptes_secteur = par_secteur(articles)
comptes_semaine = par_semaine(articles, n_semaines=N_SEMAINES)

pays_tete = max(comptes_pays.items(), key=lambda kv: kv[1]) if comptes_pays else None
noms_pays = {a["pays_iso"]: a["pays_nom"] for a in articles if a["pays_iso"]}

k1, k2, k3 = st.columns(3)
k1.metric("Articles analysés", _nb)
k2.metric("Pays africains couverts", len(comptes_pays))
k3.metric(
    "Pays le plus actif",
    f"{noms_pays.get(pays_tete[0], '—')} · {pays_tete[1]}" if pays_tete else "—",
)

st.divider()

# --- Carte ---------------------------------------------------------------------
st.subheader("Où l'IA fait parler d'elle")
_legende("Nombre d'articles mentionnant chaque pays. Passe la souris pour le détail.")

if comptes_pays:
    df_pays = pd.DataFrame(
        [
            {"iso": iso, "pays": noms_pays.get(iso, iso), "articles": n}
            for iso, n in comptes_pays.items()
        ]
    )
    fig_pays = px.choropleth(
        df_pays,
        locations="iso",
        color="articles",
        scope="africa",
        color_continuous_scale=ECHELLE_SEQ,
        hover_name="pays",
        hover_data={"iso": False, "articles": True},
        labels={"articles": "Articles"},
    )
    fig_pays.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>%{z} articles<extra></extra>",
        marker_line_color="#FFFFFF",
        marker_line_width=0.6,
    )
    st.plotly_chart(styliser(fig_pays, hauteur=460), config=PLOTLY_CONFIG, width="stretch")
else:
    st.info("Aucun pays africain identifié sur la période.")

st.divider()

# --- Secteurs ----------------------------------------------------------------
st.subheader("Quels secteurs sont sous les projecteurs")
_legende(
    "Un article peut relever de plusieurs secteurs. « Généraliste » = aucun secteur "
    "spécifique détecté (politique IA, recherche, infrastructure…)."
)

df_secteur = pd.DataFrame(
    sorted(comptes_secteur.items(), key=lambda kv: kv[1]),
    columns=["secteur", "articles"],
)
df_secteur["libelle"] = df_secteur["secteur"].str.capitalize()
fig_secteur = px.bar(
    df_secteur, x="articles", y="libelle", orientation="h", text="articles"
)
fig_secteur.update_traces(
    marker_color=ACCENT,
    marker_cornerradius=4,
    textposition="outside",
    textfont=dict(size=12),
    cliponaxis=False,
    hovertemplate="%{y} — %{x} articles<extra></extra>",
)
fig_secteur.update_layout(
    xaxis=dict(visible=False),
    yaxis=dict(title="", showgrid=False),
    bargap=0.45,
)
st.plotly_chart(
    styliser(fig_secteur, hauteur=60 + 46 * len(df_secteur)),
    config=PLOTLY_CONFIG,
    width="stretch",
)

st.divider()

# --- Timeline ---------------------------------------------------------------
st.subheader("Le rythme de l'actualité, semaine par semaine")
_legende("Nombre d'articles pertinents collectés chaque semaine (lundi → dimanche).")

df_semaine = pd.DataFrame(comptes_semaine, columns=["semaine", "articles"])
df_semaine["libelle"] = pd.to_datetime(df_semaine["semaine"]).dt.strftime("%d %b")
fig_semaine = px.bar(df_semaine, x="libelle", y="articles", text="articles")
fig_semaine.update_traces(
    marker_color=ACCENT,
    marker_cornerradius=4,
    textposition="outside",
    textfont=dict(size=12),
    cliponaxis=False,
    hovertemplate="Semaine du %{x} — %{y} articles<extra></extra>",
)
fig_semaine.update_layout(
    xaxis=dict(title="", showgrid=False),
    yaxis=dict(visible=False),
    bargap=0.5,
)
st.plotly_chart(styliser(fig_semaine, hauteur=320), config=PLOTLY_CONFIG, width="stretch")

st.divider()
st.caption(
    "AfroTech Pulse — la voix digitale de la communauté Y'TILIKAN. "
    "Données mises à jour quotidiennement · Dashboard V1"
)

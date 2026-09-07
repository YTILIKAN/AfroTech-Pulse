# dashboard/app.py — Dashboard public AfroTech Pulse (V2) : filtres, carte, secteurs,
# timeline, nuage de mots, top acteurs et comparaison entre pays.
#
# Lancer : streamlit run dashboard/app.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud

import database
from dashboard.aggregations import comparer_pays, par_pays, par_secteur, par_semaine
from dashboard.data import charger_articles
from dashboard.enrichment import SECTEUR_DEFAUT, enrichir
from dashboard.entities import charger_prefixes_medias, extraire_entites
from dashboard.filters import (
    PERIODE_DEFAUT,
    PERIODE_MAX,
    PERIODES,
    bornes_periode,
    filtrer,
    options_pays,
    options_secteurs,
)
from dashboard.text import compter_mots
from dashboard.theme import ACCENT, ECHELLE_SEQ, ENCRE_DOUCE, PLOTLY_CONFIG, styliser

NB_ACTEURS = 12
NB_PAYS_COMPARES = 3

st.set_page_config(
    page_title="AfroTech Pulse — Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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
def _charger_corpus():
    """Charge une seule fois la fenêtre la plus large ; les périodes plus courtes sont
    dérivées en mémoire. ~1100 articles enrichis en 0,2 s : inutile de relire SQLite à
    chaque changement de filtre."""
    depuis, jusqua = bornes_periode(PERIODE_MAX)
    return enrichir(charger_articles(database.DB_PATH, depuis=depuis, jusqua=jusqua))


@st.cache_data(ttl=3600)
def _prefixes_medias():
    return charger_prefixes_medias()


def _legende(texte):
    st.markdown(
        f"<p style='color:{ENCRE_DOUCE};font-size:0.85rem;margin:-0.4rem 0 1.2rem'>{texte}</p>",
        unsafe_allow_html=True,
    )


corpus = _charger_corpus()

# --- Filtres ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Filtres")

    n_semaines = st.radio(
        "Période",
        PERIODES,
        index=PERIODES.index(PERIODE_DEFAUT),
        format_func=lambda n: f"{n} dernières semaines",
    )

    depuis, jusqua = bornes_periode(n_semaines)
    corpus_periode = filtrer(corpus, depuis=depuis, jusqua=jusqua)

    # Les options sont construites sur la période retenue : proposer un pays qui ne
    # renverrait aucun article serait trompeur.
    choix_pays = options_pays(corpus_periode)
    libelles_pays = {iso: f"{nom} ({n})" for iso, nom, n in choix_pays}
    pays_selectionnes = st.multiselect(
        "Pays",
        [iso for iso, _nom, _n in choix_pays],
        format_func=lambda iso: libelles_pays.get(iso, iso),
        placeholder="Tous les pays",
    )

    choix_secteurs = options_secteurs(corpus_periode)
    libelles_secteurs = {s: f"{s.capitalize()} ({n})" for s, n in choix_secteurs}
    secteurs_selectionnes = st.multiselect(
        "Secteur",
        [s for s, _n in choix_secteurs],
        format_func=lambda s: libelles_secteurs.get(s, s),
        placeholder="Tous les secteurs",
    )

    st.caption(
        "Les filtres s'appliquent simultanément à toutes les visualisations. "
        "Aucune sélection = tout est inclus."
    )

articles = filtrer(
    corpus_periode, pays_iso=pays_selectionnes, secteurs=secteurs_selectionnes
)

# --- En-tête ------------------------------------------------------------------
_nb = f"{len(articles):,}".replace(",", " ")

st.title("Le pouls de l'IA en Afrique")
st.markdown(
    f"<p style='color:{ENCRE_DOUCE};font-size:1rem;margin-top:-0.6rem'>"
    f"Ce que révèlent {_nb} articles mentionnant le continent, collectés sur 50+ sources "
    f"sur les {n_semaines} dernières semaines complètes (depuis le "
    f"{depuis.strftime('%d/%m/%Y')}).</p>",
    unsafe_allow_html=True,
)

if not corpus:
    st.warning(
        "Aucun article sur les dernières semaines. "
        "Le pipeline de collecte a-t-il tourné récemment ?"
    )
    st.stop()

if not articles:
    st.warning(
        "Aucun article ne correspond à ces filtres. "
        "Élargis la période ou retire un critère dans le panneau de gauche."
    )
    st.stop()

comptes_pays = par_pays(articles)
comptes_secteur = par_secteur(articles)
comptes_semaine = par_semaine(articles, n_semaines=n_semaines)

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

# --- Nuage de mots ------------------------------------------------------------
st.subheader("Les mots de la période")
_legende(
    "Vocabulaire des titres, résumés et extraits des articles retenus. Les mots outils et "
    "le vocabulaire commun à tout le corpus (« IA », « Afrique ») sont écartés : ils "
    "écraseraient le nuage sans rien révéler."
)

frequences = compter_mots(articles, prefixes_exclus=_prefixes_medias())

if frequences:
    def _couleur(*_args, font_size=12, **_kwargs):
        # Une seule teinte, plus soutenue quand le mot est fréquent : même logique que
        # l'échelle séquentielle de la carte.
        palette = ["#F1C89B", "#E39A5E", "#CB6234", ACCENT, "#8A2D19"]
        return palette[min(font_size // 18, len(palette) - 1)]

    nuage = WordCloud(
        width=1100,
        height=420,
        mode="RGBA",
        background_color=None,
        color_func=_couleur,
        prefer_horizontal=0.9,
        max_words=120,
        relative_scaling=0.5,
    ).generate_from_frequencies(frequences)
    st.image(nuage.to_array(), width="stretch")
else:
    st.info("Pas assez de texte sur cette sélection pour construire un nuage de mots.")

st.divider()

# --- Top acteurs --------------------------------------------------------------
st.subheader("Les acteurs les plus cités")
_legende(
    "Entreprises et organisations repérées dans le texte des articles, comptées une fois "
    "par article. Les noms de sources, les pays et les villes sont exclus : ils sont déjà "
    "portés par la carte, ou ne désignent pas un acteur."
)

acteurs = extraire_entites(articles, limite=NB_ACTEURS)

if acteurs:
    df_acteurs = pd.DataFrame(acteurs, columns=["acteur", "articles"]).iloc[::-1]
    fig_acteurs = px.bar(
        df_acteurs, x="articles", y="acteur", orientation="h", text="articles"
    )
    fig_acteurs.update_traces(
        marker_color=ACCENT,
        marker_cornerradius=4,
        textposition="outside",
        textfont=dict(size=12),
        cliponaxis=False,
        hovertemplate="%{y} — cité dans %{x} articles<extra></extra>",
    )
    fig_acteurs.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(title="", showgrid=False),
        bargap=0.4,
    )
    st.plotly_chart(
        styliser(fig_acteurs, hauteur=60 + 34 * len(df_acteurs)),
        config=PLOTLY_CONFIG,
        width="stretch",
    )
else:
    st.info("Aucun acteur identifiable sur cette sélection.")

st.divider()

# --- Comparaison entre pays ---------------------------------------------------
st.subheader("Comparer des pays")
_legende(
    "Choisis au moins deux pays pour confronter leur volume d'articles et leur profil "
    "sectoriel. Cette vue suit la période et le secteur choisis à gauche, mais garde sa "
    "propre sélection de pays."
)

# Le filtre pays de la barre latérale n'est volontairement pas appliqué ici : on
# comparerait sinon des pays qu'il vient précisément d'exclure.
base_comparaison = filtrer(corpus_periode, secteurs=secteurs_selectionnes)
choix_comparaison = options_pays(base_comparaison)
libelles_comparaison = {iso: nom for iso, nom, _n in choix_comparaison}

# La sélection de la barre latérale sert de point de départ, mais seulement si elle porte
# déjà sur au moins deux pays : filtrer sur un seul pays ne doit pas faire disparaître la
# comparaison, qui retombe alors sur les pays les plus couverts.
defaut = [iso for iso in pays_selectionnes if iso in libelles_comparaison]
if len(defaut) < 2:
    defaut = [iso for iso, _nom, _n in choix_comparaison[:NB_PAYS_COMPARES]]

pays_compares = st.multiselect(
    "Pays à comparer",
    [iso for iso, _nom, _n in choix_comparaison],
    default=defaut,
    format_func=lambda iso: libelles_comparaison.get(iso, iso),
)

if len(pays_compares) < 2:
    st.info("Sélectionne au moins deux pays pour afficher la comparaison.")
else:
    comparaison = comparer_pays(base_comparaison, pays_compares)

    colonnes = st.columns(len(pays_compares))
    for colonne, iso in zip(colonnes, pays_compares):
        donnees = comparaison[iso]
        secteur_fort = (
            max(donnees["secteurs"].items(), key=lambda kv: kv[1])[0].capitalize()
            if donnees["secteurs"] else "—"
        )
        colonne.metric(donnees["nom"], f"{donnees['articles']} articles", secteur_fort)

    lignes = [
        {"pays": donnees["nom"], "secteur": secteur.capitalize(), "articles": n}
        for donnees in comparaison.values()
        for secteur, n in (donnees["secteurs"] or {SECTEUR_DEFAUT: 0}).items()
    ]
    df_comparaison = pd.DataFrame(lignes)

    fig_comparaison = px.bar(
        df_comparaison,
        x="pays",
        y="articles",
        color="secteur",
        barmode="group",
        text="articles",
        color_discrete_sequence=["#8A2D19", ACCENT, "#E39A5E", "#F1C89B", "#C9C2B4"],
    )
    fig_comparaison.update_traces(
        marker_cornerradius=4,
        textposition="outside",
        textfont=dict(size=11),
        cliponaxis=False,
        hovertemplate="%{x} — %{y} articles<extra>%{fullData.name}</extra>",
    )
    fig_comparaison.update_layout(
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(visible=False),
        bargap=0.35,
        showlegend=True,
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(
        styliser(fig_comparaison, hauteur=420), config=PLOTLY_CONFIG, width="stretch"
    )

st.divider()
st.caption(
    "AfroTech Pulse — la voix digitale de la communauté Y'TILIKAN. "
    "Données mises à jour quotidiennement · Dashboard V2"
)

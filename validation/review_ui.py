# validation/review_ui.py — Interface Streamlit de validation humaine (15 min, lundi matin)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import database

STATUTS_STYLE = {
    "brouillon": ("gray", "📝"),
    "en_revue": ("blue", "🔎"),
    "validé": ("green", "✅"),
    "rejeté": ("red", "❌"),
    "publié": ("violet", "🚀"),
}

st.set_page_config(page_title="AfroTech Pulse — Validation", page_icon="📰")

database.creer_base()

newsletter = database.derniere_newsletter_brouillon()

st.title("📰 Validation de la newsletter")

if newsletter is None:
    st.info("Aucune newsletter en attente de validation (statut 'brouillon').")
    st.stop()

newsletter_id, contenu, nb_articles, statut, date_generation = newsletter
couleur, icone = STATUTS_STYLE.get(statut, ("gray", "📄"))

col_sous_titre, col_badge = st.columns([3, 1])
col_sous_titre.subheader(f"Newsletter #{newsletter_id}")
with col_badge:
    st.badge(statut, icon=icone, color=couleur)

col_a, col_b = st.columns(2)
col_a.metric("Articles", nb_articles)
col_b.metric("Générée le", date_generation.split("T")[0])

st.divider()

auteur = st.text_input("Ton prénom (validateur)", placeholder="ex. Steve")

tab_edition, tab_apercu, tab_historique = st.tabs(["✏️ Édition", "👁️ Aperçu", "🕘 Historique"])

with tab_edition:
    contenu_edite = st.text_area(
        "Contenu de la newsletter", value=contenu, height=450, label_visibility="collapsed"
    )

with tab_apercu:
    st.markdown(contenu_edite)

with tab_historique:
    historique = database.historique_newsletter(newsletter_id)
    if historique:
        for ancien, nouveau, auteur_ligne, horodatage in historique:
            couleur_h, icone_h = STATUTS_STYLE.get(nouveau, ("gray", "📄"))
            with st.container(border=True):
                ligne_gauche, ligne_droite = st.columns([3, 2])
                ligne_gauche.markdown(f"**{ancien} → {nouveau}**")
                with ligne_droite:
                    st.badge(nouveau, icon=icone_h, color=couleur_h)
                st.caption(f"Par **{auteur_ligne}** — {horodatage}")
    else:
        st.caption("Aucune transition enregistrée pour cette newsletter.")

st.divider()

col1, col2, col3 = st.columns(3)
modifier = col1.button("Modifier", use_container_width=True)
valider = col2.button("Valider", type="primary", use_container_width=True)
rejeter = col3.button("Rejeter", use_container_width=True)


def _finaliser(newsletter_id, decision, auteur):
    database.changer_statut_newsletter(newsletter_id, "en_revue", auteur)
    database.changer_statut_newsletter(newsletter_id, decision, auteur)


if modifier or valider or rejeter:
    if not auteur.strip():
        st.error("Indique ton prénom avant de valider une action.")
        st.stop()

    if contenu_edite != contenu:
        database.modifier_contenu_newsletter(newsletter_id, contenu_edite)

    if valider:
        _finaliser(newsletter_id, "validé", auteur)
        st.success(f"Newsletter #{newsletter_id} validée par {auteur}.")
    elif rejeter:
        _finaliser(newsletter_id, "rejeté", auteur)
        st.warning(f"Newsletter #{newsletter_id} rejetée par {auteur}.")
    else:
        st.success("Modifications enregistrées.")

    st.rerun()

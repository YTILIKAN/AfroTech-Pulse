# archive/app.py — Archive publique : toutes les éditions publiées, cherchables en full-text

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import database
from archive.search import indexer_editions, rechercher

st.set_page_config(page_title="AfroTech Pulse — Archive", page_icon="📚", layout="centered")

database.creer_base()

st.title("📚 Archive AfroTech Pulse")
st.caption("Toutes les éditions publiées, cherchables mot à mot.")

with st.sidebar:
    st.markdown("### Maintenance")
    st.caption(
        "À utiliser si la base a été modifiée à la main : la réindexation est automatique "
        "après chaque publication."
    )
    if st.button("🔄 Réindexer l'archive", use_container_width=True):
        with st.spinner("Réindexation en cours..."):
            nb_indexees = indexer_editions()
        st.success(f"{nb_indexees} édition(s) réindexée(s).")

requete = st.text_input(
    "Rechercher dans les éditions",
    placeholder="ex. fintech, Kenya, intelligence artificielle",
    label_visibility="collapsed",
)

resultats = rechercher(requete)
terme = requete.strip()

if terme:
    if resultats:
        st.markdown(f"**{len(resultats)}** résultat(s) pour « {terme} »")
    else:
        st.info(
            f"Aucune édition ne contient « {terme} ». "
            "Essaie un mot-clé plus court ou vide le champ pour voir toute l'archive."
        )
elif resultats:
    st.markdown(f"**{len(resultats)}** édition(s) publiée(s), de la plus récente à la plus ancienne")
else:
    st.info("Aucune édition publiée pour le moment. L'archive se remplit à chaque publication.")

st.divider()

for edition in resultats:
    with st.container(border=True):
        ligne_gauche, ligne_droite = st.columns([3, 1])
        ligne_gauche.subheader(edition["titre"])
        with ligne_droite:
            st.badge("publié", icon="🚀", color="violet")

        col_date, col_articles = st.columns(2)
        col_date.caption(f"📅 {edition['date_generation'].split('T')[0]}")
        col_articles.caption(f"📰 {edition['nb_articles']} article(s) — édition #{edition['id']}")

        st.markdown(edition["extrait"])

        with st.expander("Lire l'édition complète"):
            st.markdown(edition["contenu"])

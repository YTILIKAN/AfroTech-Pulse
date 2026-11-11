"""Application Streamlit multipage — Dashboard, Archive, Validation en un seul service.

Regroupe les trois interfaces qui étaient lancées séparément. En hébergement, ce
fichier n'est **pas** lancé directement : ``serve.py`` démarre d'abord le
planificateur des tâches puis lance cette app. En local, les deux marchent :

    streamlit run streamlit_app.py     # les 3 interfaces, sans le planificateur
    python serve.py                    # + le planificateur (comme en production)

Les interfaces restent aussi lançables à l'unité (``streamlit run dashboard/app.py``…).
"""

import streamlit as st

import database

database.creer_base()

st.set_page_config(page_title="AfroTech Pulse", page_icon="📰", layout="wide")

_PAGES = [
    st.Page("dashboard/app.py", title="Dashboard", icon="📊", url_path="dashboard", default=True),
    st.Page("archive/app.py", title="Archive", icon="📚", url_path="archive"),
    st.Page("validation/review_ui.py", title="Validation", icon="📰", url_path="validation"),
]

st.navigation(_PAGES).run()

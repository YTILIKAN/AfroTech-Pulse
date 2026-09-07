import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database

APP_PATH = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")
DB_PROD = Path(__file__).resolve().parent.parent / "afrotech.db"


@pytest.fixture(autouse=True)
def _vider_cache_streamlit():
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_page_se_charge_sur_une_copie_de_la_base_de_prod(monkeypatch, tmp_path):
    if not DB_PROD.exists():
        pytest.skip("afrotech.db absente")
    copie = tmp_path / "afrotech.db"
    shutil.copy(DB_PROD, copie)
    monkeypatch.setattr(database, "DB_PATH", str(copie))

    at = AppTest.from_file(APP_PATH, default_timeout=60).run()

    assert not at.exception, "la page ne doit pas lever d'exception avec les données de prod"
    # V1 : carte + secteurs + timeline. La V2 (S11) ajoute top acteurs + comparaison
    # pays, soit 5 graphiques Plotly, le nuage de mots étant rendu en image.
    assert len(at.get("plotly_chart")) == 5
    assert any("pouls de l'IA" in h.value for h in at.title)


def test_page_affiche_un_message_si_aucun_article_sur_la_periode(monkeypatch, tmp_path):
    vide = tmp_path / "afrotech.db"
    monkeypatch.setattr(database, "DB_PATH", str(vide))
    database.creer_base()

    at = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert not at.exception
    assert any("Aucun article" in w.value for w in at.warning)
    assert len(at.get("plotly_chart")) == 0

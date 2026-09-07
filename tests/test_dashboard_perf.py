import time
from pathlib import Path

import pytest

import database
from dashboard.aggregations import par_pays, par_secteur, par_semaine
from dashboard.data import charger_articles, fenetre_semaines
from dashboard.enrichment import enrichir

DB_PROD = Path(__file__).resolve().parent.parent / "afrotech.db"

SEUIL_SECONDES = 3.0


def test_chargement_et_agregation_sous_le_seuil_sur_la_base_de_prod():
    if not DB_PROD.exists():
        pytest.skip("afrotech.db absente")
    database.DB_PATH = str(DB_PROD)

    debut = time.perf_counter()
    articles = enrichir(charger_articles(str(DB_PROD), depuis=fenetre_semaines(semaines=4)))
    par_pays(articles)
    par_secteur(articles)
    par_semaine(articles, n_semaines=4)
    duree = time.perf_counter() - debut

    print(f"\n[PERF] {len(articles)} articles enrichis + agrégés en {duree:.2f}s "
          f"(seuil : {SEUIL_SECONDES}s)")
    assert duree < SEUIL_SECONDES, (
        f"chargement + enrichissement + agrégation trop lent ({duree:.2f}s) — "
        "optimiser enrichment.py (regex compilée unique) avant de dépasser le seuil"
    )

from datetime import datetime

import database
from dashboard.data import charger_articles, fenetre_semaines, lundi_courant


def _db(monkeypatch, tmp_path):
    test_db = tmp_path / "dashboard_data_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()
    return str(test_db)


def test_charger_articles_parse_les_dates_et_filtre_par_periode(monkeypatch, tmp_path):
    db = _db(monkeypatch, tmp_path)
    database.sauvegarder_article("Vieux", "https://e.com/1", "src", "2026-01-01T09:00:00", "corps", 50)
    database.sauvegarder_article("Récent", "https://e.com/2", "src", "2026-08-20T09:00:00", "corps", 50)
    database.sauvegarder_article("Avec Z", "https://e.com/3", "src", "2026-08-25T09:00:00Z", "corps", 50)
    database.sauvegarder_article("Sans date", "https://e.com/4", "src", None, "corps", 50)

    tous = charger_articles(db_path=db)
    titres = {a["titre"] for a in tous}
    assert titres == {"Vieux", "Récent", "Avec Z"}, "un article sans date_pub parsable est ignoré"
    assert all(isinstance(a["date_pub"], datetime) for a in tous)
    assert all(a["date_pub"].tzinfo is None for a in tous), "les dates sont normalisées en naïf UTC"

    depuis = datetime(2026, 8, 1)
    recents = {a["titre"] for a in charger_articles(db_path=db, depuis=depuis)}
    assert recents == {"Récent", "Avec Z"}


def test_charger_articles_borne_haute_jusqua_est_exclue(monkeypatch, tmp_path):
    db = _db(monkeypatch, tmp_path)
    database.sauvegarder_article("Avant", "https://e.com/a", "src", "2026-08-20T09:00:00", "x", 50)
    database.sauvegarder_article("Pile", "https://e.com/b", "src", "2026-08-24T00:00:00", "x", 50)
    database.sauvegarder_article("Après", "https://e.com/c", "src", "2026-08-25T09:00:00", "x", 50)

    titres = {a["titre"] for a in charger_articles(db_path=db, jusqua=datetime(2026, 8, 24))}
    assert titres == {"Avant"}, "jusqua est une borne exclue"


def test_charger_articles_filtre_les_articles_sans_signal_africain(monkeypatch, tmp_path):
    db = _db(monkeypatch, tmp_path)
    database.sauvegarder_article("Pertinent", "https://e.com/p", "src", "2026-08-20T09:00:00", "x", 20)
    database.sauvegarder_article("Hors sujet", "https://e.com/h", "src", "2026-08-20T09:00:00", "x", 0)

    assert {a["titre"] for a in charger_articles(db_path=db)} == {"Pertinent"}
    assert {a["titre"] for a in charger_articles(db_path=db, score_min=0)} == {"Pertinent", "Hors sujet"}


def test_charger_articles_base_vide_retourne_liste_vide(monkeypatch, tmp_path):
    db = _db(monkeypatch, tmp_path)
    assert charger_articles(db_path=db) == []


def test_fenetre_couvre_4_semaines_completes_alignees_lundi(monkeypatch, tmp_path):
    # mercredi 2026-09-09 -> semaine en cours = lundi 2026-09-07 (borne haute, exclue)
    mercredi = datetime(2026, 9, 9, 15, 30)
    assert lundi_courant(mercredi) == datetime(2026, 9, 7)
    debut = fenetre_semaines(maintenant=mercredi, semaines=4)
    assert debut == datetime(2026, 8, 10, 0, 0, 0)  # 4 semaines pleines avant le 07/09
    assert debut.weekday() == 0

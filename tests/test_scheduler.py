import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database
import scheduler

RACINE = Path(__file__).resolve().parent.parent


def test_les_cinq_jobs_sont_planifies_aux_horaires_des_anciens_crons():
    planificateur = scheduler.construire_planificateur()
    jobs = {job.id: job for job in planificateur.get_jobs()}

    assert set(jobs) == {
        "scrape_quotidien",
        "redaction_hebdomadaire",
        "rappel_validation",
        "publication_hebdomadaire",
        "sauvegarde_base",
    }

    def champs(nom):
        return {f.name: str(f) for f in jobs[nom].trigger.fields}

    assert (champs("scrape_quotidien")["hour"], champs("scrape_quotidien")["minute"]) == ("6", "0")
    assert champs("redaction_hebdomadaire")["day_of_week"] == "sun"
    assert champs("redaction_hebdomadaire")["hour"] == "20"
    assert champs("rappel_validation")["day_of_week"] == "mon"
    assert champs("rappel_validation")["hour"] == "11"
    assert champs("publication_hebdomadaire")["day_of_week"] == "mon"
    assert champs("publication_hebdomadaire")["hour"] == "13"
    assert all(str(job.trigger.timezone) == "UTC" for job in jobs.values())
    assert all(job.max_instances == 1 for job in jobs.values())


def test_une_exception_dans_un_job_ne_remonte_pas(caplog):
    def casse():
        raise RuntimeError("panne simulée")

    with caplog.at_level("INFO", logger="afrotech.scheduler"):
        scheduler._executer("job_test", casse)

    assert "échec" in caplog.text
    assert "panne simulée" in caplog.text


def test_sauvegarde_cree_une_copie_datee_et_purge_au_dela_de_7_jours(monkeypatch, tmp_path):
    base = tmp_path / "data" / "afrotech.db"
    base.parent.mkdir()
    monkeypatch.setattr(database, "DB_PATH", str(base))
    database.creer_base()

    backups = base.parent / "backups"
    backups.mkdir()
    for jour in range(1, 11):
        (backups / f"afrotech-202601{jour:02d}.db").write_bytes(b"vieux")

    scheduler._sauvegarde_base()

    restants = sorted(p.name for p in backups.glob("afrotech-*.db"))
    assert len(restants) == scheduler.JOURS_BACKUP_CONSERVES
    assert restants[0] != "afrotech-20260101.db", "les plus anciennes sauvegardes sont purgées"
    assert any(not n.startswith("afrotech-202601") for n in restants), "la sauvegarde du jour existe"


def test_sauvegarde_ignoree_si_la_base_n_existe_pas(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "absente.db"))

    scheduler._sauvegarde_base()

    assert not (tmp_path / "backups").exists()


def test_db_path_vide_retombe_sur_la_valeur_par_defaut(monkeypatch):
    import importlib

    monkeypatch.setenv("DB_PATH", "")
    try:
        assert importlib.reload(database).DB_PATH == "afrotech.db"
    finally:
        monkeypatch.undo()
        importlib.reload(database)


def test_page_validation_exige_le_mot_de_passe_quand_il_est_defini(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "v.db"))
    monkeypatch.setenv("VALIDATION_PASSWORD", "secret")

    at = AppTest.from_file(str(RACINE / "validation" / "review_ui.py"), default_timeout=30).run()

    assert not at.exception
    assert len(at.text_input) == 1, "seul le champ mot de passe est affiché"
    assert not at.button, "aucune action de validation avant authentification"

    at.text_input[0].set_value("mauvais").run()
    assert any("incorrect" in e.value for e in at.error)
    assert not at.button

    at.text_input[0].set_value("secret").run()
    assert not at.exception
    assert not at.text_input, "mot de passe accepté : l'écran de saisie disparaît"


def test_page_validation_sans_mot_de_passe_reste_ouverte_en_local(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "v.db"))
    monkeypatch.delenv("VALIDATION_PASSWORD", raising=False)

    at = AppTest.from_file(str(RACINE / "validation" / "review_ui.py"), default_timeout=30).run()

    assert not at.exception
    assert not at.text_input


def test_app_multipage_demarre_sur_une_base_vide(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "neuve.db"))

    at = AppTest.from_file(str(RACINE / "streamlit_app.py"), default_timeout=60).run()

    assert not at.exception, "un volume vierge ne doit pas faire planter la page par défaut"
    assert os.path.exists(tmp_path / "neuve.db")

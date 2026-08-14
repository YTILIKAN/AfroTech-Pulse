import sqlite3
from pathlib import Path

from streamlit.testing.v1 import AppTest

import database

REVIEW_UI_PATH = str(Path(__file__).resolve().parent.parent / "validation" / "review_ui.py")

CONTENU_GENERE = (
    "## Édito\n"
    "Une semaine marquée par la fintech nigériane et l'IA agricole kényane.\n\n"
    "## Cette semaine\n"
    "### 1. Lagos startup raises funding\n"
    "Une startup nigériane basée à Lagos lève des fonds pour accélérer son expansion en Afrique.\n"
    "Lien : https://exemple.com/tp-1\n\n"
    "## Conclusion\n"
    "Rendez-vous la semaine prochaine pour une nouvelle édition."
)

CONTENU_CORRIGE = CONTENU_GENERE.replace("Rendez-vous", "À très vite")


def test_parcours_complet_generation_affichage_modification_validation(monkeypatch, tmp_path):
    test_db = tmp_path / "afrotech_review_ui_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()
    newsletter_id = database.sauvegarder_newsletter(CONTENU_GENERE, nb_articles=1)

    at = AppTest.from_file(REVIEW_UI_PATH)
    at.run()
    assert not at.exception, "l'UI ne doit pas lever d'exception à l'affichage"
    assert at.text_area[0].value == CONTENU_GENERE, \
        "l'UI doit afficher le contenu de la newsletter en statut brouillon"

    at.text_input[0].set_value("Steve").run()
    at.text_area[0].set_value(CONTENU_CORRIGE).run()
    assert [b.label for b in at.button] == ["Modifier", "Valider", "Rejeter"]
    at.button[1].click().run()
    assert not at.exception, "valider une newsletter en_revue ne doit pas lever d'exception"

    conn = sqlite3.connect(str(test_db))
    contenu_en_base, statut_en_base = conn.execute(
        "SELECT contenu, statut FROM newsletters WHERE id = ?", (newsletter_id,)
    ).fetchone()
    historique = conn.execute(
        "SELECT ancien_statut, nouveau_statut, auteur FROM newsletters_historique "
        "WHERE newsletter_id = ? ORDER BY horodatage",
        (newsletter_id,),
    ).fetchall()
    conn.close()

    assert contenu_en_base == CONTENU_CORRIGE, \
        "la modification faite dans l'UI doit être persistée en base"
    assert statut_en_base == "validé", "le statut final doit être 'validé'"
    assert historique == [
        ("brouillon", "en_revue", "Steve"),
        ("en_revue", "validé", "Steve"),
    ], "l'historique doit tracer les deux transitions avec l'identité du validateur"


def test_parcours_rejet_empeche_publication_ulterieure(monkeypatch, tmp_path):
    test_db = tmp_path / "afrotech_review_ui_rejet_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()
    newsletter_id = database.sauvegarder_newsletter(CONTENU_GENERE, nb_articles=1)

    at = AppTest.from_file(REVIEW_UI_PATH)
    at.run()
    at.text_input[0].set_value("Bob").run()
    at.button[2].click().run()  # bouton Rejeter
    assert not at.exception, "rejeter une newsletter en_revue ne doit pas lever d'exception"

    conn = sqlite3.connect(str(test_db))
    statut_en_base = conn.execute(
        "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
    ).fetchone()[0]
    conn.close()
    assert statut_en_base == "rejeté", "le statut final doit être 'rejeté'"

    try:
        database.changer_statut_newsletter(newsletter_id, "publié", "Bob")
        assert False, "une newsletter rejetée ne doit jamais pouvoir être publiée"
    except ValueError:
        pass

    conn = sqlite3.connect(str(test_db))
    statut_apres_tentative = conn.execute(
        "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
    ).fetchone()[0]
    conn.close()
    assert statut_apres_tentative == "rejeté", \
        "le statut ne doit pas bouger après une tentative de publication refusée"

    at2 = AppTest.from_file(REVIEW_UI_PATH)
    at2.run()
    assert not at2.exception
    assert "Aucune newsletter en attente de validation" in at2.info[0].value, \
        "une newsletter rejetée ne doit plus apparaître comme à valider dans l'UI"

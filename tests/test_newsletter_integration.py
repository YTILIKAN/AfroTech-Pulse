import sqlite3
from types import SimpleNamespace

import database
import newsletter.writer as writer_module
from newsletter.writer import generer_newsletter

FAKE_SELECTION = [
    {
        "titre": "Lagos startup raises funding",
        "url": "https://exemple.com/tp-1",
        "resume": "Une startup nigériane basée à Lagos lève des fonds pour accélérer son expansion en Afrique.",
    },
    {
        "titre": "Kenya launches national AI strategy",
        "url": "https://exemple.com/ke-1",
        "resume": "Le Kenya lance une stratégie nationale pour l'intelligence artificielle dans l'agriculture.",
    },
]

FAKE_NEWSLETTER = (
    "## Édito\n"
    "Une semaine marquée par la fintech nigériane et l'IA agricole kényane.\n\n"
    "## Cette semaine\n"
    "### 1. Lagos startup raises funding\n"
    "Une startup nigériane basée à Lagos lève des fonds pour accélérer son expansion en Afrique.\n"
    "Lien : https://exemple.com/tp-1\n\n"
    "### 2. Kenya launches national AI strategy\n"
    "Le Kenya lance une stratégie nationale pour l'intelligence artificielle dans l'agriculture.\n"
    "Lien : https://exemple.com/ke-1\n\n"
    "## Conclusion\n"
    "Rendez-vous la semaine prochaine pour une nouvelle édition."
)


def fake_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeClient:
    def __init__(self, complete_fn):
        self.chat = SimpleNamespace(complete=complete_fn)


def test_generer_newsletter_puis_sauvegarde_en_base_avec_statut_brouillon(monkeypatch, tmp_path):
    test_db = tmp_path / "afrotech_newsletter_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(
        writer_module, "get_client", lambda: FakeClient(lambda **kw: fake_response(FAKE_NEWSLETTER))
    )

    database.creer_base()

    contenu = generer_newsletter(FAKE_SELECTION)
    assert contenu is not None, "la génération ne doit pas échouer avec une sélection valide"

    newsletter_id = database.sauvegarder_newsletter(contenu, nb_articles=len(FAKE_SELECTION))

    conn = sqlite3.connect(str(test_db))
    row = conn.execute(
        "SELECT contenu, nb_articles, statut FROM newsletters WHERE id = ?", (newsletter_id,)
    ).fetchone()
    conn.close()

    assert row is not None, "la newsletter générée doit être présente en base"
    contenu_en_base, nb_articles_en_base, statut_en_base = row
    assert contenu_en_base == contenu
    assert nb_articles_en_base == len(FAKE_SELECTION)
    assert statut_en_base == "brouillon", "une newsletter nouvellement générée doit être en brouillon"

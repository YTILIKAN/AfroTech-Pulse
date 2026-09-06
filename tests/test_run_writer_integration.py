from types import SimpleNamespace

import database
import newsletter.run_writer as run_writer_module
import newsletter.writer as writer_module
import orchestrator
import pipeline.run_summarize as run_summarize_module

FAKE_SOURCES = [
    {"id": "techpoint-africa", "name": "TechPoint Africa", "category": "startup",
     "type": "rss", "active": True, "url": "http://fake-techpoint"},
]

CONTENU_PERTINENT = (
    "A new startup based in Lagos, Nigeria is changing the way africans access "
    "financial services. This african tech company is a leading tech hub."
)

FAKE_ARTICLES = {
    "techpoint-africa": [
        {
            "source_id": "techpoint-africa",
            "title": f"How Lagos startup {i} is disrupting fintech in Africa",
            "url": f"https://exemple.com/article-{i}",
            "published": "2026-08-10T00:00:00",
            "content": CONTENU_PERTINENT,
        }
        for i in range(6)
    ],
}


def fake_scrape_rss(source):
    return FAKE_ARTICLES[source["id"]]


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def test_run_writer_chaine_selection_et_redaction_jusquau_brouillon(monkeypatch, tmp_path):
    """Bout-en-bout S6 -> S7 -> sauvegarde : run_writer.run() doit produire une
    newsletter en base, en statut 'brouillon', avec le bon nombre d'articles."""
    test_db = tmp_path / "run_writer_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss)
    monkeypatch.setattr(run_summarize_module, "summarize_article",
                         lambda titre, contenu: f"Résumé automatique de : {titre}")

    orchestrator.run()
    run_summarize_module.run()

    def fake_post(url, json):
        newsletter = (
            "## Édito\nTest.\n\n## Cette semaine\n"
            "### 1. Article\nRésumé.\nLien : https://exemple.com\n\n"
            "## Conclusion\nTest."
        )
        json_data = {"candidates": [{"content": {"parts": [{"text": newsletter}]}}]}
        return SimpleNamespace(status_code=200, text="", json=lambda: json_data)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(fake_post))

    newsletter_id = run_writer_module.run()

    assert newsletter_id is not None, "run_writer.run() doit retourner l'id de la newsletter créée"

    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter is not None, "la newsletter doit être persistée en base"
    assert newsletter[3] == "brouillon", "une newsletter fraîchement rédigée doit être en statut 'brouillon'"
    assert newsletter[2] > 0, "nb_articles doit refléter le nombre d'articles réellement sélectionnés"

    import sqlite3
    conn = sqlite3.connect(str(test_db))
    selectionnes = conn.execute("SELECT COUNT(*) FROM articles_raw WHERE selectionne = 1").fetchone()[0]
    conn.close()
    assert selectionnes == newsletter[2], \
        "le nombre d'articles marqués 'selectionne' en base doit correspondre à nb_articles"


def test_run_writer_sans_articles_selectionnables_ne_cree_rien(monkeypatch, tmp_path):
    test_db = tmp_path / "run_writer_vide_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()

    resultat = run_writer_module.run()

    assert resultat is None, "sans article sélectionnable, aucune newsletter ne doit être créée"

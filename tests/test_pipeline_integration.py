import sqlite3
from types import SimpleNamespace

import database
import newsletter.writer as writer_module
import orchestrator
import pipeline.editor as editor_module
import pipeline.run_editor as run_editor_module
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


def test_chaine_complete_scrape_puis_resume_puis_selection(monkeypatch, tmp_path):
    """Reproduit l'ordre exact de daily_scrape.yml (orchestrator -> run_summarize)
    puis weekly_editor.yml (run_editor), pour garantir que la sélection S6 trouve
    bien des candidats une fois l'étape résumé branchée. Avant le fix de
    daily_scrape.yml, l'étape run_summarize n'existait dans aucun workflow et
    ce test aurait échoué (0 article sélectionnable, resume toujours NULL)."""
    test_db = tmp_path / "pipeline_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss)
    monkeypatch.setattr(run_summarize_module, "summarize_article",
                         lambda titre, contenu: f"Résumé automatique de : {titre}")

    # Étapes 1-3 (daily_scrape.yml) : collecte + score + dédup
    orchestrator.run()

    conn = sqlite3.connect(str(test_db))
    avant_resume = conn.execute(
        "SELECT COUNT(*) FROM articles_raw WHERE resume IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert avant_resume == 0, "aucun résumé ne doit exister avant l'étape de résumé"

    # Étape 4 (daily_scrape.yml, étape qui manquait avant le fix) : résumé LLM
    run_summarize_module.run()

    # Étape 5 (weekly_editor.yml) : sélection éditoriale hebdomadaire
    run_editor_module.run()

    conn = sqlite3.connect(str(test_db))
    selectionnes = conn.execute(
        "SELECT COUNT(*) FROM articles_raw WHERE selectionne = 1"
    ).fetchone()[0]
    conn.close()

    assert selectionnes > 0, (
        "sans l'étape résumé avant la sélection, selectionner_articles_semaine() "
        "ne trouve aucun candidat (resume IS NOT NULL) — ce test aurait échoué "
        "avant le fix de daily_scrape.yml"
    )


def test_selection_ne_trouve_rien_si_le_resume_est_saute(monkeypatch, tmp_path):
    """Contre-épreuve : reproduit le bug tel qu'il existait avant le fix
    (résumé jamais exécuté) pour prouver que le test ci-dessus est bien
    discriminant et ne passerait pas par hasard."""
    test_db = tmp_path / "pipeline_bug_repro_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss)

    orchestrator.run()
    # (pas d'appel à run_summarize_module.run() ici : c'est exactement le bug)
    run_editor_module.run()

    conn = sqlite3.connect(str(test_db))
    selectionnes = conn.execute(
        "SELECT COUNT(*) FROM articles_raw WHERE selectionne = 1"
    ).fetchone()[0]
    conn.close()

    assert selectionnes == 0, "sans résumé, la sélection doit être vide (c'était le bug)"


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def test_selection_s6_alimente_generer_newsletter_avec_un_resume_reel(monkeypatch, tmp_path):
    """Bout-en-bout S6 -> S7 : les articles retournés par selectionner_articles_semaine()
    (S6) doivent porter un resume exploitable par generer_newsletter() (S7). Avant le fix
    de articles_selectionnables()/selectionner_articles_semaine() (qui ne sélectionnaient
    ni ne reportaient la colonne resume), chaque article arrivait sans resume ni contenu,
    et le LLM devait inventer le texte à partir du seul titre, ce qui viole le garde-fou
    anti-invention de generer_newsletter()."""
    test_db = tmp_path / "pipeline_s6_s7_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss)
    monkeypatch.setattr(run_summarize_module, "summarize_article",
                         lambda titre, contenu: f"Résumé automatique de : {titre}")

    orchestrator.run()
    run_summarize_module.run()

    selection = editor_module.selectionner_articles_semaine()

    assert len(selection) > 0, "la sélection doit trouver des candidats pour que ce test soit significatif"
    assert all(article.get("resume") for article in selection), (
        "chaque article sélectionné par S6 doit porter un resume non vide, sinon S7 reçoit "
        "un article sans contenu et le LLM invente le texte à partir du titre seul"
    )

    payloads_captures = {}

    def fake_post(url, json):
        payloads_captures["payload"] = json
        newsletter = "## Édito\nTest.\n\n## Cette semaine\n" + "\n".join(
            f"### {i}. {a['titre']}\n{a['resume']}\nLien : {a['url']}"
            for i, a in enumerate(selection, start=1)
        ) + "\n\n## Conclusion\nTest."
        json_data = {"candidates": [{"content": {"parts": [{"text": newsletter}]}}]}
        return SimpleNamespace(status_code=200, text="", json=lambda: json_data)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(fake_post))

    contenu_newsletter = writer_module.generer_newsletter(selection)

    assert contenu_newsletter is not None
    prompt_utilisateur = payloads_captures["payload"]["contents"][0]["parts"][0]["text"]
    for article in selection:
        assert article["resume"] in prompt_utilisateur, (
            f"le resume de l'article '{article['titre']}' doit apparaître dans le prompt "
            "envoyé au LLM, sinon la newsletter est rédigée sans ce contenu"
        )

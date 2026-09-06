"""Cycle complet S12 : collecte -> résumé -> sélection/rédaction -> validation humaine
(simulée) -> publication automatique. Prouve que le seul geste manuel restant est le
passage brouillon -> validé (le « clic de validation » du ticket)."""

import database
import newsletter.run_writer as run_writer_module
import orchestrator
import publisher.publish as publish_module
import publisher.run_publish as run_publish_module
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


def test_cycle_complet_jusqua_publication_automatique(monkeypatch, tmp_path):
    test_db = tmp_path / "full_cycle_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", lambda source: FAKE_ARTICLES[source["id"]])
    monkeypatch.setattr(run_summarize_module, "summarize_article",
                        lambda titre, contenu: f"Résumé automatique de : {titre}")
    monkeypatch.setattr(
        run_writer_module, "generer_newsletter",
        lambda selection: "## Édito\nTest.\n\n## Cette semaine\n"
        + "\n".join(f"### {i}. {a['titre']}\n{a['resume']}\nLien : {a['url']}"
                    for i, a in enumerate(selection, start=1))
        + "\n\n## Conclusion\nTest.",
    )

    # --- Étapes automatiques : daily_scrape.yml puis weekly_editor.yml ---
    orchestrator.run()
    run_summarize_module.run()
    newsletter_id = run_writer_module.run()
    assert newsletter_id is not None
    assert database.newsletter_par_id(newsletter_id)[3] == "brouillon"

    # --- Avant validation : la publication automatique ne doit RIEN faire ---
    def envoi_interdit(contenu):
        raise AssertionError("aucune publication tant que la newsletter n'est pas validée")

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", envoi_interdit)
    assert run_publish_module.run() == 0
    assert database.newsletter_par_id(newsletter_id)[3] == "brouillon"

    # --- Unique geste manuel : le clic de validation (brouillon -> en_revue -> validé) ---
    database.changer_statut_newsletter(newsletter_id, "en_revue", "Steve")
    database.changer_statut_newsletter(newsletter_id, "validé", "Steve")

    # --- Étape automatique : monday_publish.yml ---
    envois = []
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram",
                        lambda contenu: envois.append(contenu) or True)

    assert run_publish_module.run() == 0
    assert len(envois) == 1, "la newsletter validée doit être envoyée une fois sur Telegram"

    newsletter_apres = database.newsletter_par_id(newsletter_id)
    assert newsletter_apres[3] == "publié"
    publications = {c: s for c, s, *_ in database.statuts_publication(newsletter_id)}
    assert publications == {"telegram": "publié"}

    # --- Idempotence : un second run ne republie pas ---
    assert run_publish_module.run() == 0
    assert len(envois) == 1, "une newsletter déjà publiée ne doit pas repartir"

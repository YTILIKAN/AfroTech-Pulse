import pipeline.run_summarize as run_summarize_module


def test_articles_resumes_sont_sauvegardes(monkeypatch):
    articles = [
        ("https://exemple.com/a1", "Titre 1", "Contenu 1"),
        ("https://exemple.com/a2", "Titre 2", "Contenu 2"),
    ]
    appels_sauvegarde = []

    monkeypatch.setattr(run_summarize_module.database, "creer_base", lambda: None)
    monkeypatch.setattr(run_summarize_module.database, "articles_a_resumer",
                         lambda seuil, limit: articles)
    monkeypatch.setattr(run_summarize_module.database, "sauvegarder_resume",
                         lambda url, resume: appels_sauvegarde.append((url, resume)))
    monkeypatch.setattr(run_summarize_module, "summarize_article",
                         lambda titre, contenu: f"Résumé de {titre}")

    run_summarize_module.run()

    assert appels_sauvegarde == [
        ("https://exemple.com/a1", "Résumé de Titre 1"),
        ("https://exemple.com/a2", "Résumé de Titre 2"),
    ]


def test_echec_de_resume_n_appelle_pas_sauvegarder_resume(monkeypatch):
    articles = [("https://exemple.com/a1", "Titre 1", "Contenu 1")]

    def echoue_si_appelee(url, resume):
        raise AssertionError("sauvegarder_resume ne doit pas être appelé si le résumé a échoué")

    monkeypatch.setattr(run_summarize_module.database, "creer_base", lambda: None)
    monkeypatch.setattr(run_summarize_module.database, "articles_a_resumer",
                         lambda seuil, limit: articles)
    monkeypatch.setattr(run_summarize_module, "summarize_article", lambda titre, contenu: None)
    monkeypatch.setattr(run_summarize_module.database, "sauvegarder_resume", echoue_si_appelee)

    run_summarize_module.run()  # ne doit pas lever d'exception


def test_limit_est_transmis_a_articles_a_resumer(monkeypatch):
    limites_recues = []

    def fake_articles_a_resumer(seuil, limit):
        limites_recues.append(limit)
        return []

    monkeypatch.setattr(run_summarize_module.database, "creer_base", lambda: None)
    monkeypatch.setattr(run_summarize_module.database, "articles_a_resumer", fake_articles_a_resumer)

    run_summarize_module.run(limit=5)

    assert limites_recues == [5]


def test_aucun_article_a_resumer_ne_fait_aucun_appel(monkeypatch):
    def echoue_si_appelee(*args, **kwargs):
        raise AssertionError("summarize_article ne doit pas être appelé s'il n'y a aucun article")

    monkeypatch.setattr(run_summarize_module.database, "creer_base", lambda: None)
    monkeypatch.setattr(run_summarize_module.database, "articles_a_resumer", lambda seuil, limit: [])
    monkeypatch.setattr(run_summarize_module, "summarize_article", echoue_si_appelee)

    run_summarize_module.run()

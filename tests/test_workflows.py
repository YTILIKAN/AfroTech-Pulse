from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"


def test_daily_scrape_appelle_le_resume():
    contenu = (WORKFLOWS_DIR / "daily_scrape.yml").read_text(encoding="utf-8")
    assert "run_summarize" in contenu, (
        "daily_scrape.yml doit exécuter pipeline/run_summarize.py, sinon la colonne "
        "resume n'est jamais remplie en production et selectionner_articles_semaine() "
        "(pipeline/editor.py) ne trouve jamais aucun candidat (bug déjà rencontré)."
    )


def test_daily_scrape_utilise_le_secret_gemini():
    contenu = (WORKFLOWS_DIR / "daily_scrape.yml").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in contenu, (
        "pipeline/summarize.py lit GEMINI_API_KEY (plus MISTRAL_API_KEY) depuis la migration "
        "vers Gemini — sans ce secret renommé côté GitHub Actions, le résumé plante à chaque run."
    )
    assert "MISTRAL_API_KEY" not in contenu


def test_weekly_editor_appelle_la_selection_et_la_redaction():
    contenu = (WORKFLOWS_DIR / "weekly_editor.yml").read_text(encoding="utf-8")
    assert "run_writer" in contenu, (
        "weekly_editor.yml doit exécuter newsletter/run_writer.py (sélection + rédaction), "
        "pas seulement pipeline/run_editor.py (sélection seule) — sinon aucun brouillon de "
        "newsletter n'est généré automatiquement le dimanche soir."
    )
    assert "GEMINI_API_KEY" in contenu, (
        "run_writer.py appelle generer_newsletter() qui a besoin de GEMINI_API_KEY."
    )

from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"


def test_daily_scrape_appelle_le_resume():
    contenu = (WORKFLOWS_DIR / "daily_scrape.yml").read_text(encoding="utf-8")
    assert "run_summarize" in contenu, (
        "daily_scrape.yml doit exécuter pipeline/run_summarize.py, sinon la colonne "
        "resume n'est jamais remplie en production et selectionner_articles_semaine() "
        "(pipeline/editor.py) ne trouve jamais aucun candidat (bug déjà rencontré)."
    )


def test_weekly_editor_appelle_la_selection():
    contenu = (WORKFLOWS_DIR / "weekly_editor.yml").read_text(encoding="utf-8")
    assert "run_editor" in contenu

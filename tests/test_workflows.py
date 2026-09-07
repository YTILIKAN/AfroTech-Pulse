import re
from pathlib import Path

RACINE = Path(__file__).parent.parent
WORKFLOWS_DIR = RACINE / ".github" / "workflows"


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


def test_monday_publish_publie_via_le_point_dentree_avec_code_de_sortie():
    contenu = (WORKFLOWS_DIR / "monday_publish.yml").read_text(encoding="utf-8")
    assert 'cron: "0 13 * * 1"' in contenu, (
        "monday_publish.yml doit tourner le lundi à 13:00 UTC (9h Montréal l'été)."
    )
    assert "publisher.run_publish" in contenu, (
        "monday_publish.yml doit appeler publisher/run_publish.py (et pas publish.py "
        "directement) : c'est run_publish qui traduit un échec en exit code non nul, "
        "sinon un échec Telegram passerait vert sur GitHub Actions."
    )
    for secret in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID"):
        assert secret in contenu, f"monday_publish.yml a besoin du secret {secret}."
    assert "afrotech.db" in contenu, (
        "monday_publish.yml doit committer afrotech.db : le passage validé -> publié et "
        "les lignes newsletters_publications doivent être persistés dans le repo."
    )


def test_monday_reminder_rappelle_la_validation():
    contenu = (WORKFLOWS_DIR / "monday_reminder.yml").read_text(encoding="utf-8")
    assert 'cron: "0 11 * * 1"' in contenu, (
        "monday_reminder.yml doit tourner le lundi à 11:00 UTC, avant monday_publish."
    )
    assert "-m notifier" in contenu, "monday_reminder.yml doit exécuter le module notifier."
    assert "TELEGRAM_ADMIN_CHAT_ID" in contenu, (
        "le rappel s'envoie au groupe privé de l'équipe (TELEGRAM_ADMIN_CHAT_ID), "
        "pas au canal public."
    )


def test_tous_les_crons_des_workflows_sont_documentes_dans_le_readme():
    readme = (RACINE / "README.md").read_text(encoding="utf-8")
    for fichier in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for cron in re.findall(r'cron:\s*"([^"]+)"', fichier.read_text(encoding="utf-8")):
            assert cron in readme, (
                f"le cron {cron!r} de {fichier.name} n'apparaît pas dans le README — "
                "les horaires réels doivent correspondre à ceux documentés."
            )

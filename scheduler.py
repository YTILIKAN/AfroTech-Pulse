"""Planificateur des tâches automatiques du pipeline.

Remplace les 4 workflows GitHub Actions (`daily_scrape`, `weekly_editor`,
`monday_reminder`, `monday_publish`) quand l'application tourne en service unique
sur un hébergement type Railway. Démarré en tâche de fond par ``streamlit_app.py``.

Les horaires sont **identiques** aux crons GitHub Actions, en UTC :

| Tâche              | Cron GitHub      | Horaire UTC          |
|-------------------|------------------|----------------------|
| scrape + résumé    | `0 6 * * *`      | tous les jours 06:00 |
| sélection + rédaction | `0 20 * * 0`  | dimanche 20:00       |
| rappel validation  | `0 11 * * 1`     | lundi 11:00          |
| publication        | `0 13 * * 1`     | lundi 13:00          |
| sauvegarde base    | (nouveau)        | tous les jours 05:00 |

Mettre ``DISABLE_SCHEDULER=1`` pour lancer l'app sans le planificateur
(développement local, ou un second réplica qui ne doit pas dupliquer les jobs).
"""

import glob
import logging
import os
import shutil
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

JOURS_BACKUP_CONSERVES = 7


def _configurer_logs():
    """Rend visibles, sur la sortie standard, les logs du planificateur et d'APScheduler.

    Indispensable en hébergement : c'est la seule fenêtre sur l'exécution des jobs.
    """
    formatteur = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatteur)
    for nom in ("afrotech.scheduler", "apscheduler"):
        lg = logging.getLogger(nom)
        lg.setLevel(logging.INFO)
        if not lg.handlers:
            lg.addHandler(handler)
        lg.propagate = False


_configurer_logs()
logger = logging.getLogger("afrotech.scheduler")


def _scrape_quotidien():
    import orchestrator
    from pipeline import run_summarize

    orchestrator.run()
    run_summarize.run()


def _redaction_hebdomadaire():
    from newsletter import run_writer

    run_writer.run()


def _rappel_validation():
    import notifier

    notifier.main()


def _publication_hebdomadaire():
    from publisher import run_publish

    run_publish.run()


def _sauvegarde_base():
    """Copie datée de la base dans ``<dossier base>/backups/``, purge au-delà de 7 jours.

    Protège contre une corruption ou une mauvaise manipulation. Ne remplace pas
    une vraie sauvegarde hors-site (à ajouter si le projet grandit).
    """
    import database

    if not os.path.exists(database.DB_PATH):
        logger.warning("Sauvegarde ignorée : %s introuvable", database.DB_PATH)
        return

    dossier = os.path.join(os.path.dirname(database.DB_PATH) or ".", "backups")
    os.makedirs(dossier, exist_ok=True)
    cible = os.path.join(dossier, f"afrotech-{datetime.now(timezone.utc):%Y%m%d}.db")
    shutil.copy2(database.DB_PATH, cible)

    anciens = sorted(glob.glob(os.path.join(dossier, "afrotech-*.db")))
    for vieux in anciens[:-JOURS_BACKUP_CONSERVES]:
        os.remove(vieux)
    logger.info("Sauvegarde base -> %s", cible)


def _executer(nom, fonction):
    """Enveloppe commune : trace le début/fin et empêche une exception de tuer le planificateur."""
    logger.info("Tâche %s — démarrage", nom)
    try:
        fonction()
        logger.info("Tâche %s — terminée", nom)
    except Exception:
        logger.exception("Tâche %s — échec", nom)


# (id, fonction, kwargs du CronTrigger). Le trigger est construit dans
# construire_planificateur() pour que la timezone UTC soit bien appliquée.
_JOBS = [
    ("scrape_quotidien", _scrape_quotidien, dict(hour=6, minute=0)),
    ("redaction_hebdomadaire", _redaction_hebdomadaire,
     dict(day_of_week="sun", hour=20, minute=0)),
    ("rappel_validation", _rappel_validation,
     dict(day_of_week="mon", hour=11, minute=0)),
    ("publication_hebdomadaire", _publication_hebdomadaire,
     dict(day_of_week="mon", hour=13, minute=0)),
    ("sauvegarde_base", _sauvegarde_base, dict(hour=5, minute=0)),
]


def construire_planificateur():
    """Retourne un ``BackgroundScheduler`` configuré (jobs planifiés en UTC), non démarré."""
    planificateur = BackgroundScheduler(timezone="UTC")
    options = dict(coalesce=True, misfire_grace_time=3600, max_instances=1)

    for nom, fonction, cron_kwargs in _JOBS:
        trigger = CronTrigger(timezone="UTC", **cron_kwargs)
        planificateur.add_job(
            _executer, trigger, args=(nom, fonction), id=nom, **options
        )
        logger.info("Job planifié : %s (%s)", nom, trigger)

    return planificateur

"""Lanceur de production — planificateur + application web dans un seul process racine.

C'est la commande de démarrage de l'hébergement (Railway) :

    python serve.py

Séquence :
1. démarre ``scheduler`` (APScheduler en tâche de fond) — les 4 crons GitHub Actions
   deviennent des jobs internes, exécutés que quelqu'un consulte l'app ou non ;
2. lance Streamlit (``streamlit_app.py``) en sous-process, sur ``$PORT`` ;
3. si Streamlit s'arrête, on arrête proprement le planificateur et on sort avec
   son code retour (Railway redémarrera).

``DISABLE_SCHEDULER=1`` lance l'app seule (utile pour un éventuel second réplica).
"""

import os
import subprocess
import sys


def main() -> int:
    # Premier démarrage sur un volume vide : sans tables, le dashboard (page par défaut)
    # planterait jusqu'au premier scrape de 06:00 UTC.
    import database

    dossier_base = os.path.dirname(database.DB_PATH)
    if dossier_base:
        os.makedirs(dossier_base, exist_ok=True)
    database.creer_base()

    planificateur = None
    if os.getenv("DISABLE_SCHEDULER") != "1":
        from scheduler import construire_planificateur

        planificateur = construire_planificateur()
        planificateur.start()

    port = os.getenv("PORT", "8501")
    commande = [
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
    ]

    try:
        return subprocess.run(commande).returncode
    finally:
        if planificateur is not None:
            planificateur.shutdown(wait=False)


if __name__ == "__main__":
    sys.exit(main())

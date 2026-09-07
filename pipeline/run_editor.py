# pipeline/run_editor.py — sélectionne et marque en base les articles de la newsletter de la semaine

import argparse

import database
from pipeline.editor import SELECTION_MIN, selectionner_articles_semaine


def run(seuil=None):
    database.creer_base()

    selection = selectionner_articles_semaine(seuil=seuil)

    print("AfroTech Pulse — Sélection éditoriale hebdomadaire")
    print(f"{len(selection)} article(s) sélectionné(s)\n")

    if len(selection) < SELECTION_MIN:
        print(f"[ATTENTION] moins de {SELECTION_MIN} articles disponibles cette semaine "
              f"({len(selection)} trouvés) — vérifier le pipeline de collecte/résumé.\n")

    for article in selection:
        database.marquer_selectionne(article["url"], article["score_editorial"])
        pays = article["pays"] or "non identifié"
        print(f"  [{article['score_editorial']:5.1f}] ({pays}) {article['titre']}")

    print(f"\nBase : {database.DB_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="Sélectionne les 5-7 meilleurs articles de la semaine pour la newsletter."
    )
    parser.add_argument(
        "--seuil", type=int, default=None,
        help="Seuil de pertinence minimum (défaut : database.SEUIL_PERTINENCE).",
    )
    args = parser.parse_args()
    run(seuil=args.seuil)


if __name__ == "__main__":
    main()

# newsletter/run_writer.py — chaîne sélection éditoriale (S6) et rédaction (S7), sauvegarde en brouillon

import argparse

import database
from newsletter.writer import generer_newsletter
from pipeline.editor import SELECTION_MIN, selectionner_articles_semaine


def run(seuil=None):
    """Enchaîne sélection éditoriale et rédaction, et sauvegarde un brouillon.

    Retourne l'identifiant de la newsletter créée, ou None si aucun article n'est
    sélectionnable ou si la rédaction échoue. Les articles ne sont marqués `selectionne`
    qu'après une génération réussie : un échec du LLM les laisse disponibles pour la
    tentative suivante au lieu de les consommer.

    Point d'entrée de `weekly_editor.yml`.
    """
    database.creer_base()

    selection = selectionner_articles_semaine(seuil=seuil)

    print("AfroTech Pulse — Rédaction hebdomadaire")
    print(f"{len(selection)} article(s) sélectionné(s)\n")

    if len(selection) < SELECTION_MIN:
        print(f"[ATTENTION] moins de {SELECTION_MIN} articles disponibles cette semaine "
              f"({len(selection)} trouvés) — vérifier le pipeline de collecte/résumé.\n")

    if not selection:
        print("[ÉCHEC] aucun article sélectionnable, pas de newsletter générée.")
        return None

    contenu = generer_newsletter(selection)
    if contenu is None:
        print("[ÉCHEC] la rédaction de la newsletter a échoué — aucun article marqué "
              "'sélectionné', ils restent disponibles pour une prochaine tentative.")
        return None

    for article in selection:
        database.marquer_selectionne(article["url"], article["score_editorial"])

    newsletter_id = database.sauvegarder_newsletter(contenu, nb_articles=len(selection))
    print(f"\nNewsletter #{newsletter_id} créée en statut 'brouillon' ({len(selection)} articles).")
    print(f"Base : {database.DB_PATH}")
    return newsletter_id


def main():
    """Point d'entrée en ligne de commande : `python -m newsletter.run_writer [--seuil N]`."""
    parser = argparse.ArgumentParser(
        description="Sélectionne les meilleurs articles de la semaine et rédige la newsletter en brouillon."
    )
    parser.add_argument(
        "--seuil", type=int, default=None,
        help="Seuil de pertinence minimum (défaut : database.SEUIL_PERTINENCE).",
    )
    args = parser.parse_args()
    run(seuil=args.seuil)


if __name__ == "__main__":
    main()

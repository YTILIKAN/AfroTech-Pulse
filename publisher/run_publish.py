# publisher/run_publish.py — Point d'entrée de la publication automatique du lundi.
#
# publish_newsletter() retourne un dict et ne lève jamais d'exception (filet volontaire) :
# sans cette enveloppe, un échec Telegram passerait « vert » sur GitHub Actions. Ici on
# traduit le résultat en code de sortie — un échec rend le run ROUGE et alerte l'équipe.

import sys

import database
import notifier
from publisher.publish import publish_newsletter


def run(auteur="github-actions") -> int:
    database.creer_base()
    resultats = publish_newsletter(auteur=auteur)

    if not resultats:
        print("[INFO] Aucune newsletter validée en attente — rien à publier.")
        return 0

    echecs = [canal for canal, succes in resultats.items() if not succes]
    if echecs:
        print(
            f"[ÉCHEC] Publication automatique incomplète — canaux en échec : {echecs}. "
            "Statut de la newsletter inchangé (reste 'validé')."
        )
        message = (
            "⚠️ <b>Publication automatique en échec</b>\n"
            f"Canaux en échec : {', '.join(echecs)}\n"
            "La newsletter reste au statut 'validé'. Republier manuellement via "
            "<code>streamlit run validation/review_ui.py</code>."
        )
        try:
            notifier.envoyer_notification_equipe(message)
        except RuntimeError as e:
            # L'alerte est un bonus : son échec ne doit pas masquer l'échec de publication.
            print(f"[ERREUR] Alerte équipe non envoyée : {e}")
        return 1

    print(f"[OK] Newsletter publiée automatiquement sur : {', '.join(resultats)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())

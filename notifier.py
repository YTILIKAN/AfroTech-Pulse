# notifier.py — Notifications internes vers l'équipe (groupe Telegram privé).
#
# Distinct de publisher/telegram_client.py, qui publie la newsletter sur le canal PUBLIC
# (TELEGRAM_CHANNEL_ID). Ici on écrit à l'équipe (TELEGRAM_ADMIN_CHAT_ID) : rappels de
# validation, alertes d'échec de publication automatique. Rien de ce qui passe par ce
# module n'est visible par les abonnés.

import os
import sys

import httpx
from dotenv import load_dotenv

import database

load_dotenv()

TIMEOUT = 10.0

# Comment lancer l'interface de validation humaine (affiché dans le rappel du lundi).
COMMANDE_VALIDATION = "streamlit run validation/review_ui.py"


def _get_client():
    # Pas de mise en cache du client : même raisonnement que telegram_client.get_client() —
    # un token changé dans .env sans redémarrage ne doit pas rester utilisé.
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN manquant — copie .env.example en .env et renseigne ton token."
        )
    return httpx.Client(
        base_url=f"https://api.telegram.org/bot{token}",
        timeout=TIMEOUT,
    )


def envoyer_notification_equipe(message: str) -> bool:
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_ADMIN_CHAT_ID manquant — identifiant du groupe Telegram privé de "
            "l'équipe (à ne pas confondre avec TELEGRAM_CHANNEL_ID, le canal public). "
            "Copie .env.example en .env et renseigne la valeur."
        )

    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = _get_client().post("/sendMessage", json=payload)
    except httpx.HTTPError as e:
        print(f"[ERREUR] notification équipe non envoyée (réseau) : {e}")
        return False

    if response.status_code != 200:
        print(
            f"[ERREUR] notification équipe non envoyée (HTTP {response.status_code}) : "
            f"{response.text}"
        )
        return False
    return True


def rappel_validation() -> bool:
    """Prévient l'équipe qu'une newsletter est en attente de validation humaine.

    Retourne True si un rappel a bien été envoyé, False s'il n'y avait rien à valider.
    Un échec d'envoi (secret manquant, HTTP KO) n'est jamais silencieux : RuntimeError
    pour un secret manquant, log [ERREUR] + retour False sinon."""
    database.creer_base()
    brouillon = database.derniere_newsletter_brouillon()
    if brouillon is None:
        print("[INFO] Aucune newsletter en brouillon — aucun rappel de validation envoyé.")
        return False

    newsletter_id, _contenu, nb_articles, _statut, date_generation = brouillon
    message = (
        "🔔 <b>Newsletter prête à valider</b>\n"
        f"Newsletter #{newsletter_id} — {nb_articles} article(s) — générée le "
        f"{date_generation.split('T')[0]}.\n\n"
        f"1. <code>git pull</code>\n"
        f"2. <code>{COMMANDE_VALIDATION}</code> → relire et valider\n"
        "3. <code>git add afrotech.db &amp;&amp; git commit -m \"validation newsletter\" "
        "&amp;&amp; git push</code>\n\n"
        "Sans le push, la publication automatique de ce lundi ne verra pas la validation."
    )
    if envoyer_notification_equipe(message):
        print(f"[OK] Rappel de validation envoyé pour la newsletter #{newsletter_id}.")
        return True
    return False


def main() -> int:
    database.creer_base()
    # Rien à valider -> exit 0 (cas normal). Newsletter en attente mais envoi KO -> exit 1
    # pour que le run GitHub Actions vire au rouge et que l'échec soit visible.
    if database.derniere_newsletter_brouillon() is None:
        print("[INFO] Aucune newsletter en brouillon — aucun rappel de validation envoyé.")
        return 0
    return 0 if rappel_validation() else 1


if __name__ == "__main__":
    sys.exit(main())

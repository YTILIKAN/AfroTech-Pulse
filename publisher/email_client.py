"""Client Resend — envoi de la newsletter par email aux abonnés actifs.

Canal **en évolution, désactivé** : `email` n'est pas dans
``database.CANAUX_PUBLICATION`` tant que le domaine d'envoi n'est pas vérifié
sur Resend. Le code est fonctionnel et testé.

`envoyer_email(contenu)` met tous les abonnés actifs en `bcc` (ils ne se voient
pas entre eux), avec 3 tentatives et backoff sur les 429/5xx/timeouts.
Config : ``RESEND_API_KEY``, ``RESEND_FROM_EMAIL``.
"""

import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

import database

load_dotenv()

MAX_TENTATIVES = 3

def get_client():
    # Pas de mise en cache du client : si la clé RESEND_API_KEY change dans .env pendant
    # que review_ui.py tourne en continu, un client mis en cache resterait périmé jusqu'au
    # redémarrage du process et échouerait avec un 401 qui ressemble à un bug API.
    cle = os.getenv("RESEND_API_KEY")
    if not cle:
        raise RuntimeError(
            "RESEND_API_KEY manquante — copie .env.example en .env et renseigne ta clé."
        )
    return httpx.Client(
        base_url="https://api.resend.com",
        headers={"Authorization": f"Bearer {cle}"},
        timeout=10.0,
    )


def envoyer_email(contenu: str) -> bool:
    """Envoie `contenu` par email à tous les abonnés actifs. ``True`` si l'API a accepté l'envoi.

    Lève ``RuntimeError`` si ``RESEND_FROM_EMAIL`` est absent ou s'il n'y a aucun
    abonné actif.
    """
    expediteur = os.getenv("RESEND_FROM_EMAIL")
    if not expediteur:
        raise RuntimeError(
            "RESEND_FROM_EMAIL manquant — copie .env.example en .env et renseigne "
            "l'adresse d'expédition (domaine vérifié sur Resend)."
        )

    destinataires = database.lister_abonnes_actifs()
    if not destinataires:
        raise RuntimeError("Aucun abonné actif — ajoute au moins un email via database.ajouter_abonne_email().")

    date_edition = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "from": expediteur,
        # Les abonnés sont en bcc (pas en to) pour qu'ils ne voient pas les adresses
        # des uns et des autres dans l'en-tête To: — "to" pointe sur l'expéditeur lui-même,
        # simple exigence technique de l'API Resend qui veut un destinataire principal.
        "to": [expediteur],
        "bcc": destinataires,
        "subject": f"AfroTech Pulse — Édition du {date_edition}",
        "text": contenu,
    }

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post("/emails", json=payload)
            if response.status_code == 200:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(
                    f"  [ERREUR API {response.status_code}] envoi email impossible, "
                    f"on abandonne. {response.text}"
                )
                return False
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] envoi email abandonné après {MAX_TENTATIVES} tentatives.")
    return False

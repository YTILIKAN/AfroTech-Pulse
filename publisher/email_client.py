# publisher/email_client.py — Client Resend, envoi de la newsletter par email aux abonnés actifs

import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

import database

load_dotenv()

MAX_TENTATIVES = 3

_client = None


def get_client():
    global _client
    if _client is None:
        cle = os.getenv("RESEND_API_KEY")
        if not cle:
            raise RuntimeError(
                "RESEND_API_KEY manquante — copie .env.example en .env et renseigne ta clé."
            )
        _client = httpx.Client(
            base_url="https://api.resend.com",
            headers={"Authorization": f"Bearer {cle}"},
            timeout=10.0,
        )
    return _client


def envoyer_email(contenu: str) -> bool:
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
        "to": destinataires,
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

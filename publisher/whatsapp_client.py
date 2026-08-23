# publisher/whatsapp_client.py — Client WhatsApp Business Cloud API, envoi vers le Channel Y'TILIKAN

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

MAX_TENTATIVES = 3
GRAPH_API_VERSION = "v19.0"

_client = None


def get_client():
    global _client
    if _client is None:
        token = os.getenv("WHATSAPP_TOKEN")
        if not token:
            raise RuntimeError(
                "WHATSAPP_TOKEN manquant — copie .env.example en .env et renseigne ton token."
            )
        _client = httpx.Client(
            base_url=f"https://graph.facebook.com/{GRAPH_API_VERSION}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    return _client


def envoyer_whatsapp(contenu: str) -> bool:
    channel_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not channel_id:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID manquant — copie .env.example en .env et renseigne "
            "l'identifiant du numéro/canal WhatsApp."
        )

    payload = {
        "messaging_product": "whatsapp",
        "to": channel_id,
        "type": "text",
        "text": {"body": contenu},
    }

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post(f"/{channel_id}/messages", json=payload)
            if response.status_code == 200:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(
                    f"  [ERREUR API {response.status_code}] envoi WhatsApp impossible, "
                    f"on abandonne. {response.text}"
                )
                return False
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] envoi WhatsApp abandonné après {MAX_TENTATIVES} tentatives.")
    return False

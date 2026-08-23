# publisher/linkedin_client.py — Client LinkedIn Posts API, publication sur la page Y'TILIKAN

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

MAX_TENTATIVES = 3
LINKEDIN_API_VERSION = "202401"

_client = None


def get_client():
    global _client
    if _client is None:
        token = os.getenv("LINKEDIN_TOKEN")
        if not token:
            raise RuntimeError(
                "LINKEDIN_TOKEN manquant — copie .env.example en .env et renseigne ton token."
            )
        _client = httpx.Client(
            base_url="https://api.linkedin.com/rest",
            headers={
                "Authorization": f"Bearer {token}",
                "LinkedIn-Version": LINKEDIN_API_VERSION,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
    return _client


def envoyer_linkedin(contenu: str) -> bool:
    organization_urn = os.getenv("LINKEDIN_ORGANIZATION_URN")
    if not organization_urn:
        raise RuntimeError(
            "LINKEDIN_ORGANIZATION_URN manquant — copie .env.example en .env et renseigne "
            "l'URN de la page LinkedIn Y'TILIKAN."
        )

    payload = {
        "author": organization_urn,
        "commentary": contenu,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post("/posts", json=payload)
            if response.status_code == 201:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(
                    f"  [ERREUR API {response.status_code}] publication LinkedIn impossible, "
                    f"on abandonne. {response.text}"
                )
                return False
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] publication LinkedIn abandonnée après {MAX_TENTATIVES} tentatives.")
    return False

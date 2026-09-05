# pipeline/summarize.py — Agent résumé LLM (Gemini) : 3 lignes, angle africain, en français

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.6-flash"
MAX_TENTATIVES = 3
LONGUEUR_MIN_CONTENU = 50

_client = None


def get_client():
    global _client
    if _client is None:
        cle = os.getenv("GEMINI_API_KEY")
        if not cle:
            raise RuntimeError(
                "GEMINI_API_KEY manquante — copie .env.example en .env et renseigne ta clé."
            )
        _client = httpx.Client(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            headers={"x-goog-api-key": cle, "Content-Type": "application/json"},
            timeout=30.0,
        )
    return _client

SYSTEM_PROMPT = """Tu es journaliste pour AfroTech Pulse, une newsletter qui couvre l'actualité de \
l'intelligence artificielle en Afrique.

Ta tâche : résumer l'article fourni en exactement 3 lignes, en français, avec un ton neutre \
et journalistique (pas de sensationnalisme, pas d'emojis).

Règle essentielle : le résumé doit obligatoirement inclure un angle africain concret.
- Si l'article parle déjà d'un pays, d'une organisation ou d'un acteur africain, mets ce lien en avant.
- Si l'article n'a aucun lien africain explicite (ex. un lancement produit aux États-Unis), \
reformule pour expliquer en quoi ce sujet pourrait concerner l'Afrique : marché potentiel, \
acteurs locaux comparables, secteur impacté (fintech, santé, éducation, agriculture...), \
adoption possible sur le continent.

Interdiction stricte : n'invente aucun fait, chiffre, nom d'entreprise ou d'organisation qui \
n'est pas dans l'article. La reformulation de l'angle africain doit rester plausible et \
prudente (ex. "pourrait", "un modèle similaire existe déjà en..."), jamais présentée comme \
un fait établi.

Format de réponse : 3 lignes distinctes séparées par un retour à la ligne (une phrase par ligne), \
sans numérotation, sans tiret, sans titre ni introduction."""


def summarize_article(titre: str, contenu: str) -> str | None:
    if not contenu or len(contenu.strip()) < LONGUEUR_MIN_CONTENU:
        print("  [IGNORÉ] article trop court/vide pour être résumé.")
        return None

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": f"Titre : {titre}\n\nContenu : {contenu}"}]}
        ],
    }

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post(f"/models/{MODEL}:generateContent", json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(f"  [ERREUR API {response.status_code}] résumé impossible, on abandonne. {response.text}")
                return None
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] résumé abandonné après {MAX_TENTATIVES} tentatives.")
    return None

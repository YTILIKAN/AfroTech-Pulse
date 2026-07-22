# pipeline/summarize.py — Agent résumé LLM (Mistral) : 3 lignes, angle africain, en français

import os
import time

import httpx
from dotenv import load_dotenv
from mistralai.client import Mistral
from mistralai.client.errors import SDKError

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise RuntimeError(
        "MISTRAL_API_KEY manquante — copie .env.example en .env et renseigne ta clé."
    )

MODEL = "mistral-small-latest"
MAX_TENTATIVES = 3
LONGUEUR_MIN_CONTENU = 50

client = Mistral(api_key=MISTRAL_API_KEY)

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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Titre : {titre}\n\nContenu : {contenu}"},
    ]

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = client.chat.complete(model=MODEL, messages=messages)
            return response.choices[0].message.content.strip()
        except SDKError as e:
            if e.raw_response.status_code != 429:
                print(f"  [ERREUR API {e.raw_response.status_code}] résumé impossible, on abandonne.")
                return None
            print(f"  [RATE LIMIT] tentative {tentative}/{MAX_TENTATIVES}...")
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] résumé abandonné après {MAX_TENTATIVES} tentatives.")
    return None


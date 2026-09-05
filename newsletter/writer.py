# newsletter/writer.py — Agent rédacteur : génère la newsletter complète (charte Y'TILIKAN)

import os
import re
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.6-flash"
MAX_TENTATIVES = 3

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


SYSTEM_PROMPT = """Tu es le rédacteur en chef d'AfroTech Pulse, la newsletter hebdomadaire de la \
communauté Y'TILIKAN qui couvre l'actualité de l'intelligence artificielle en Afrique.

Ta tâche : à partir de la sélection d'articles fournie (déjà choisis et résumés), rédiger la \
newsletter complète de la semaine, en français, avec un ton journalistique, informatif et \
engagé — jamais promotionnel, jamais sensationnaliste, sans emojis.

Structure obligatoire, dans cet ordre exact :

## Édito
Un paragraphe d'introduction (3 à 5 phrases) qui donne le ton de la semaine et met en avant \
un ou deux fils conducteurs parmi les articles sélectionnés (une tendance, une région qui \
se distingue, un secteur en mouvement). Pas de liste, pas de titre d'article cité ici.

## Cette semaine
Un bloc par article de la sélection, chacun sous la forme :

### <numéro>. <titre de l'article>
<reprise fidèle du résumé fourni pour cet article, 2 à 3 phrases>
Lien : <url de l'article>

Il doit y avoir exactement autant de blocs "###" que d'articles fournis, dans l'ordre où ils \
sont donnés, sans en ajouter ni en omettre.

## Conclusion
Un paragraphe de clôture (2 à 3 phrases) qui résume l'esprit de la semaine et invite à \
retrouver la prochaine édition. Pas de nouvelle information factuelle ici.

Interdiction stricte : n'invente et ne rajoute aucun fait, chiffre, nom d'entreprise, de \
personne ou d'organisation qui n'est pas déjà présent dans le titre, le résumé ou le contenu \
fournis pour chaque article. Ne fusionne pas deux articles entre eux. Base-toi uniquement sur \
la matière donnée.

Format de sortie : Markdown brut, respectant exactement les titres de section ci-dessus \
("## Édito", "## Cette semaine", "## Conclusion"), sans introduction ni commentaire avant ou \
après la newsletter elle-même. Ce même Markdown doit rester lisible tel quel sur Telegram \
et par email — pas de tableaux, pas d'images, pas de HTML."""


def _construire_prompt_utilisateur(articles: list[dict]) -> str:
    date_edition = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lignes = [f"Édition du {date_edition}. {len(articles)} article(s) sélectionné(s) cette semaine :\n"]

    for i, article in enumerate(articles, start=1):
        titre = article.get("titre") or article.get("title", "")
        url = article.get("url", "")
        resume = article.get("resume") or article.get("contenu") or article.get("content", "")
        lignes.append(f"{i}. {titre}\nLien : {url}\nRésumé : {resume}")

    return "\n\n".join(lignes)


def compter_articles(newsletter: str) -> int:
    return len(re.findall(r"^### ", newsletter, flags=re.MULTILINE))


def structure_respectee(newsletter: str, nb_articles_attendu: int) -> bool:
    if "## Édito" not in newsletter:
        return False
    if "## Cette semaine" not in newsletter:
        return False
    if "## Conclusion" not in newsletter:
        return False
    return compter_articles(newsletter) == nb_articles_attendu


def generer_newsletter(articles: list[dict]) -> str | None:
    if not articles:
        print("  [IGNORÉ] aucun article fourni, pas de newsletter à générer.")
        return None

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": _construire_prompt_utilisateur(articles)}]}
        ],
    }

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post(f"/models/{MODEL}:generateContent", json=payload)
            if response.status_code == 200:
                data = response.json()
                newsletter = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if not structure_respectee(newsletter, len(articles)):
                    print(
                        "  [ATTENTION] la structure générée ne respecte pas exactement le "
                        "template attendu (sections ou nombre d'articles) — à vérifier manuellement."
                    )
                return newsletter
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(f"  [ERREUR API {response.status_code}] génération impossible, on abandonne. {response.text}")
                return None
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] génération abandonnée après {MAX_TENTATIVES} tentatives.")
    return None

"""Déduplication d'un lot d'articles.

Deux passes : (1) doublon exact par hash MD5 du titre normalisé ; (2) quasi-doublon
par similarité cosinus des embeddings (`sentence-transformers`, modèle
multilingue) au-dessus de ``SEUIL_QUASI_DOUBLON``.

Le modèle d'embeddings est chargé paresseusement (premier appel seulement) et les
embeddings sont mis en cache sur chaque dict article pour la durée du lot.

Limite connue : la déduplication est **intra-lot** — `orchestrator.py` ne compare
pas un nouvel article à ceux déjà en base (voir README, « Limites connues »).
"""

import hashlib
import re
import string

MODELE_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"
SEUIL_QUASI_DOUBLON = 0.85

_model = None

PONCTUATION = string.punctuation + "’‘“”«»–—…"


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODELE_EMBEDDINGS)
    return _model


def hash_article(titre: str, url: str) -> str:
    """Hash MD5 du titre normalisé (minuscules, sans ponctuation, espaces réduits).

    `url` est ignorée : deux URL différentes avec le même titre sont un doublon.
    """
    titre_normalise = titre.lower().strip()
    titre_normalise = titre_normalise.translate(str.maketrans("", "", PONCTUATION))
    titre_normalise = re.sub(r"\s+", " ", titre_normalise).strip()
    return hashlib.md5(titre_normalise.encode("utf-8")).hexdigest()


def est_doublon_exact(article: dict, hashes_vus: set) -> bool:
    h = hash_article(article.get("title", ""), article.get("url", ""))
    return h in hashes_vus


def _embedding(article: dict):
    # Mis en cache sur l'article : évite de ré-encoder le même texte
    # à chaque comparaison avec un nouvel article du batch.
    if article.get("_embedding") is None:
        texte = f"{article.get('title', '')} {article.get('content', '')}".strip()
        article["_embedding"] = _get_model().encode(texte, normalize_embeddings=True)
    return article["_embedding"]


def est_quasi_doublon(article: dict, articles_vus: list, seuil: float = SEUIL_QUASI_DOUBLON) -> bool:
    if not articles_vus:
        return False

    embedding = _embedding(article)
    for autre in articles_vus:
        similarite = float(embedding @ _embedding(autre))
        if similarite >= seuil:
            return True
    return False


def deduplicate(articles: list) -> list:
    """Retourne la liste `articles` sans les doublons exacts ni les quasi-doublons.

    Conserve le premier exemplaire rencontré. Attend des dicts avec les clés
    ``title``, ``url``, ``content``. Affiche un récapitulatif sur stdout.
    """
    hashes_vus = set()
    articles_vus = []
    resultat = []
    nb_doublons_exacts = 0
    nb_quasi_doublons = 0

    for article in articles:
        if est_doublon_exact(article, hashes_vus):
            nb_doublons_exacts += 1
            continue

        if est_quasi_doublon(article, articles_vus):
            nb_quasi_doublons += 1
            continue

        hashes_vus.add(hash_article(article.get("title", ""), article.get("url", "")))
        articles_vus.append(article)
        resultat.append(article)

    print(
        f"Déduplication : {nb_doublons_exacts} doublons exacts, "
        f"{nb_quasi_doublons} quasi-doublons retirés sur {len(articles)} articles "
        f"({len(resultat)} conservés)"
    )
    return resultat

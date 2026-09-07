# pipeline/dedup.py — Déduplication par hashing MD5 + similarité cosinus

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

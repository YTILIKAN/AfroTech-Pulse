# dashboard/aggregations.py — Agrégations pures (aucun accès I/O) sur une liste d'articles
# déjà enrichis par dashboard.enrichment.enrichir().

from collections import Counter
from datetime import timedelta

from dashboard.data import fenetre_semaines


def par_pays(articles_enrichis):
    """{code ISO-3: nombre d'articles}. Les articles sans pays détecté sont ignorés."""
    compte = Counter()
    for article in articles_enrichis:
        iso = article.get("pays_iso")
        if iso:
            compte[iso] += 1
    return dict(compte)


def par_secteur(articles_enrichis):
    """{secteur: nombre d'articles}. Un article multi-secteurs compte dans chacun."""
    compte = Counter()
    for article in articles_enrichis:
        for secteur in article.get("secteurs") or []:
            compte[secteur] += 1
    return dict(compte)


def comparer_pays(articles_enrichis, codes_iso):
    """{iso: {"nom", "articles", "secteurs"}} pour les pays demandés.

    Les pays sans aucun article sur la période sont retournés à zéro plutôt qu'omis :
    dans une vue comparative, « le Ghana n'a rien publié » est une information, pas un
    trou dans le graphique.
    """
    resultat = {
        iso: {"nom": iso, "articles": 0, "secteurs": {}} for iso in codes_iso
    }

    for article in articles_enrichis:
        iso = article.get("pays_iso")
        if iso not in resultat:
            continue
        entree = resultat[iso]
        entree["articles"] += 1
        if article.get("pays_nom"):
            entree["nom"] = article["pays_nom"]
        for secteur in article.get("secteurs") or []:
            entree["secteurs"][secteur] = entree["secteurs"].get(secteur, 0) + 1

    return resultat


def par_semaine(articles, n_semaines=4, maintenant=None):
    """Liste de (lundi ISO 'YYYY-MM-DD', nombre d'articles) sur les n dernières semaines.
    Toujours n entrées, y compris les semaines à 0 (sinon la timeline a des trous)."""
    debut = fenetre_semaines(maintenant=maintenant, semaines=n_semaines)
    libelles = [
        (debut + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(n_semaines)
    ]
    compte = {libelle: 0 for libelle in libelles}

    for article in articles:
        date_pub = article["date_pub"]
        if date_pub < debut:
            continue
        index = (date_pub - debut).days // 7
        if 0 <= index < n_semaines:
            compte[libelles[index]] += 1

    return [(libelle, compte[libelle]) for libelle in libelles]

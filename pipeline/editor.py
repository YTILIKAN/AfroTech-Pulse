# pipeline/editor.py — Agent éditeur : sélection hebdomadaire des 5-7 meilleurs articles
# Combine score de pertinence (S3), fraîcheur, et diversité géographique.

from datetime import datetime, timezone

import database
from pipeline.filter import detecter_pays

BONUS_FRAICHEUR_MAX = 20
JOURS_FRAICHEUR_MAX = 7

SELECTION_MIN = 5
SELECTION_MAX = 7
MAX_ARTICLES_PAR_PAYS = 2


def _jours_depuis_publication(date_pub: str, maintenant: datetime | None = None) -> float:
    """Nombre de jours écoulés depuis date_pub.

    Retourne JOURS_FRAICHEUR_MAX (donc bonus de fraîcheur nul) si la date est
    absente ou mal formée, pour ne jamais faire planter le scoring sur une
    donnée de scraping imparfaite.
    """
    if maintenant is None:
        maintenant = datetime.now(timezone.utc)
    if not date_pub:
        return JOURS_FRAICHEUR_MAX
    try:
        publie = datetime.fromisoformat(date_pub)
        if publie.tzinfo is None:
            publie = publie.replace(tzinfo=timezone.utc)
    except ValueError:
        return JOURS_FRAICHEUR_MAX
    return max(0.0, (maintenant - publie).total_seconds() / 86400)


def score_editorial(score_pertinence: int, date_pub: str, maintenant: datetime | None = None) -> float:
    """Score éditorial = pertinence africaine (S3) + bonus de fraîcheur.

    Le bonus de diversité géographique n'est volontairement pas inclus ici :
    il dépend des articles déjà retenus dans la sélection en cours (un même
    pays ne doit pas dominer la semaine), donc il est appliqué au niveau de
    selectionner_articles_semaine(), pas sur un article isolé.
    """
    jours = _jours_depuis_publication(date_pub, maintenant)
    ratio_fraicheur = max(0.0, 1 - jours / JOURS_FRAICHEUR_MAX)
    bonus_fraicheur = BONUS_FRAICHEUR_MAX * ratio_fraicheur
    return round(score_pertinence + bonus_fraicheur, 2)


def selectionner_articles_semaine(seuil=None, maintenant=None):
    """Sélectionne 5 à 7 articles parmi les candidats résumés et pas encore
    sélectionnés (database.articles_selectionnables), triés par score
    éditorial, avec une règle de diversité géographique (max
    MAX_ARTICLES_PAR_PAYS articles par pays détecté).

    Fonction pure (aucune écriture en base) : le marquage en base est fait
    séparément par l'appelant (run_editor.py), via database.marquer_selectionne().
    """
    if seuil is None:
        seuil = database.SEUIL_PERTINENCE

    candidats = database.articles_selectionnables(seuil=seuil)

    enrichis = []
    for url, titre, contenu, source_id, date_pub, score_pertinence, resume in candidats:
        enrichis.append({
            "url": url,
            "titre": titre,
            "resume": resume,
            "source_id": source_id,
            "pays": detecter_pays(titre, contenu),
            "score_editorial": score_editorial(score_pertinence, date_pub, maintenant),
        })

    enrichis.sort(key=lambda a: a["score_editorial"], reverse=True)

    selection = []
    compte_par_pays = {}

    for article in enrichis:
        if len(selection) >= SELECTION_MAX:
            break
        pays = article["pays"]
        # Un article sans pays détectable ne compte pas dans la règle de
        # diversité : on ne sait pas de quel pays le pénaliser.
        if pays is not None and compte_par_pays.get(pays, 0) >= MAX_ARTICLES_PAR_PAYS:
            continue
        selection.append(article)
        if pays is not None:
            compte_par_pays[pays] = compte_par_pays.get(pays, 0) + 1

    # Si la règle de diversité empêche d'atteindre le minimum, on complète
    # avec les meilleurs articles restants malgré la sur-représentation d'un pays,
    # plutôt que de livrer une newsletter trop courte.
    if len(selection) < SELECTION_MIN:
        urls_deja_choisis = {a["url"] for a in selection}
        for article in enrichis:
            if len(selection) >= SELECTION_MIN:
                break
            if article["url"] in urls_deja_choisis:
                continue
            selection.append(article)

    return selection

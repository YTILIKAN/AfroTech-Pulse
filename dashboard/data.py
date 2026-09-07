# dashboard/data.py — Accès aux données du dashboard.
#
# Seul module du dashboard qui touche SQLite : les tests injectent une fixture en passant
# un autre db_path, sans avoir à monter une vraie base.

import sqlite3
from datetime import datetime, timedelta, timezone

import database


def _parser_date(valeur):
    """Parse une date_pub ISO (avec ou sans fuseau, avec ou sans 'Z') en datetime naïf UTC.
    Retourne None si la valeur est vide ou non parsable."""
    if not valeur:
        return None
    texte = valeur.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(texte)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def lundi_courant(maintenant=None):
    """Lundi 00:00 de la semaine en cours (borne haute, exclue, de la période analysée :
    la semaine en cours est partielle, on ne la montre pas)."""
    maintenant = maintenant or datetime.now(timezone.utc).replace(tzinfo=None)
    return (maintenant - timedelta(days=maintenant.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def fenetre_semaines(maintenant=None, semaines=4):
    """Borne basse de la période : lundi 00:00 d'il y a `semaines` semaines. Combinée à
    lundi_courant() comme borne haute, on couvre exactement `semaines` semaines
    calendaires *complètes*, alignées sur le lundi."""
    return lundi_courant(maintenant) - timedelta(weeks=semaines)


# Le dashboard illustre « le pouls de l'IA EN AFRIQUE » : on ne garde que les articles
# ayant au moins un signal de pertinence africaine (pays, ville, organisation ou source
# africaine détectés par pipeline/filter.py). score_pertinence == 0 = aucun lien Afrique
# détecté (ex. un papier arXiv de ML générique) — hors sujet pour ce dashboard.
SCORE_MIN_DEFAUT = 1


def charger_articles(db_path=None, depuis=None, jusqua=None, score_min=SCORE_MIN_DEFAUT):
    """Charge les articles depuis articles_raw. `depuis`/`jusqua` (datetime naïfs UTC)
    bornent date_pub ([depuis, jusqua[), `score_min` borne score_pertinence. Les articles
    sans date_pub parsable sont ignorés (ni timeline ni fenêtre temporelle possibles)."""
    db_path = db_path or database.DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        lignes = conn.execute(
            """
            SELECT titre, contenu, resume, source_id, date_pub, score_pertinence
            FROM articles_raw
            WHERE score_pertinence >= ?
            """,
            (score_min,),
        ).fetchall()
    finally:
        conn.close()

    articles = []
    for titre, contenu, resume, source_id, date_pub, score in lignes:
        dt = _parser_date(date_pub)
        if dt is None:
            continue
        if depuis is not None and dt < depuis:
            continue
        if jusqua is not None and dt >= jusqua:
            continue
        articles.append(
            {
                "titre": titre or "",
                "contenu": contenu or "",
                "resume": resume or "",
                "source_id": source_id or "",
                "date_pub": dt,
                "score_pertinence": score or 0,
            }
        )
    return articles

"""Copie de la base de prod, rajeunie pour que les tests du dashboard ne dépendent pas de la date du jour.

Le dashboard n'affiche que les 4 dernières semaines complètes : une base commitée
« figée » à une date passée donne une page vide (0 graphique) dès que ces 4 semaines
dépassent son dernier article. On décale donc toutes les `date_pub` d'un nombre entier
de semaines — le jour de la semaine et les écarts relatifs sont préservés — pour que
l'article le plus récent tombe dans la dernière semaine complète.
"""

import shutil
import sqlite3
from datetime import timedelta
from pathlib import Path

from dashboard.data import _parser_date, lundi_courant

DB_PROD = Path(__file__).resolve().parent.parent / "afrotech.db"


def copie_prod_rajeunie(destination):
    shutil.copy(DB_PROD, destination)

    conn = sqlite3.connect(destination)
    try:
        lignes = conn.execute(
            "SELECT rowid, date_pub FROM articles_raw WHERE date_pub IS NOT NULL"
        ).fetchall()
        dates = {rowid: _parser_date(brut) for rowid, brut in lignes}
        valides = [d for d in dates.values() if d is not None]
        if not valides:
            return

        semaine = timedelta(weeks=1)
        retard = lundi_courant() - max(valides)
        decalage = retard // semaine
        if retard % semaine == timedelta(0):
            decalage -= 1
        if decalage <= 0:
            return

        decalage_total = decalage * semaine
        conn.executemany(
            "UPDATE articles_raw SET date_pub = ? WHERE rowid = ?",
            [
                ((dt + decalage_total).isoformat(), rowid)
                for rowid, dt in dates.items()
                if dt is not None
            ],
        )
        conn.commit()
    finally:
        conn.close()

# dashboard/filters.py — Filtres du dashboard V2 : période, pays, secteur.
#
# Fonctions pures : aucun accès SQLite, aucun appel Streamlit. Le dashboard charge une
# seule fois la fenêtre la plus large (cf. PERIODE_MAX) et dérive toutes les vues d'ici,
# plutôt que de relire la base à chaque changement de filtre.

from dashboard.data import fenetre_semaines, lundi_courant

PERIODES = (4, 8, 12)
PERIODE_DEFAUT = 4
PERIODE_MAX = max(PERIODES)


def bornes_periode(n_semaines, maintenant=None):
    """(depuis, jusqua) pour une période de n semaines calendaires complètes.

    Mêmes bornes que la V1 : alignées sur le lundi, la semaine en cours étant exclue
    parce qu'elle est partielle.
    """
    return fenetre_semaines(maintenant=maintenant, semaines=n_semaines), lundi_courant(maintenant)


def filtrer(articles, pays_iso=(), secteurs=(), depuis=None, jusqua=None):
    """Filtre une liste d'articles enrichis.

    Convention st.multiselect : une sélection vide ne filtre pas cette dimension.
    À l'intérieur d'une dimension les valeurs sont en OU (Kenya *ou* Nigéria) ; entre
    dimensions elles sont en ET (Kenya *et* fintech). Un article multi-secteurs matche
    dès qu'un de ses secteurs est retenu.
    """
    pays_iso = set(pays_iso or ())
    secteurs = set(secteurs or ())

    resultat = []
    for article in articles:
        date_pub = article.get("date_pub")
        if depuis is not None and date_pub is not None and date_pub < depuis:
            continue
        if jusqua is not None and date_pub is not None and date_pub >= jusqua:
            continue
        # Un article sans pays détecté sort dès qu'un filtre pays est actif : on ne peut
        # pas affirmer qu'il concerne le pays demandé.
        if pays_iso and article.get("pays_iso") not in pays_iso:
            continue
        if secteurs and not (set(article.get("secteurs") or ()) & secteurs):
            continue
        resultat.append(article)
    return resultat


def options_pays(articles):
    """[(iso, nom, nombre d'articles)] des pays réellement présents, du plus couvert au moins.

    Les options viennent des données affichées, pas de la table complète des ~55 pays :
    proposer un filtre qui ne renverrait rien serait trompeur.
    """
    comptes = {}
    noms = {}
    for article in articles:
        iso = article.get("pays_iso")
        if not iso:
            continue
        comptes[iso] = comptes.get(iso, 0) + 1
        noms[iso] = article.get("pays_nom") or iso
    return sorted(
        ((iso, noms[iso], n) for iso, n in comptes.items()),
        key=lambda t: (-t[2], t[1]),
    )


def options_secteurs(articles):
    """[(secteur, nombre d'articles)] des secteurs présents, du plus au moins fréquent."""
    comptes = {}
    for article in articles:
        for secteur in article.get("secteurs") or []:
            comptes[secteur] = comptes.get(secteur, 0) + 1
    return sorted(comptes.items(), key=lambda t: (-t[1], t[0]))

# archive/search.py — Moteur de recherche Whoosh sur toutes les éditions

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from whoosh import highlight, index
from whoosh.analysis import CharsetFilter, StandardAnalyzer
from whoosh.fields import ID, STORED, TEXT, Schema
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.query import Every
from whoosh.support.charset import accent_map

import database

INDEX_DIR = "archive/index_whoosh"

# Repli des accents : « edition validee » doit retrouver « édition validée ». Pas de stemming,
# celui de Whoosh est anglais et massacrerait les terminaisons françaises.
ANALYSEUR_FR = StandardAnalyzer() | CharsetFilter(accent_map)

LONGUEUR_EXTRAIT = 300

MOIS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _schema():
    return Schema(
        id=ID(unique=True, stored=True),
        titre=TEXT(stored=True, analyzer=ANALYSEUR_FR),
        contenu=TEXT(stored=True, analyzer=ANALYSEUR_FR),
        date_generation=ID(stored=True, sortable=True),
        nb_articles=STORED,
    )


class _FormatteurMarkdown(highlight.Formatter):
    """Met les mots trouvés en **gras** markdown.

    Le formateur HTML par défaut de Whoosh obligerait l'app à appeler st.markdown() avec
    unsafe_allow_html=True, donc à rendre du HTML brut issu du contenu des newsletters.
    """

    def format_token(self, text, token, replace=False):
        return f"**{highlight.get_text(text, token, replace)}**"


def _titre_edition(date_generation, edition_id):
    """Titre d'archive : « Édition du 6 septembre 2026 ».

    Le format documenté (docs/format_newsletter.md) commence directement par « ## Édito » :
    il n'y a pas de titre H1 à extraire, et un H1 vaudrait de toute façon « AfroTech Pulse »
    pour toutes les éditions. La date est ce qui les distingue réellement.
    """
    try:
        annee, mois, jour = date_generation.split("T")[0].split("-")
        return f"Édition du {int(jour)} {MOIS_FR[int(mois) - 1]} {annee}"
    except (AttributeError, IndexError, ValueError):
        return f"Édition #{edition_id}"


def _sans_titres_markdown(texte):
    """Retire les « # » de tête : un extrait affiché dans une carte ne doit pas rendre un H2."""
    lignes = [ligne.lstrip("#").strip() for ligne in (texte or "").splitlines()]
    return "\n".join(ligne for ligne in lignes if ligne)


def _apercu(contenu):
    texte = _sans_titres_markdown(contenu).replace("\n", " ")
    if len(texte) <= LONGUEUR_EXTRAIT:
        return texte
    return texte[:LONGUEUR_EXTRAIT].rstrip() + "…"


def _ouvrir_index():
    if not os.path.exists(INDEX_DIR):
        os.makedirs(INDEX_DIR, exist_ok=True)
    if index.exists_in(INDEX_DIR):
        return index.open_dir(INDEX_DIR)
    return index.create_in(INDEX_DIR, _schema())


def _index_absent():
    return not (os.path.exists(INDEX_DIR) and index.exists_in(INDEX_DIR))


def _ids_indexes(ix):
    with ix.searcher() as searcher:
        return {champs["id"] for champs in searcher.reader().all_stored_fields()}


def indexer_editions():
    """(Ré)indexe toutes les newsletters publiées. Idempotent : rejouable sans dupliquer."""
    editions = database.lister_editions_publiees()
    ix = _ouvrir_index()
    ids_deja_indexes = _ids_indexes(ix)

    writer = ix.writer()
    try:
        ids_publies = set()
        for edition_id, contenu, nb_articles, _statut, date_generation in editions:
            ids_publies.add(str(edition_id))
            # update_document() remplace le document portant le même id (champ unique)
            # au lieu d'en ajouter un second : c'est ce qui garantit la non-duplication.
            writer.update_document(
                id=str(edition_id),
                titre=_titre_edition(date_generation, edition_id),
                contenu=contenu or "",
                date_generation=date_generation,
                nb_articles=nb_articles,
            )

        # Une édition dépubliée (ou dont le statut a été corrigé à la main en base) doit
        # sortir de l'index, sinon l'archive publique afficherait un contenu retiré.
        for id_obsolete in ids_deja_indexes - ids_publies:
            writer.delete_by_term("id", id_obsolete)
    except Exception:
        writer.cancel()
        raise

    writer.commit()
    return len(editions)


def _formater(hit, avec_extrait):
    contenu = hit.get("contenu", "")
    if avec_extrait:
        # Le fragment de Whoosh est découpé dans le markdown brut : il peut tomber au milieu
        # d'un « ### 3. Titre ». On le nettoie avant de le rendre dans une carte.
        extrait = _sans_titres_markdown(hit.highlights("contenu")).replace("\n", " ")
        extrait = extrait or _apercu(contenu)
    else:
        extrait = _apercu(contenu)

    return {
        "id": int(hit["id"]),
        "titre": hit.get("titre", ""),
        "contenu": contenu,
        "date_generation": hit.get("date_generation", ""),
        "nb_articles": hit.get("nb_articles"),
        "extrait": extrait,
        "score": hit.score,
    }


def rechercher(query="", limit=None):
    """Retourne les éditions publiées correspondant à `query`.

    Recherche vide → toutes les éditions publiées, de la plus récente à la plus ancienne.
    L'index est construit à la volée s'il est absent (il est gitignoré : un clone frais n'en a pas).
    """
    if _index_absent():
        indexer_editions()

    ix = _ouvrir_index()
    terme = (query or "").strip()

    with ix.searcher() as searcher:
        if terme:
            parseur = MultifieldParser(
                ["titre", "contenu"], schema=ix.schema, group=OrGroup.factory(0.9)
            )
            resultats = searcher.search(parseur.parse(terme), limit=limit)
            resultats.formatter = _FormatteurMarkdown()
            resultats.fragmenter.surround = 60
        else:
            resultats = searcher.search(
                Every(), limit=limit, sortedby="date_generation", reverse=True
            )
        return [_formater(hit, avec_extrait=bool(terme)) for hit in resultats]


if __name__ == "__main__":
    database.creer_base()
    nb = indexer_editions()
    print(f"{nb} édition(s) publiée(s) indexée(s) dans '{INDEX_DIR}'.")

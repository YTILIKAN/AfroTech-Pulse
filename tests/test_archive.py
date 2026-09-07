import database
import archive.search as search_module
import publisher.publish as publish_module
from archive.search import indexer_editions, rechercher
from publisher.publish import publish_newsletter

# Format réel des newsletters (docs/format_newsletter.md) : pas de titre H1, ça commence à « ## Édito ».
CONTENUS = {
    "kenya": "## Édito\nL'IA transforme l'agriculture au Kenya cette semaine.\n\n## Conclusion\nÀ suivre.",
    "fintech": "## Édito\nUne startup fintech nigériane lève 20 millions de dollars.\n\n## Conclusion\nÀ suivre.",
    "energie": "## Édito\nLe solaire off-grid accélère l'accès à l'énergie au Sahel.\n\n## Conclusion\nÀ suivre.",
}


def _publier(contenu, nb_articles=3):
    newsletter_id = database.sauvegarder_newsletter(contenu, nb_articles=nb_articles)
    database.changer_statut_newsletter(newsletter_id, "en_revue", "Alice")
    database.changer_statut_newsletter(newsletter_id, "validé", "Alice")
    database.changer_statut_newsletter(newsletter_id, "publié", "Alice")
    return newsletter_id


def _preparer_archive(monkeypatch, tmp_path):
    """Base et index isolés, avec les 5 statuts représentés : seuls les 'publié' sont indexables."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(search_module, "INDEX_DIR", str(tmp_path / "index_whoosh"))
    database.creer_base()

    ids = {cle: _publier(contenu) for cle, contenu in CONTENUS.items()}

    ids["brouillon"] = database.sauvegarder_newsletter("# Brouillon\n\nKenya en brouillon.", 1)

    ids["validé"] = database.sauvegarder_newsletter("# Validée\n\nKenya validé non publié.", 2)
    database.changer_statut_newsletter(ids["validé"], "en_revue", "Alice")
    database.changer_statut_newsletter(ids["validé"], "validé", "Alice")

    ids["rejeté"] = database.sauvegarder_newsletter("# Rejetée\n\nKenya rejeté.", 1)
    database.changer_statut_newsletter(ids["rejeté"], "en_revue", "Alice")
    database.changer_statut_newsletter(ids["rejeté"], "rejeté", "Bob")

    return ids


def test_indexation_puis_recherche_ne_remonte_que_l_edition_concernee(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)

    assert indexer_editions() == 3, "seules les 3 éditions publiées doivent être indexées"

    resultats = rechercher("Kenya")

    assert [r["id"] for r in resultats] == [ids["kenya"]], (
        "la recherche doit remonter la seule édition publiée contenant le mot-clé"
    )
    assert resultats[0]["nb_articles"] == 3
    assert "**Kenya**" in resultats[0]["extrait"], (
        "l'extrait doit mettre le mot-clé en gras markdown pour l'affichage Streamlit"
    )
    assert not resultats[0]["extrait"].lstrip().startswith("#"), (
        "l'extrait ne doit pas rendre un titre markdown au milieu d'une carte de résultat"
    )


def test_titre_est_date_car_le_format_reel_n_a_pas_de_h1(monkeypatch, tmp_path):
    _preparer_archive(monkeypatch, tmp_path)
    indexer_editions()

    titres = [r["titre"] for r in rechercher("")]

    assert all(t.startswith("Édition du ") for t in titres), (
        "le format documenté commence par « ## Édito » : le titre d'archive doit venir de la "
        f"date, pas du contenu (obtenu : {titres})"
    )
    assert search_module._titre_edition("2026-09-06T09:00:00+00:00", 7) == "Édition du 6 septembre 2026"
    assert search_module._titre_edition(None, 7) == "Édition #7", "repli si la date est illisible"


def test_reindexation_ne_duplique_pas(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)

    indexer_editions()
    indexer_editions()
    indexer_editions()

    toutes = rechercher("")
    assert len(toutes) == 3, "trois réindexations ne doivent pas créer de doublons dans l'index"
    assert len({r["id"] for r in toutes}) == 3, "chaque édition ne doit apparaître qu'une fois"
    assert [r["id"] for r in rechercher("Kenya")] == [ids["kenya"]], (
        "une édition réindexée ne doit pas remonter plusieurs fois dans les résultats"
    )


def test_recherche_vide_retourne_toutes_les_editions_publiees(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)
    indexer_editions()

    resultats = rechercher("")
    ids_trouves = [r["id"] for r in resultats]

    assert set(ids_trouves) == {ids["kenya"], ids["fintech"], ids["energie"]}, (
        "une recherche vide doit lister toutes les éditions publiées"
    )
    for statut in ("brouillon", "validé", "rejeté"):
        assert ids[statut] not in ids_trouves, (
            f"une newsletter en statut '{statut}' ne doit jamais apparaître dans l'archive publique"
        )

    dates = [r["date_generation"] for r in resultats]
    assert dates == sorted(dates, reverse=True), "l'archive doit lister la plus récente en premier"

    assert rechercher("   ") == resultats, "une requête faite d'espaces vaut une recherche vide"


def test_recherche_ignore_les_accents(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)
    indexer_editions()

    assert [r["id"] for r in rechercher("energie")] == [ids["energie"]], (
        "« energie » sans accent doit retrouver « énergie » (repli des accents à l'indexation)"
    )


def test_index_absent_est_construit_a_la_volee(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)
    # aucun appel à indexer_editions() : le dossier d'index n'existe pas encore (il est gitignoré)

    assert [r["id"] for r in rechercher("fintech")] == [ids["fintech"]], (
        "rechercher() doit construire l'index absent au lieu de retourner une liste vide"
    )


def test_edition_depubliee_sort_de_l_index(monkeypatch, tmp_path):
    ids = _preparer_archive(monkeypatch, tmp_path)
    indexer_editions()

    # Correction manuelle en base : la machine à états n'autorise pas de sortie de 'publié'.
    import sqlite3

    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("UPDATE newsletters SET statut = 'rejeté' WHERE id = ?", (ids["kenya"],))
    conn.commit()
    conn.close()

    indexer_editions()

    assert rechercher("Kenya") == [], "une édition dépubliée doit disparaître de l'archive publique"
    assert len(rechercher("")) == 2


# --- Hook de réindexation après publication (publisher/publish.py) ---


def _preparer_newsletter_validee(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(search_module, "INDEX_DIR", str(tmp_path / "index_whoosh"))
    database.creer_base()
    newsletter_id = database.sauvegarder_newsletter(CONTENUS["kenya"], nb_articles=3)
    database.changer_statut_newsletter(newsletter_id, "en_revue", "Alice")
    database.changer_statut_newsletter(newsletter_id, "validé", "Alice")
    return newsletter_id


def test_publication_reussie_rend_l_edition_cherchable(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: True)

    publish_newsletter()

    assert [r["id"] for r in rechercher("Kenya")] == [newsletter_id], (
        "une publication réussie doit réindexer l'archive sans intervention manuelle"
    )


def test_publication_echouee_n_indexe_rien(monkeypatch, tmp_path):
    _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: False)

    publish_newsletter()

    assert rechercher("") == [], (
        "une newsletter restée en 'validé' après échec ne doit pas atterrir dans l'archive publique"
    )


def test_echec_d_indexation_ne_fait_pas_echouer_la_publication(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: True)

    def indexation_qui_plante():
        raise OSError("disque plein")

    monkeypatch.setattr(search_module, "indexer_editions", indexation_qui_plante)

    resultats = publish_newsletter()

    assert resultats == {"telegram": True}, "l'envoi a réussi, le résultat doit le refléter"
    assert database.newsletter_par_id(newsletter_id)[3] == "publié", (
        "une archive en panne ne doit jamais annuler une publication déjà partie aux abonnés"
    )

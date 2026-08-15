import database
import publisher.publish as publish_module
from publisher.publish import publish_newsletter

CONTENU = "## Édito\nTest.\n\n## Cette semaine\n### 1. Article\nRésumé.\nLien : https://exemple.com\n\n## Conclusion\nFin."


def _newsletter_validee(nb_articles=3):
    newsletter_id = database.sauvegarder_newsletter(CONTENU, nb_articles=nb_articles)
    database.changer_statut_newsletter(newsletter_id, "en_revue", "Steve")
    database.changer_statut_newsletter(newsletter_id, "validé", "Steve")
    return newsletter_id


def _preparer_db(monkeypatch, tmp_path, nom_fichier):
    test_db = tmp_path / nom_fichier
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()


# --- publish_newsletter() : les 4 combinaisons ------------------------------

def test_whatsapp_ok_linkedin_ok_marque_publie(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_ok_ok.db")
    newsletter_id = _newsletter_validee()
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: True)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: True)

    resultat = publish_newsletter(newsletter_id)

    assert resultat == {"whatsapp": True, "linkedin": True}
    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "publié", "les deux canaux ont réussi, le statut doit passer à publié"
    assert newsletter[5] == 1 and newsletter[6] == 1


def test_whatsapp_ok_linkedin_ko_ne_marque_pas_publie(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_ok_ko.db")
    newsletter_id = _newsletter_validee()
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: True)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: False)

    resultat = publish_newsletter(newsletter_id)

    assert resultat == {"whatsapp": True, "linkedin": False}
    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "validé", "un échec partiel ne doit jamais marquer publié"
    assert newsletter[5] == 1, "le canal WhatsApp réussi doit être marqué"
    assert newsletter[6] == 0, "le canal LinkedIn en échec ne doit pas être marqué"


def test_whatsapp_ko_linkedin_ok_ne_marque_pas_publie(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_ko_ok.db")
    newsletter_id = _newsletter_validee()
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: False)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: True)

    resultat = publish_newsletter(newsletter_id)

    assert resultat == {"whatsapp": False, "linkedin": True}
    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "validé", "un échec partiel ne doit jamais marquer publié"
    assert newsletter[5] == 0
    assert newsletter[6] == 1


def test_whatsapp_ko_linkedin_ko_ne_marque_pas_publie(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_ko_ko.db")
    newsletter_id = _newsletter_validee()
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: False)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: False)

    resultat = publish_newsletter(newsletter_id)

    assert resultat == {"whatsapp": False, "linkedin": False}
    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "validé", "aucun canal n'a réussi, le statut ne doit pas bouger"
    assert newsletter[5] == 0 and newsletter[6] == 0


# --- retry ciblé : ne republie pas sur le canal déjà réussi -----------------

def test_retry_apres_echec_partiel_ne_republie_pas_le_canal_deja_reussi(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_retry.db")
    newsletter_id = _newsletter_validee()

    appels_whatsapp = {"n": 0}

    def whatsapp_toujours_ok(contenu):
        appels_whatsapp["n"] += 1
        return True

    monkeypatch.setattr(publish_module, "publier_whatsapp", whatsapp_toujours_ok)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: False)

    resultat_1 = publish_newsletter(newsletter_id)
    assert resultat_1 == {"whatsapp": True, "linkedin": False}
    assert appels_whatsapp["n"] == 1

    # Le problème LinkedIn est corrigé entre-temps ; on relance la publication.
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: True)
    resultat_2 = publish_newsletter(newsletter_id)

    assert resultat_2 == {"whatsapp": True, "linkedin": True}
    assert appels_whatsapp["n"] == 1, \
        "le canal WhatsApp déjà publié ne doit pas être republié lors du nouvel essai"
    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "publié"


# --- non-régression ----------------------------------------------------------

def test_newsletter_introuvable_leve_erreur(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_introuvable.db")
    try:
        publish_newsletter(9999)
        assert False, "devrait lever ValueError pour une newsletter inexistante"
    except ValueError:
        pass


def test_publication_refusee_si_statut_pas_valide(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_statut_invalide.db")
    newsletter_id = database.sauvegarder_newsletter(CONTENU, nb_articles=3)  # reste en brouillon
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: True)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: True)

    try:
        publish_newsletter(newsletter_id)
        assert False, "une newsletter non validée ne doit jamais être publiée"
    except ValueError:
        pass

    newsletter = database.obtenir_newsletter(newsletter_id)
    assert newsletter[3] == "brouillon", "le statut ne doit pas bouger si la publication est refusée"


def test_newsletter_deja_publiee_ne_peut_pas_etre_republiee(monkeypatch, tmp_path):
    _preparer_db(monkeypatch, tmp_path, "publish_deja_publiee.db")
    newsletter_id = _newsletter_validee()
    monkeypatch.setattr(publish_module, "publier_whatsapp", lambda contenu: True)
    monkeypatch.setattr(publish_module, "publier_linkedin", lambda contenu: True)
    publish_newsletter(newsletter_id)

    try:
        publish_newsletter(newsletter_id)
        assert False, "une newsletter déjà publiée ne doit pas pouvoir être republiée"
    except ValueError:
        pass

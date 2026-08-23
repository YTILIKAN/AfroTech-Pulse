import database
import publisher.publish as publish_module
from publisher.publish import publish_newsletter, republier_canal


def _preparer_newsletter_validee(monkeypatch, tmp_path):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()
    newsletter_id = database.sauvegarder_newsletter("# AfroTech Pulse\n\nContenu test.", nb_articles=3)
    database.changer_statut_newsletter(newsletter_id, "en_revue", "Alice")
    database.changer_statut_newsletter(newsletter_id, "validé", "Alice")
    return newsletter_id


def test_whatsapp_ok_linkedin_ok_marque_publie(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "whatsapp", lambda contenu: True)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: True)

    resultats = publish_newsletter()

    assert resultats == {"whatsapp": True, "linkedin": True}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "publié", "les deux canaux ont réussi, le statut global doit être 'publié'"


def test_whatsapp_ok_linkedin_ko_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "whatsapp", lambda contenu: True)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: False)

    resultats = publish_newsletter()

    assert resultats == {"whatsapp": True, "linkedin": False}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec partiel ne doit jamais marquer statut = publié"

    publications = {c: s for c, s, *_ in database.statuts_publication(newsletter_id)}
    assert publications["whatsapp"] == "publié"
    assert publications["linkedin"] == "echec"


def test_whatsapp_ko_linkedin_ok_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "whatsapp", lambda contenu: False)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: True)

    resultats = publish_newsletter()

    assert resultats == {"whatsapp": False, "linkedin": True}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec partiel ne doit jamais marquer statut = publié"

    publications = {c: s for c, s, *_ in database.statuts_publication(newsletter_id)}
    assert publications["whatsapp"] == "echec"
    assert publications["linkedin"] == "publié"


def test_whatsapp_ko_linkedin_ko_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "whatsapp", lambda contenu: False)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: False)

    resultats = publish_newsletter()

    assert resultats == {"whatsapp": False, "linkedin": False}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec total ne doit jamais marquer statut = publié"


def test_republication_ciblee_ne_retouche_pas_le_canal_deja_reussi(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)

    appels_whatsapp = {"n": 0}

    def whatsapp_fn(contenu):
        appels_whatsapp["n"] += 1
        return True

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "whatsapp", whatsapp_fn)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: False)

    publish_newsletter()
    assert appels_whatsapp["n"] == 1

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "linkedin", lambda contenu: True)
    succes = republier_canal(newsletter_id, "linkedin")

    assert succes is True
    assert appels_whatsapp["n"] == 1, "republier_canal() ne doit pas réenvoyer sur le canal déjà réussi"

    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "publié", \
        "après republication réussie du seul canal en échec, le statut global doit passer à 'publié'"

    tentatives = {c: t for c, s, t, e, h in database.statuts_publication(newsletter_id)}
    assert tentatives["linkedin"] == 2, "republier_canal() doit incrémenter le compteur de tentatives du canal concerné"
    assert tentatives["whatsapp"] == 1, "le canal déjà réussi ne doit pas recevoir de tentative supplémentaire"


def test_aucune_newsletter_validee_ne_fait_rien(monkeypatch, tmp_path):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()

    assert publish_newsletter() == {}

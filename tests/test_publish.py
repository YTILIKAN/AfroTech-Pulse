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


# --- Comportement actuel : Telegram est le seul canal actif (email en pause, cf. database.py) ---

def test_telegram_ok_marque_publie(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: True)

    resultats = publish_newsletter()

    assert resultats == {"telegram": True}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "publié", "le seul canal actif a réussi, le statut global doit être 'publié'"


def test_telegram_ko_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: False)

    resultats = publish_newsletter()

    assert resultats == {"telegram": False}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec ne doit jamais marquer statut = publié"


def test_aucune_newsletter_validee_ne_fait_rien(monkeypatch, tmp_path):
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()

    assert publish_newsletter() == {}


# --- Couverture de la logique multicanal générique (utile pour la réactivation future d'"email") ---

def test_multicanal_ok_ko_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setattr(database, "CANAUX_PUBLICATION", ("telegram", "email"))
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: True)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "email", lambda contenu: False)

    resultats = publish_newsletter()

    assert resultats == {"telegram": True, "email": False}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec partiel ne doit jamais marquer statut = publié"

    publications = {c: s for c, s, *_ in database.statuts_publication(newsletter_id)}
    assert publications["telegram"] == "publié"
    assert publications["email"] == "echec"


def test_multicanal_ko_ko_statut_reste_valide(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setattr(database, "CANAUX_PUBLICATION", ("telegram", "email"))
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: False)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "email", lambda contenu: False)

    resultats = publish_newsletter()

    assert resultats == {"telegram": False, "email": False}
    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "validé", "un échec total ne doit jamais marquer statut = publié"


def test_republication_ciblee_ne_retouche_pas_le_canal_deja_reussi(monkeypatch, tmp_path):
    newsletter_id = _preparer_newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setattr(database, "CANAUX_PUBLICATION", ("telegram", "email"))

    appels_telegram = {"n": 0}

    def telegram_fn(contenu):
        appels_telegram["n"] += 1
        return True

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", telegram_fn)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "email", lambda contenu: False)

    publish_newsletter()
    assert appels_telegram["n"] == 1

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "email", lambda contenu: True)
    succes = republier_canal(newsletter_id, "email")

    assert succes is True
    assert appels_telegram["n"] == 1, "republier_canal() ne doit pas réenvoyer sur le canal déjà réussi"

    newsletter = database.newsletter_par_id(newsletter_id)
    assert newsletter[3] == "publié", \
        "après republication réussie du seul canal en échec, le statut global doit passer à 'publié'"

    tentatives = {c: t for c, s, t, e, h in database.statuts_publication(newsletter_id)}
    assert tentatives["email"] == 2, "republier_canal() doit incrémenter le compteur de tentatives du canal concerné"
    assert tentatives["telegram"] == 1, "le canal déjà réussi ne doit pas recevoir de tentative supplémentaire"

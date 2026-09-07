import database
import publisher.publish as publish_module
import publisher.run_publish as run_publish_module


def _newsletter_validee(monkeypatch, tmp_path):
    test_db = tmp_path / "run_publish_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()
    nid = database.sauvegarder_newsletter("# AfroTech Pulse\n\nContenu de test.", nb_articles=3)
    database.changer_statut_newsletter(nid, "en_revue", "Steve")
    database.changer_statut_newsletter(nid, "validé", "Steve")
    return nid


def test_rien_a_publier_retourne_0_sans_aucun_envoi(monkeypatch, tmp_path):
    test_db = tmp_path / "vide.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()

    def envoi_interdit(contenu):
        raise AssertionError("aucun envoi ne doit avoir lieu sans newsletter validée")

    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", envoi_interdit)

    assert run_publish_module.run() == 0


def test_succes_retourne_0_et_marque_la_newsletter_publiee(monkeypatch, tmp_path):
    nid = _newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: True)

    assert run_publish_module.run() == 0
    assert database.newsletter_par_id(nid)[3] == "publié"


def test_echec_retourne_1_statut_inchange_et_alerte_lequipe(monkeypatch, tmp_path, capsys):
    nid = _newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: False)

    alertes = []
    monkeypatch.setattr(
        run_publish_module.notifier, "envoyer_notification_equipe",
        lambda message: alertes.append(message) or True,
    )

    assert run_publish_module.run() == 1
    assert database.newsletter_par_id(nid)[3] == "validé", "un échec ne doit jamais marquer 'publié'"
    assert len(alertes) == 1
    assert "[ÉCHEC]" in capsys.readouterr().out


def test_lechec_de_publication_prime_meme_si_lalerte_equipe_echoue(monkeypatch, tmp_path):
    _newsletter_validee(monkeypatch, tmp_path)
    monkeypatch.setitem(publish_module.ENVOI_PAR_CANAL, "telegram", lambda contenu: False)

    def alerte_ko(message):
        raise RuntimeError("TELEGRAM_ADMIN_CHAT_ID manquant")

    monkeypatch.setattr(run_publish_module.notifier, "envoyer_notification_equipe", alerte_ko)

    assert run_publish_module.run() == 1, "l'échec de publication ne doit jamais être avalé"

from types import SimpleNamespace

import httpx
import pytest

import database
import notifier


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def _db_vierge(monkeypatch, tmp_path):
    test_db = tmp_path / "notifier_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    database.creer_base()


def _newsletter_brouillon(nb_articles=5):
    return database.sauvegarder_newsletter(
        "# AfroTech Pulse\n\nContenu de test.", nb_articles=nb_articles
    )


def test_rappel_envoye_quand_une_newsletter_attend_la_validation(monkeypatch, tmp_path):
    _db_vierge(monkeypatch, tmp_path)
    newsletter_id = _newsletter_brouillon(nb_articles=6)
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "-1001234567890")

    envois = []

    def post_fn(url, json):
        envois.append(json)
        return SimpleNamespace(status_code=200, text="")

    monkeypatch.setattr(notifier, "_get_client", lambda: FakeClient(post_fn))

    assert notifier.rappel_validation() is True
    assert len(envois) == 1
    texte = envois[0]["text"]
    assert str(newsletter_id) in texte
    assert "valider" in texte.lower()
    assert envois[0]["chat_id"] == "-1001234567890"


def test_aucun_rappel_ni_envoi_si_rien_a_valider(monkeypatch, tmp_path, capsys):
    _db_vierge(monkeypatch, tmp_path)
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "-1001234567890")

    def post_fn(url, json):
        raise AssertionError("aucun message ne doit partir s'il n'y a pas de brouillon")

    monkeypatch.setattr(notifier, "_get_client", lambda: FakeClient(post_fn))

    assert notifier.rappel_validation() is False
    assert "[INFO]" in capsys.readouterr().out


def test_secret_admin_manquant_leve_une_erreur_explicite(monkeypatch, tmp_path):
    _db_vierge(monkeypatch, tmp_path)
    _newsletter_brouillon()
    monkeypatch.delenv("TELEGRAM_ADMIN_CHAT_ID", raising=False)
    monkeypatch.setattr(notifier, "_get_client", lambda: FakeClient(lambda url, json: None))

    with pytest.raises(RuntimeError, match="TELEGRAM_ADMIN_CHAT_ID"):
        notifier.rappel_validation()


def test_echec_http_est_logge_et_ne_leve_pas(monkeypatch, tmp_path, capsys):
    _db_vierge(monkeypatch, tmp_path)
    _newsletter_brouillon()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "-1001234567890")

    def post_fn(url, json):
        return SimpleNamespace(status_code=403, text="Forbidden: bot was blocked")

    monkeypatch.setattr(notifier, "_get_client", lambda: FakeClient(post_fn))

    assert notifier.rappel_validation() is False
    sortie = capsys.readouterr().out
    assert "[ERREUR]" in sortie and "403" in sortie


def test_erreur_reseau_est_loggee_et_ne_leve_pas(monkeypatch, tmp_path, capsys):
    _db_vierge(monkeypatch, tmp_path)
    _newsletter_brouillon()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "-1001234567890")

    def post_fn(url, json):
        raise httpx.ConnectError("DNS resolution failed")

    monkeypatch.setattr(notifier, "_get_client", lambda: FakeClient(post_fn))

    assert notifier.rappel_validation() is False
    assert "[ERREUR]" in capsys.readouterr().out


def test_main_retourne_1_si_une_newsletter_attend_mais_lenvoi_echoue(monkeypatch, tmp_path):
    _db_vierge(monkeypatch, tmp_path)
    _newsletter_brouillon()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "-1001234567890")
    monkeypatch.setattr(
        notifier, "_get_client",
        lambda: FakeClient(lambda url, json: SimpleNamespace(status_code=500, text="boom")),
    )

    assert notifier.main() == 1


def test_main_retourne_0_si_rien_a_valider(monkeypatch, tmp_path):
    _db_vierge(monkeypatch, tmp_path)
    assert notifier.main() == 0

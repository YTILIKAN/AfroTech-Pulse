from types import SimpleNamespace

import httpx
import pytest

import database
import publisher.email_client as email_module
from publisher.email_client import envoyer_email

CONTENU = "# AfroTech Pulse\n\nContenu de test."


def fake_response(status_code, text=""):
    return SimpleNamespace(status_code=status_code, text=text)


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def _preparer_env(monkeypatch, abonnes=("test@exemple.com",)):
    monkeypatch.setenv("RESEND_FROM_EMAIL", "newsletter@ytilikan.org")
    monkeypatch.setattr(database, "lister_abonnes_actifs", lambda: list(abonnes))


def test_envoi_reussi_retourne_true(monkeypatch):
    _preparer_env(monkeypatch)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        assert json["to"] == ["test@exemple.com"]
        return fake_response(200)

    monkeypatch.setattr(email_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_email(CONTENU) is True
    assert appels["n"] == 1


def test_erreur_4xx_abandonne_immediatement(monkeypatch):
    _preparer_env(monkeypatch)
    monkeypatch.setattr(email_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(422, "Unprocessable: domain not verified")

    monkeypatch.setattr(email_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_email(CONTENU) is False
    assert appels["n"] == 1, "une erreur 4xx ne doit pas être réessayée"


def test_erreur_5xx_retry_puis_succes(monkeypatch):
    _preparer_env(monkeypatch)
    monkeypatch.setattr(email_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(503, "Service Unavailable")
        return fake_response(200)

    monkeypatch.setattr(email_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_email(CONTENU) is True
    assert appels["n"] == 3


def test_timeout_retry_puis_echec_apres_max_tentatives(monkeypatch):
    _preparer_env(monkeypatch)
    monkeypatch.setattr(email_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(email_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_email(CONTENU) is False
    assert appels["n"] == email_module.MAX_TENTATIVES


def test_expediteur_manquant_leve_runtime_error(monkeypatch):
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)
    monkeypatch.setattr(database, "lister_abonnes_actifs", lambda: ["test@exemple.com"])

    with pytest.raises(RuntimeError):
        envoyer_email(CONTENU)


def test_aucun_abonne_leve_runtime_error(monkeypatch):
    _preparer_env(monkeypatch, abonnes=())

    with pytest.raises(RuntimeError):
        envoyer_email(CONTENU)


def test_envoie_a_tous_les_abonnes_actifs_en_un_seul_appel(monkeypatch):
    _preparer_env(monkeypatch, abonnes=("a@exemple.com", "b@exemple.com", "c@exemple.com"))
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        assert json["to"] == ["a@exemple.com", "b@exemple.com", "c@exemple.com"]
        return fake_response(200)

    monkeypatch.setattr(email_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_email(CONTENU) is True
    assert appels["n"] == 1, "tous les abonnés doivent être inclus dans un seul envoi, pas un par abonné"

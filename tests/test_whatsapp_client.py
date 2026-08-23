from types import SimpleNamespace

import httpx
import pytest

import publisher.whatsapp_client as whatsapp_module
from publisher.whatsapp_client import envoyer_whatsapp

CONTENU = "# AfroTech Pulse\n\nContenu de test."


def fake_response(status_code, text=""):
    return SimpleNamespace(status_code=status_code, text=text)


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def test_envoi_reussi_retourne_true(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(200)

    monkeypatch.setattr(whatsapp_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_whatsapp(CONTENU) is True
    assert appels["n"] == 1


def test_erreur_4xx_abandonne_immediatement(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setattr(whatsapp_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(400, "Bad Request")

    monkeypatch.setattr(whatsapp_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_whatsapp(CONTENU) is False
    assert appels["n"] == 1, "une erreur 4xx ne doit pas être réessayée"


def test_erreur_5xx_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setattr(whatsapp_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(503, "Service Unavailable")
        return fake_response(200)

    monkeypatch.setattr(whatsapp_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_whatsapp(CONTENU) is True
    assert appels["n"] == 3


def test_timeout_retry_puis_echec_apres_max_tentatives(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setattr(whatsapp_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(whatsapp_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_whatsapp(CONTENU) is False
    assert appels["n"] == whatsapp_module.MAX_TENTATIVES


def test_phone_number_id_manquant_leve_runtime_error(monkeypatch):
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)

    with pytest.raises(RuntimeError):
        envoyer_whatsapp(CONTENU)

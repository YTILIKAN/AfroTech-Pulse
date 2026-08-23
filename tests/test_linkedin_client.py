from types import SimpleNamespace

import httpx
import pytest

import publisher.linkedin_client as linkedin_module
from publisher.linkedin_client import envoyer_linkedin

CONTENU = "# AfroTech Pulse\n\nContenu de test."


def fake_response(status_code, text=""):
    return SimpleNamespace(status_code=status_code, text=text)


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def test_publication_reussie_retourne_true(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORGANIZATION_URN", "urn:li:organization:12345678")
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(201)

    monkeypatch.setattr(linkedin_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_linkedin(CONTENU) is True
    assert appels["n"] == 1


def test_erreur_4xx_abandonne_immediatement(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORGANIZATION_URN", "urn:li:organization:12345678")
    monkeypatch.setattr(linkedin_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(401, "Unauthorized")

    monkeypatch.setattr(linkedin_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_linkedin(CONTENU) is False
    assert appels["n"] == 1, "une erreur 4xx ne doit pas être réessayée"


def test_erreur_5xx_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORGANIZATION_URN", "urn:li:organization:12345678")
    monkeypatch.setattr(linkedin_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(503, "Service Unavailable")
        return fake_response(201)

    monkeypatch.setattr(linkedin_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_linkedin(CONTENU) is True
    assert appels["n"] == 3


def test_timeout_retry_puis_echec_apres_max_tentatives(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORGANIZATION_URN", "urn:li:organization:12345678")
    monkeypatch.setattr(linkedin_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(linkedin_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_linkedin(CONTENU) is False
    assert appels["n"] == linkedin_module.MAX_TENTATIVES


def test_organization_urn_manquant_leve_runtime_error(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ORGANIZATION_URN", raising=False)

    with pytest.raises(RuntimeError):
        envoyer_linkedin(CONTENU)

import httpx

import publisher.publish as publish_module
from publisher.publish import publier_linkedin, publier_whatsapp


class FakeHttpClient:
    def __init__(self, post_fn):
        self._post_fn = post_fn

    def post(self, url, headers=None, json=None):
        return self._post_fn(url, headers, json)


def fake_response(status_code):
    return httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://exemple.com"))


# --- publier_whatsapp() -----------------------------------------------------

def test_publier_whatsapp_sans_token_leve_erreur(monkeypatch):
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    try:
        publier_whatsapp("contenu")
        assert False, "devrait lever RuntimeError sans WHATSAPP_TOKEN"
    except RuntimeError:
        pass


def test_publier_whatsapp_succes(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module, "_get_http_client",
                         lambda: FakeHttpClient(lambda *a, **k: fake_response(200)))
    assert publier_whatsapp("contenu") is True


def test_publier_whatsapp_erreur_4xx_abandonne_immediatement(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        return fake_response(401)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_whatsapp("contenu") is False
    assert appels["n"] == 1, "une erreur 4xx (hors 429) ne doit pas être retentée"


def test_publier_whatsapp_erreur_5xx_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(503)
        return fake_response(200)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_whatsapp("contenu") is True
    assert appels["n"] == 3


def test_publier_whatsapp_timeout_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        if appels["n"] < 2:
            raise httpx.TimeoutException("timeout")
        return fake_response(200)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_whatsapp("contenu") is True
    assert appels["n"] == 2


def test_publier_whatsapp_echec_persistant_apres_max_tentatives(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        return fake_response(500)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_whatsapp("contenu") is False
    assert appels["n"] == publish_module.MAX_TENTATIVES


# --- publier_linkedin() ------------------------------------------------------

def test_publier_linkedin_sans_token_leve_erreur(monkeypatch):
    monkeypatch.delenv("LINKEDIN_TOKEN", raising=False)
    try:
        publier_linkedin("contenu")
        assert False, "devrait lever RuntimeError sans LINKEDIN_TOKEN"
    except RuntimeError:
        pass


def test_publier_linkedin_succes(monkeypatch):
    monkeypatch.setenv("LINKEDIN_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module, "_get_http_client",
                         lambda: FakeHttpClient(lambda *a, **k: fake_response(201)))
    assert publier_linkedin("contenu") is True


def test_publier_linkedin_erreur_4xx_abandonne_immediatement(monkeypatch):
    monkeypatch.setenv("LINKEDIN_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        return fake_response(403)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_linkedin("contenu") is False
    assert appels["n"] == 1


def test_publier_linkedin_erreur_5xx_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("LINKEDIN_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        if appels["n"] < 2:
            return fake_response(502)
        return fake_response(201)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_linkedin("contenu") is True
    assert appels["n"] == 2


def test_publier_linkedin_timeout_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("LINKEDIN_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        if appels["n"] < 3:
            raise httpx.TimeoutException("timeout")
        return fake_response(201)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_linkedin("contenu") is True
    assert appels["n"] == 3


def test_publier_linkedin_echec_persistant_apres_max_tentatives(monkeypatch):
    monkeypatch.setenv("LINKEDIN_TOKEN", "faux-token")
    monkeypatch.setattr(publish_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(*a, **k):
        appels["n"] += 1
        return fake_response(429)

    monkeypatch.setattr(publish_module, "_get_http_client", lambda: FakeHttpClient(post_fn))
    assert publier_linkedin("contenu") is False
    assert appels["n"] == publish_module.MAX_TENTATIVES

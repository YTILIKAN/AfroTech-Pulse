from types import SimpleNamespace

import httpx
from mistralai.client.errors import SDKError

import pipeline.summarize as summarize_module
from pipeline.summarize import summarize_article

CONTENU_VALIDE = "Contenu suffisamment long pour passer le garde-fou de longueur minimale du script."


def fake_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeClient:
    def __init__(self, complete_fn):
        self.chat = SimpleNamespace(complete=complete_fn)


def echoue_si_appelee(**kwargs):
    raise AssertionError("l'API ne doit pas être appelée pour un contenu vide/trop court")


def erreur_sdk(status_code):
    reponse = httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.mistral.ai"))
    return SDKError("erreur", reponse)


def test_appel_reussi_retourne_le_resume_nettoye(monkeypatch):
    fake_client = FakeClient(lambda **kw: fake_response("  Ligne 1.\nLigne 2.\nLigne 3.  "))
    monkeypatch.setattr(summarize_module, "get_client", lambda: fake_client)

    resultat = summarize_article("titre", CONTENU_VALIDE)
    assert resultat == "Ligne 1.\nLigne 2.\nLigne 3."


def test_contenu_vide_retourne_none(monkeypatch):
    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(echoue_si_appelee))
    assert summarize_article("titre", "") is None


def test_contenu_trop_court_retourne_none(monkeypatch):
    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(echoue_si_appelee))
    assert summarize_article("titre", "trop court") is None


def test_summarize_gere_erreur_api_avec_retry(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        if appels["n"] < 3:
            raise erreur_sdk(429)
        return fake_response("Ligne 1.\nLigne 2.\nLigne 3.")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(complete_fn))

    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat == "Ligne 1.\nLigne 2.\nLigne 3."
    assert appels["n"] == 3


def test_summarize_erreur_api_non_retryable_abandonne_immediatement(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        raise erreur_sdk(500)

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(complete_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None
    assert appels["n"] == 1


def test_summarize_abandonne_apres_max_tentatives_si_rate_limit_persiste(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        raise erreur_sdk(429)

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(complete_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None
    assert appels["n"] == summarize_module.MAX_TENTATIVES

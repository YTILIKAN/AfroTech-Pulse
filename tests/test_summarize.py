from types import SimpleNamespace

import httpx

import pipeline.summarize as summarize_module
from pipeline.summarize import summarize_article

CONTENU_VALIDE = "Contenu suffisamment long pour passer le garde-fou de longueur minimale du script."


def fake_response(status_code, texte_genere=None, text=""):
    json_data = None
    if texte_genere is not None:
        json_data = {"candidates": [{"content": {"parts": [{"text": texte_genere}]}}]}
    return SimpleNamespace(status_code=status_code, text=text, json=lambda: json_data)


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def echoue_si_appelee(url, json):
    raise AssertionError("l'API ne doit pas être appelée pour un contenu vide/trop court")


def test_appel_reussi_retourne_le_resume_nettoye(monkeypatch):
    def post_fn(url, json):
        return fake_response(200, "  Ligne 1.\nLigne 2.\nLigne 3.  ")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

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

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(429)
        return fake_response(200, "Ligne 1.\nLigne 2.\nLigne 3.")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat == "Ligne 1.\nLigne 2.\nLigne 3."
    assert appels["n"] == 3


def test_summarize_erreur_api_non_retryable_abandonne_immediatement(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(400, text="Bad Request")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None
    assert appels["n"] == 1


def test_summarize_erreur_serveur_est_reessayee(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 2:
            return fake_response(503)
        return fake_response(200, "Ligne 1.\nLigne 2.\nLigne 3.")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    assert summarize_article("titre", CONTENU_VALIDE) == "Ligne 1.\nLigne 2.\nLigne 3."
    assert appels["n"] == 2


def test_summarize_timeout_est_reessaye(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None
    assert appels["n"] == summarize_module.MAX_TENTATIVES


def test_summarize_reponse_sans_candidats_ne_plante_pas(monkeypatch):
    """Gemini peut renvoyer 200 avec 'candidates' vide (ex. contenu bloqué par un filtre
    de sécurité) — ça ne doit jamais faire planter avec un IndexError."""

    def post_fn(url, json):
        return SimpleNamespace(status_code=200, text="", json=lambda: {"candidates": []})

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None


def test_summarize_abandonne_apres_max_tentatives_si_rate_limit_persiste(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(429)

    monkeypatch.setattr(summarize_module, "get_client", lambda: FakeClient(post_fn))

    assert summarize_article("titre", CONTENU_VALIDE) is None
    assert appels["n"] == summarize_module.MAX_TENTATIVES

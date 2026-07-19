from types import SimpleNamespace

import httpx

import pipeline.summarize as summarize_module
from pipeline.summarize import summarize_article
from mistralai.client.errors import SDKError

CONTENU_VALIDE = "Contenu suffisamment long pour passer le garde-fou de longueur minimale du script."


def fake_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def fake_sdk_error(status_code):
    raw_response = httpx.Response(status_code, request=httpx.Request("POST", "https://fake.test"))
    return SDKError("erreur simulée", raw_response)


def test_contenu_vide_retourne_none_sans_appeler_lapi(monkeypatch):
    def echoue_si_appelee(**kwargs):
        raise AssertionError("l'API ne doit pas être appelée pour un contenu vide")

    monkeypatch.setattr(summarize_module.client.chat, "complete", echoue_si_appelee)
    assert summarize_article("titre", "") is None


def test_contenu_trop_court_retourne_none_sans_appeler_lapi(monkeypatch):
    def echoue_si_appelee(**kwargs):
        raise AssertionError("l'API ne doit pas être appelée pour un contenu trop court")

    monkeypatch.setattr(summarize_module.client.chat, "complete", echoue_si_appelee)
    assert summarize_article("titre", "trop court") is None


def test_appel_reussi_retourne_le_resume_nettoye(monkeypatch):
    monkeypatch.setattr(
        summarize_module.client.chat, "complete",
        lambda **kw: fake_response("  Ligne 1.\nLigne 2.\nLigne 3.  "),
    )
    resultat = summarize_article("titre", CONTENU_VALIDE)
    assert resultat == "Ligne 1.\nLigne 2.\nLigne 3."


def test_titre_et_contenu_transmis_dans_le_message_utilisateur(monkeypatch):
    captured = {}

    def fake_complete(**kwargs):
        captured.update(kwargs)
        return fake_response("resume")

    monkeypatch.setattr(summarize_module.client.chat, "complete", fake_complete)
    summarize_article("Mon Titre Unique", CONTENU_VALIDE)

    messages = captured["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Mon Titre Unique" in messages[1]["content"]
    assert CONTENU_VALIDE in messages[1]["content"]


def test_retry_sur_rate_limit_puis_succes(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda s: None)
    reponses = [fake_sdk_error(429), fake_sdk_error(429), fake_response("résumé final")]

    def fake_complete(**kwargs):
        r = reponses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(summarize_module.client.chat, "complete", fake_complete)
    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat == "résumé final"
    assert reponses == [], "les 3 tentatives doivent avoir été consommées"


def test_abandon_apres_max_tentatives_sur_rate_limit(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda s: None)
    nb_appels = {"count": 0}

    def fake_complete(**kwargs):
        nb_appels["count"] += 1
        raise fake_sdk_error(429)

    monkeypatch.setattr(summarize_module.client.chat, "complete", fake_complete)
    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat is None
    assert nb_appels["count"] == 3, "doit tenter exactement 3 fois avant d'abandonner"


def test_timeout_retry_puis_abandon(monkeypatch):
    monkeypatch.setattr(summarize_module.time, "sleep", lambda s: None)
    nb_appels = {"count": 0}

    def fake_complete(**kwargs):
        nb_appels["count"] += 1
        raise httpx.TimeoutException("timeout simulé")

    monkeypatch.setattr(summarize_module.client.chat, "complete", fake_complete)
    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat is None
    assert nb_appels["count"] == 3


def test_erreur_non_retryable_abandonne_immediatement(monkeypatch):
    nb_appels = {"count": 0}

    def fake_complete(**kwargs):
        nb_appels["count"] += 1
        raise fake_sdk_error(401)

    monkeypatch.setattr(summarize_module.client.chat, "complete", fake_complete)
    resultat = summarize_article("titre", CONTENU_VALIDE)

    assert resultat is None
    assert nb_appels["count"] == 1, "une erreur non-429 ne doit pas être retentée"


def test_system_prompt_contient_les_contraintes_cles():
    texte = summarize_module.SYSTEM_PROMPT.lower()
    assert "3 lignes" in texte
    assert "français" in texte
    assert "afric" in texte
    assert "invente" in texte

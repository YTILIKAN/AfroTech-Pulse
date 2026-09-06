from types import SimpleNamespace

import httpx
import pytest

import publisher.telegram_client as telegram_module
from publisher.telegram_client import envoyer_telegram

CONTENU = "# AfroTech Pulse\n\nContenu de test."


def fake_response(status_code, text=""):
    return SimpleNamespace(status_code=status_code, text=text)


class FakeClient:
    def __init__(self, post_fn):
        self.post = post_fn


def test_envoi_reussi_retourne_true(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(CONTENU) is True
    assert appels["n"] == 1


def test_erreur_4xx_abandonne_immediatement(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    monkeypatch.setattr(telegram_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        return fake_response(400, "Bad Request: can't parse entities")

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(CONTENU) is False
    assert appels["n"] == 1, "une erreur 4xx ne doit pas être réessayée"


def test_erreur_5xx_retry_puis_succes(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    monkeypatch.setattr(telegram_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        if appels["n"] < 3:
            return fake_response(503, "Service Unavailable")
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(CONTENU) is True
    assert appels["n"] == 3


def test_timeout_retry_puis_echec_apres_max_tentatives(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    monkeypatch.setattr(telegram_module.time, "sleep", lambda _: None)
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(CONTENU) is False
    assert appels["n"] == telegram_module.MAX_TENTATIVES


def test_channel_id_manquant_leve_runtime_error(monkeypatch):
    monkeypatch.delenv("TELEGRAM_CHANNEL_ID", raising=False)

    with pytest.raises(RuntimeError):
        envoyer_telegram(CONTENU)


def test_contenu_long_est_decoupe_en_plusieurs_messages(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    contenu_long = "Paragraphe de test suffisamment long.\n\n" * 200
    appels = {"n": 0}

    def post_fn(url, json):
        appels["n"] += 1
        assert len(json["text"]) <= telegram_module.LIMITE_CARACTERES_TELEGRAM
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(contenu_long) is True
    assert appels["n"] > 1, "un contenu de plus de 4096 caractères doit être envoyé en plusieurs messages"


def test_decoupe_ne_coupe_pas_au_milieu_dune_balise_html():
    texte_avant = "x" * (telegram_module.LIMITE_CARACTERES_TELEGRAM - 30)
    lien = '<a href="https://exemple.com/article">Lire l\'article complet</a>'
    contenu = texte_avant + lien + "y" * 200

    morceaux = telegram_module._decouper_message(contenu)

    assert len(morceaux) > 1
    for morceau in morceaux:
        assert morceau.count("<a") == morceau.count("</a>"), (
            "un morceau ne doit jamais contenir une balise <a> ouverte sans sa fermeture "
            "— Telegram rejette un message HTML mal formé"
        )


def test_get_client_ne_met_pas_en_cache_un_token_perime(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-initial")
    client_1 = telegram_module.get_client()
    assert "token-initial" in str(client_1.base_url)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-mis-a-jour")
    client_2 = telegram_module.get_client()
    assert "token-mis-a-jour" in str(client_2.base_url), (
        "get_client() ne doit jamais renvoyer un client construit avec un token périmé mis en cache"
    )


def test_titre_avec_esperluette_reste_une_entite_html_valide(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    contenu = "## Fintech & Santé"
    textes_envoyes = []

    def post_fn(url, json):
        textes_envoyes.append(json["text"])
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(contenu) is True
    # Le "&" doit rester "&amp;" (minuscule, entité valide), pas "&AMP;" produit si .upper()
    # est appliqué après l'échappement HTML.
    assert "<b>FINTECH &amp; SANTÉ</b>" in textes_envoyes[0]
    assert "&AMP;" not in textes_envoyes[0]


def test_les_titres_sont_convertis_en_gras_html(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    contenu = "## Édito\nUn texte d'intro.\n\n### 1. Un article\nUn résumé."
    textes_envoyes = []

    def post_fn(url, json):
        textes_envoyes.append(json["text"])
        assert json["parse_mode"] == "HTML"
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(contenu) is True
    texte = textes_envoyes[0]
    assert "<b>ÉDITO</b>" in texte
    assert "<b>1. Un article</b>" in texte
    assert "##" not in texte and "###" not in texte


def test_les_liens_deviennent_cliquables(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    contenu = "Un résumé.\nLien : https://exemple.com/article"
    textes_envoyes = []

    def post_fn(url, json):
        textes_envoyes.append(json["text"])
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(contenu) is True
    assert '<a href="https://exemple.com/article">Lire l\'article complet</a>' in textes_envoyes[0]


def test_caracteres_html_speciaux_sont_echappes(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan")
    contenu = "Une startup <Fintech> & Co lève des fonds."
    textes_envoyes = []

    def post_fn(url, json):
        textes_envoyes.append(json["text"])
        return fake_response(200)

    monkeypatch.setattr(telegram_module, "get_client", lambda: FakeClient(post_fn))

    assert envoyer_telegram(contenu) is True
    assert textes_envoyes[0] == "Une startup &lt;Fintech&gt; &amp; Co lève des fonds."

from types import SimpleNamespace

import httpx
from mistralai.client.errors import SDKError

import newsletter.writer as writer_module
from newsletter.writer import compter_articles, generer_newsletter, structure_respectee


def fake_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeClient:
    def __init__(self, complete_fn):
        self.chat = SimpleNamespace(complete=complete_fn)


def echoue_si_appelee(**kwargs):
    raise AssertionError("l'API ne doit pas être appelée sans article à traiter")


def erreur_sdk(status_code):
    reponse = httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://api.mistral.ai"))
    return SDKError("erreur", reponse)


def fabriquer_articles(n):
    return [
        {
            "titre": f"Article {i}",
            "url": f"https://exemple.com/article-{i}",
            "resume": f"Résumé factice de l'article {i}.",
        }
        for i in range(1, n + 1)
    ]


def fabriquer_newsletter_bien_formee(n):
    blocs = "\n\n".join(
        f"### {i}. Article {i}\nRésumé factice de l'article {i}.\nLien : https://exemple.com/article-{i}"
        for i in range(1, n + 1)
    )
    return (
        "## Édito\n"
        "Une semaine riche en actualités pour la tech africaine.\n\n"
        "## Cette semaine\n"
        f"{blocs}\n\n"
        "## Conclusion\n"
        "Rendez-vous la semaine prochaine pour une nouvelle édition."
    )


def test_structure_respectee_avec_5_articles(monkeypatch):
    newsletter = fabriquer_newsletter_bien_formee(5)
    monkeypatch.setattr(
        writer_module, "get_client", lambda: FakeClient(lambda **kw: fake_response(newsletter))
    )

    resultat = generer_newsletter(fabriquer_articles(5))

    assert resultat == newsletter
    assert compter_articles(resultat) == 5
    assert structure_respectee(resultat, 5)


def test_structure_respectee_avec_7_articles(monkeypatch):
    newsletter = fabriquer_newsletter_bien_formee(7)
    monkeypatch.setattr(
        writer_module, "get_client", lambda: FakeClient(lambda **kw: fake_response(newsletter))
    )

    resultat = generer_newsletter(fabriquer_articles(7))

    assert resultat == newsletter
    assert compter_articles(resultat) == 7
    assert structure_respectee(resultat, 7)


def test_structure_non_respectee_si_section_manquante():
    newsletter_sans_conclusion = (
        "## Édito\nUne intro.\n\n"
        "## Cette semaine\n"
        "### 1. Article 1\nRésumé.\nLien : https://exemple.com/1"
    )
    assert not structure_respectee(newsletter_sans_conclusion, 1)


def test_structure_non_respectee_si_nombre_articles_incorrect():
    newsletter_incomplete = fabriquer_newsletter_bien_formee(4)
    assert not structure_respectee(newsletter_incomplete, 5)


def test_generer_newsletter_retourne_le_texte_meme_si_structure_incorrecte(monkeypatch):
    newsletter_incomplete = fabriquer_newsletter_bien_formee(4)
    monkeypatch.setattr(
        writer_module, "get_client", lambda: FakeClient(lambda **kw: fake_response(newsletter_incomplete))
    )

    resultat = generer_newsletter(fabriquer_articles(5))

    assert resultat == newsletter_incomplete


def test_liste_vide_ne_plante_pas():
    assert generer_newsletter([]) is None


def test_liste_vide_n_appelle_pas_l_api(monkeypatch):
    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(echoue_si_appelee))
    assert generer_newsletter([]) is None


def test_generer_newsletter_gere_erreur_api_avec_retry(monkeypatch):
    monkeypatch.setattr(writer_module.time, "sleep", lambda _: None)
    newsletter = fabriquer_newsletter_bien_formee(3)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        if appels["n"] < 3:
            raise erreur_sdk(429)
        return fake_response(newsletter)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(complete_fn))

    resultat = generer_newsletter(fabriquer_articles(3))

    assert resultat == newsletter
    assert appels["n"] == 3


def test_generer_newsletter_gere_timeout_avec_retry(monkeypatch):
    monkeypatch.setattr(writer_module.time, "sleep", lambda _: None)
    newsletter = fabriquer_newsletter_bien_formee(2)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        if appels["n"] < 2:
            raise httpx.TimeoutException("timeout")
        return fake_response(newsletter)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(complete_fn))

    resultat = generer_newsletter(fabriquer_articles(2))

    assert resultat == newsletter
    assert appels["n"] == 2


def test_erreur_api_non_retryable_abandonne_immediatement(monkeypatch):
    monkeypatch.setattr(writer_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        raise erreur_sdk(500)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(complete_fn))

    assert generer_newsletter(fabriquer_articles(3)) is None
    assert appels["n"] == 1


def test_abandonne_apres_max_tentatives_si_rate_limit_persiste(monkeypatch):
    monkeypatch.setattr(writer_module.time, "sleep", lambda _: None)

    appels = {"n": 0}

    def complete_fn(**kwargs):
        appels["n"] += 1
        raise erreur_sdk(429)

    monkeypatch.setattr(writer_module, "get_client", lambda: FakeClient(complete_fn))

    assert generer_newsletter(fabriquer_articles(3)) is None
    assert appels["n"] == writer_module.MAX_TENTATIVES

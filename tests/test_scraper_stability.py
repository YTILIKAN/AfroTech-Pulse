"""[S14] scrape_rss() est le point d'entrée réseau appelé une fois par source à chaque
run de daily_scrape.yml (50+ sources, 365 runs/an) : une source qui timeout, coupe la
connexion ou renvoie un flux cassé ne doit jamais faire planter la collecte des autres
sources. Ces tests couvrent chaque branche d'erreur — jusqu'ici non testée."""

import httpx
import requests

import scraper.main as scraper_module
from scraper.main import scrape_rss

SOURCE = {
    "id": "source-instable",
    "name": "Source Instable",
    "category": "startup",
    "url": "http://source-instable.example/rss",
}

FLUX_RSS_VALIDE = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Une startup africaine leve des fonds</title>
  <link>https://exemple.com/article-1</link>
  <description>Resume de l'article.</description>
  <pubDate>Mon, 01 Sep 2026 08:00:00 GMT</pubDate>
</item>
</channel></rss>
"""


def _fake_response(content):
    return httpx.Response(200, content=content, request=httpx.Request("GET", SOURCE["url"]))


def test_scrape_rss_survit_a_un_timeout(monkeypatch, capsys):
    def get_qui_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("le serveur ne répond pas")

    monkeypatch.setattr(scraper_module.requests, "get", get_qui_timeout)

    assert scrape_rss(SOURCE) == []
    assert "TIMEOUT" in capsys.readouterr().out, "un timeout doit être loggé, pas silencieux"


def test_scrape_rss_survit_a_une_erreur_reseau(monkeypatch, capsys):
    def get_qui_echoue(*args, **kwargs):
        raise requests.exceptions.ConnectionError("DNS introuvable")

    monkeypatch.setattr(scraper_module.requests, "get", get_qui_echoue)

    assert scrape_rss(SOURCE) == []
    assert "ERREUR RÉSEAU" in capsys.readouterr().out


def test_scrape_rss_survit_a_une_erreur_http(monkeypatch, capsys):
    class FakeResponse:
        status_code = 503

        def raise_for_status(self):
            erreur = requests.exceptions.HTTPError("503 Server Error")
            erreur.response = self
            raise erreur

    monkeypatch.setattr(scraper_module.requests, "get", lambda *a, **k: FakeResponse())

    assert scrape_rss(SOURCE) == []
    assert "ERREUR HTTP 503" in capsys.readouterr().out


def test_scrape_rss_survit_a_un_flux_vide_ou_non_reconnu(monkeypatch, capsys):
    class FakeResponse:
        status_code = 200
        content = b"<html>pas un flux RSS</html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(scraper_module.requests, "get", lambda *a, **k: FakeResponse())

    assert scrape_rss(SOURCE) == []
    assert "VIDE" in capsys.readouterr().out


def test_scrape_rss_survit_a_une_exception_inattendue(monkeypatch, capsys):
    def get_qui_explose(*args, **kwargs):
        raise ValueError("erreur imprévue de parsing")

    monkeypatch.setattr(scraper_module.requests, "get", get_qui_explose)

    assert scrape_rss(SOURCE) == []
    assert "ERREUR INCONNUE" in capsys.readouterr().out


def test_scrape_rss_extrait_bien_les_articles_quand_le_flux_est_valide(monkeypatch):
    class FakeResponse:
        status_code = 200
        content = FLUX_RSS_VALIDE

        def raise_for_status(self):
            pass

    monkeypatch.setattr(scraper_module.requests, "get", lambda *a, **k: FakeResponse())

    articles = scrape_rss(SOURCE)

    assert len(articles) == 1
    assert articles[0]["url"] == "https://exemple.com/article-1"
    assert articles[0]["source_id"] == "source-instable"


def test_une_source_en_echec_ninterrompt_pas_la_collecte_des_suivantes(monkeypatch):
    """Une seule source qui timeout ne doit pas empêcher load_sources()+scrape_rss() de
    traiter le reste — c'est cette boucle (scraper/main.main() et orchestrator.run())
    qui protège la collecte quotidienne d'une seule source instable parmi 50+."""
    sources = [
        {**SOURCE, "id": "source-ko", "url": "http://ko.example/rss"},
        {**SOURCE, "id": "source-ok", "url": "http://ok.example/rss"},
    ]

    class FakeResponseOK:
        status_code = 200
        content = FLUX_RSS_VALIDE

        def raise_for_status(self):
            pass

    def get_selon_url(url, *args, **kwargs):
        if "ko.example" in url:
            raise requests.exceptions.ConnectionError("indisponible")
        return FakeResponseOK()

    monkeypatch.setattr(scraper_module.requests, "get", get_selon_url)

    resultats = {s["id"]: scrape_rss(s) for s in sources}

    assert resultats["source-ko"] == []
    assert len(resultats["source-ok"]) == 1

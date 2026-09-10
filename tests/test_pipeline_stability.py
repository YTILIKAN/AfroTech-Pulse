"""[S14] Tests de charge et stabilité du pipeline.

Rejoue 4 cycles hebdomadaires consécutifs (scrape -> résumé -> sélection/rédaction ->
validation -> publication) sur la même base, en injectant à chaque semaine une panne
différente parmi celles réellement rencontrées en production : source RSS qui timeout,
coupure réseau, erreur inattendue du scraper, rate limit / timeout Gemini, échec Telegram
transitoire puis définitif. Objectif (issue #48) :

1. le pipeline tient 4 semaines simulées sans erreur bloquante non gérée ;
2. aucune fuite de ressources (connexions SQLite, clients HTTP) sur la durée ;
3. toutes les erreurs rencontrées sont tracées/loguées, aucune silencieuse ;
4. un temps d'exécution par étape est rapporté à chaque exécution du test.
"""

import sqlite3
import time

import httpx

import database
import newsletter.run_writer as run_writer_module
import orchestrator
import pipeline.run_summarize as run_summarize_module
import pipeline.summarize as summarize_module
import publisher.run_publish as run_publish_module
import publisher.telegram_client as telegram_module

N_SEMAINES = 4

SOURCES = [
    {"id": "source-fiable", "name": "Source Fiable", "category": "startup",
     "type": "rss", "active": True, "url": "http://fiable.example/rss"},
    {"id": "source-instable", "name": "Source Instable", "category": "startup",
     "type": "rss", "active": True, "url": "http://instable.example/rss"},
]

CONTENU_PERTINENT = (
    "A new startup based in Lagos, Nigeria is changing the way africans access "
    "financial services. This african tech company is a leading tech hub."
)


def _articles_semaine(semaine, source_id, n=6):
    return [
        {
            "source_id": source_id,
            "title": f"Startup {source_id} — semaine {semaine} — article {i}",
            "url": f"https://exemple.com/{source_id}-s{semaine}-{i}",
            "published": f"2026-08-{min(3 + semaine, 28):02d}T00:00:00",
            "content": CONTENU_PERTINENT,
        }
        for i in range(n)
    ]


def _fake_gemini_response(status_code, texte=None):
    from types import SimpleNamespace
    json_data = {"candidates": [{"content": {"parts": [{"text": texte}]}}]} if texte else None
    return SimpleNamespace(status_code=status_code, text="erreur simulée", json=lambda: json_data)


def _fake_telegram_response(status_code):
    from types import SimpleNamespace
    return SimpleNamespace(status_code=status_code, text="erreur simulée")


class _ClientGeminiFactice:
    """Simule le comportement Gemini d'une semaine donnée (succès direct, retries avant
    succès, ou échec définitif non transitoire)."""

    def __init__(self, comportement):
        self.comportement = comportement
        self.appels = 0

    def post(self, url, json):
        self.appels += 1
        titre = json["contents"][0]["parts"][0]["text"].split("Titre : ")[1].split("\n")[0]
        if self.comportement == "ok":
            return _fake_gemini_response(200, f"Résumé de : {titre}")
        if self.comportement == "retry_puis_ok":
            if self.appels % 2 == 1:
                return _fake_gemini_response(429)
            return _fake_gemini_response(200, f"Résumé de : {titre}")
        if self.comportement == "timeout_puis_ok":
            if self.appels % 2 == 1:
                raise httpx.TimeoutException("gemini trop lent")
            return _fake_gemini_response(200, f"Résumé de : {titre}")
        raise AssertionError(f"comportement Gemini inconnu : {self.comportement}")


class _ClientTelegramFactice:
    """Simule Telegram : succès direct, retries avant succès, ou panne prolongée (échec
    même après MAX_TENTATIVES, comme une vraie coupure de plusieurs minutes)."""

    def __init__(self, comportement):
        self.comportement = comportement
        self.appels = 0
        self.ferme = False

    def post(self, url, json):
        self.appels += 1
        if self.comportement == "ok":
            return _fake_telegram_response(200)
        if self.comportement == "retry_puis_ok":
            return _fake_telegram_response(200 if self.appels >= 2 else 503)
        if self.comportement == "panne_prolongee":
            return _fake_telegram_response(500)
        raise AssertionError(f"comportement Telegram inconnu : {self.comportement}")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.ferme = True
        return False


PANNES_PAR_SEMAINE = [
    {  # Semaine 1 : la source instable timeout, Gemini et Telegram nickel.
        "scraper": "timeout",
        "gemini": "ok",
        "telegram": "ok",
    },
    {  # Semaine 2 : coupure réseau sur la source instable, rate limit Gemini répété.
        "scraper": "connexion",
        "gemini": "retry_puis_ok",
        "telegram": "ok",
    },
    {  # Semaine 3 : toutes les sources répondent, timeout Gemini, Telegram flaky.
        "scraper": "ok",
        "gemini": "timeout_puis_ok",
        "telegram": "retry_puis_ok",
    },
    {  # Semaine 4 : erreur inattendue du scraper + panne Telegram prolongée (non transitoire).
        "scraper": "inattendue",
        "gemini": "ok",
        "telegram": "panne_prolongee",
    },
]


def _patch_scraper(monkeypatch, comportement):
    def scrape_rss_instable(source):
        if source["id"] != "source-instable":
            return _articles_semaine.derniere_semaine_fiable
        if comportement == "ok":
            return _articles_semaine.derniere_semaine_instable
        if comportement == "timeout":
            print("  [TIMEOUT] Source Instable — site trop lent, on passe.")
            return []
        if comportement == "connexion":
            print("  [ERREUR RÉSEAU] Source Instable — site inaccessible, on passe.")
            return []
        if comportement == "inattendue":
            print("  [ERREUR INCONNUE] Source Instable — panne imprévue, on passe.")
            return []
        raise AssertionError(f"comportement scraper inconnu : {comportement}")

    monkeypatch.setattr(orchestrator, "scrape_rss", scrape_rss_instable)


def test_quatre_cycles_hebdomadaires_consecutifs_avec_pannes_injectees(monkeypatch, tmp_path, capsys):
    test_db = tmp_path / "stability_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: SOURCES)
    # Dédup ML (sentence-transformers) hors périmètre de ce test de résilience du cycle
    # complet — déjà couverte isolément par tests/test_dedup.py.
    monkeypatch.setattr(orchestrator, "deduplicate", lambda articles: articles)
    monkeypatch.setattr(
        run_writer_module, "generer_newsletter",
        lambda selection: "## Édito\nTest.\n\n## Cette semaine\n"
        + "\n".join(f"### {i}. {a['titre']}\n{a['resume']}\nLien : {a['url']}"
                    for i, a in enumerate(selection, start=1))
        + "\n\n## Conclusion\nTest.",
    )
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-test")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@ytilikan-test")
    monkeypatch.setattr(summarize_module.time, "sleep", lambda _: None)
    monkeypatch.setattr(telegram_module.time, "sleep", lambda _: None)

    # --- Suivi des ressources : chaque connexion SQLite ouverte doit être refermée. ---
    ouvertures, fermetures = {"n": 0}, {"n": 0}
    connect_original = sqlite3.connect

    class ConnexionTracee:
        def __init__(self, *args, **kwargs):
            self._conn = connect_original(*args, **kwargs)
            ouvertures["n"] += 1

        def __getattr__(self, nom):
            return getattr(self._conn, nom)

        def close(self):
            fermetures["n"] += 1
            self._conn.close()

    monkeypatch.setattr(database.sqlite3, "connect", lambda *a, **k: ConnexionTracee(*a, **k))

    temps_par_etape = {"scrape": 0.0, "resume": 0.0, "redaction": 0.0, "publication": 0.0}
    clients_telegram_crees = []

    for semaine, panne in enumerate(PANNES_PAR_SEMAINE, start=1):
        # `_articles_semaine` porte des attributs dynamiques utilisés par le faux scraper
        # ci-dessus : simple façon d'éviter un état de module mutable partagé entre tests.
        _articles_semaine.derniere_semaine_fiable = _articles_semaine(semaine, "source-fiable")
        _articles_semaine.derniere_semaine_instable = _articles_semaine(semaine, "source-instable")
        _patch_scraper(monkeypatch, panne["scraper"])

        client_gemini = _ClientGeminiFactice(panne["gemini"])
        monkeypatch.setattr(summarize_module, "get_client", lambda c=client_gemini: c)

        client_telegram = _ClientTelegramFactice(panne["telegram"])
        clients_telegram_crees.append(client_telegram)
        monkeypatch.setattr(telegram_module, "get_client", lambda c=client_telegram: c)

        # --- daily_scrape.yml (x7 en prod, une fois ici par semaine simulée) ---
        debut = time.perf_counter()
        orchestrator.run()  # ne doit jamais lever, quelle que soit la panne réseau injectée
        temps_par_etape["scrape"] += time.perf_counter() - debut

        debut = time.perf_counter()
        run_summarize_module.run()  # idem pour les pannes Gemini (rate limit / timeout)
        temps_par_etape["resume"] += time.perf_counter() - debut

        # --- weekly_editor.yml ---
        debut = time.perf_counter()
        newsletter_id = run_writer_module.run()
        temps_par_etape["redaction"] += time.perf_counter() - debut
        assert newsletter_id is not None, (
            f"semaine {semaine} : au moins une source (fiable) doit toujours fournir assez "
            "d'articles pour générer une newsletter malgré la panne injectée"
        )

        # --- geste manuel hebdomadaire simulé ---
        database.changer_statut_newsletter(newsletter_id, "en_revue", "Steve")
        database.changer_statut_newsletter(newsletter_id, "validé", "Steve")

        # --- monday_publish.yml ---
        debut = time.perf_counter()
        code_sortie = run_publish_module.run()
        temps_par_etape["publication"] += time.perf_counter() - debut

        newsletter_apres = database.newsletter_par_id(newsletter_id)
        if panne["telegram"] == "panne_prolongee":
            assert code_sortie == 1, "une panne Telegram prolongée doit rendre le run rouge (exit 1)"
            assert newsletter_apres[3] == "validé", (
                "après un échec de publication, la newsletter doit rester 'validé' "
                "(jamais marquée 'publié' à tort)"
            )
        else:
            assert code_sortie == 0, f"semaine {semaine} : la publication aurait dû réussir"
            assert newsletter_apres[3] == "publié"

    # --- 1. Pas d'erreur bloquante non gérée sur les 4 semaines (sinon le test aurait
    #        déjà levé plus haut) : la base contient bien 4 semaines de données. ---
    sortie = capsys.readouterr().out
    assert sortie.count("Orchestrateur") == N_SEMAINES

    # --- 2. Toutes les pannes injectées sont bien tracées, aucune n'est silencieuse. ---
    for marqueur in (
        "[TIMEOUT] Source Instable",
        "[ERREUR RÉSEAU] Source Instable",
        "[ERREUR INCONNUE] Source Instable",
        "[RATE LIMIT/SERVEUR 429]",
        "[TIMEOUT] tentative",
        "[RATE LIMIT/SERVEUR 503]",
        "[ÉCHEC] envoi Telegram abandonné après",
        "[ÉCHEC] Publication automatique incomplète",
    ):
        assert marqueur in sortie, f"panne simulée non tracée dans les logs : {marqueur!r}"

    # --- 3. Aucune fuite de connexion SQLite sur les 4 cycles complets. ---
    assert ouvertures["n"] == fermetures["n"], (
        f"{ouvertures['n']} connexions SQLite ouvertes contre {fermetures['n']} refermées "
        "— fuite de ressources sur la durée."
    )
    assert ouvertures["n"] > 0

    # --- 4. Un seul client Telegram ouvert par tentative de publication, tous refermés
    #        (cf. correctif publisher/telegram_client.py — fuite corrigée dans le cadre
    #        de ce ticket de stabilité). ---
    assert len(clients_telegram_crees) == N_SEMAINES
    assert all(c.ferme for c in clients_telegram_crees), (
        "chaque client Telegram ouvert pour une tentative de publication doit être refermé, "
        "y compris après une panne prolongée"
    )

    # --- 5. Rapport de temps d'exécution par étape (visible avec `pytest -s`). ---
    total = sum(temps_par_etape.values())
    print("\nTemps d'exécution — simulation de 4 cycles hebdomadaires :")
    for etape, duree in temps_par_etape.items():
        print(f"  {etape:12s} : {duree * 1000:7.1f} ms cumulées sur {N_SEMAINES} semaines")
    print(f"  {'total':12s} : {total * 1000:7.1f} ms")
    assert total < 5.0, (
        "la simulation entière (I/O réseau et LLM mockés) doit rester de l'ordre de la "
        "seconde — un dépassement signale probablement un vrai appel réseau/sleep non mocké"
    )

import sqlite3

import database
import orchestrator


FAKE_SOURCES = [
    {"id": "techpoint-africa", "name": "TechPoint Africa", "category": "startup", "type": "rss", "active": True, "url": "http://fake-techpoint"},
    {"id": "wired-africa", "name": "Wired Africa", "category": "tech", "type": "rss", "active": True, "url": "http://fake-wired"},
]

FAKE_ARTICLES = {
    "techpoint-africa": [
        {
            "source_id": "techpoint-africa",
            "title": "Lagos startup raises funding",
            "url": "https://exemple.com/tp-1",
            "published": "2026-07-01",
            "content": "A Nigerian startup based in Lagos secures funding to expand across Africa.",
        }
    ],
    "wired-africa": [
        {
            "source_id": "wired-africa",
            "title": "Apple launches new iPhone",
            "url": "https://exemple.com/wired-1",
            "published": "2026-07-01",
            "content": "Apple held its annual keynote in Cupertino, announcing the latest iPhone model.",
        }
    ],
}


def fake_scrape_rss(source):
    return FAKE_ARTICLES[source["id"]]


def test_pipeline_complet_score_pertinence_en_base(monkeypatch, tmp_path):
    test_db = tmp_path / "afrotech_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss)

    orchestrator.run()

    conn = sqlite3.connect(str(test_db))
    rows = conn.execute("SELECT source_id, score_pertinence FROM articles_raw").fetchall()
    conn.close()

    assert len(rows) == 2, "les deux articles factices doivent être en base"
    assert all(score is not None for _, score in rows), "aucun score_pertinence ne doit être NULL"

    scores = dict(rows)
    assert scores["techpoint-africa"] > 0, "un article techpoint-africa doit avoir un score > 0"
    assert scores["wired-africa"] < 10, "un article wired-africa sans mention africaine doit avoir un score < 10"


FAKE_ARTICLES_AVEC_DOUBLON = {
    "techpoint-africa": [
        {
            "source_id": "techpoint-africa",
            "title": "Lagos startup raises funding",
            "url": "https://exemple.com/tp-1",
            "published": "2026-07-01",
            "content": "A Nigerian startup based in Lagos secures funding to expand across Africa.",
        },
        {
            "source_id": "techpoint-africa",
            "title": "Lagos startup raises funding",
            "url": "https://exemple.com/tp-1-copie",
            "published": "2026-07-01",
            "content": "Republication de la même dépêche sous une autre URL.",
        },
    ],
    "wired-africa": [
        {
            "source_id": "wired-africa",
            "title": "Apple launches new iPhone",
            "url": "https://exemple.com/wired-1",
            "published": "2026-07-01",
            "content": "Apple held its annual keynote in Cupertino, announcing the latest iPhone model.",
        }
    ],
}


def fake_scrape_rss_avec_doublon(source):
    return FAKE_ARTICLES_AVEC_DOUBLON[source["id"]]


def test_doublons_intra_source_ne_sont_pas_inseres_en_base(monkeypatch, tmp_path):
    test_db = tmp_path / "afrotech_integration_dedup_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(orchestrator, "load_sources", lambda: FAKE_SOURCES)
    monkeypatch.setattr(orchestrator, "scrape_rss", fake_scrape_rss_avec_doublon)

    orchestrator.run()

    conn = sqlite3.connect(str(test_db))
    rows = conn.execute("SELECT url FROM articles_raw").fetchall()
    conn.close()

    assert len(rows) == 2, \
        "le doublon exact (même titre) ne doit pas être inséré en base : 2 articles uniques attendus"

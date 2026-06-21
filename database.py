import sqlite3
from datetime import datetime, timezone

DB_PATH = "afrotech.db"


def creer_base():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles_raw (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                titre       TEXT NOT NULL,
                url         TEXT NOT NULL UNIQUE,
                source_id   TEXT NOT NULL,
                date_pub    TEXT,
                contenu     TEXT,
                date_collecte TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def sauvegarder_article(titre, url, source_id, date_pub, contenu):
    date_collecte = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO articles_raw
                (titre, url, source_id, date_pub, contenu, date_collecte)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (titre, url, source_id, date_pub, contenu, date_collecte),
        )
        conn.commit()
    finally:
        conn.close()


def article_existe(url):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT 1 FROM articles_raw WHERE url = ?", (url,)
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def _run_tests():
    import os
    test_db = "afrotech_test.db"
    global DB_PATH
    DB_PATH = test_db

    try:
        creer_base()

        # Test 1 : insérer un article et vérifier qu'il est en base
        sauvegarder_article(
            titre="IA révolutionne l'agriculture au Kenya",
            url="https://exemple.com/article-1",
            source_id="techpoint-africa",
            date_pub="2026-06-20",
            contenu="Des startups utilisent l'IA pour optimiser les rendements agricoles.",
        )
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT titre FROM articles_raw WHERE url = ?",
            ("https://exemple.com/article-1",),
        ).fetchone()
        conn.close()

        assert row is not None, "Test 1 ECHOUE : article introuvable après insertion"
        assert row[0] == "IA révolutionne l'agriculture au Kenya", "Test 1 ECHOUE : titre incorrect"
        print("Test 1 OK — article inséré et retrouvé en base")

        # Test 2 : article_existe() fonctionne
        assert article_existe("https://exemple.com/article-1"), \
            "Test 2 ECHOUE : article_existe() devrait retourner True"
        assert not article_existe("https://exemple.com/inexistant"), \
            "Test 2 ECHOUE : article_existe() devrait retourner False"
        print("Test 2 OK — article_existe() fonctionne correctement")

        print("\nTous les tests sont passés.")
    finally:
        DB_PATH = "afrotech.db"
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    creer_base()
    print(f"Base de données '{DB_PATH}' créée/ouverte sans erreur.")
    _run_tests()

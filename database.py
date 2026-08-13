import sqlite3
from datetime import datetime, timezone

DB_PATH = "afrotech.db"
SEUIL_PERTINENCE = 40


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
                date_collecte TEXT NOT NULL,
                score_pertinence INTEGER DEFAULT 0,
                resume TEXT
            )
        """)
        colonnes = [row[1] for row in conn.execute("PRAGMA table_info(articles_raw)")]
        if "score_pertinence" not in colonnes:
            conn.execute(
                "ALTER TABLE articles_raw ADD COLUMN score_pertinence INTEGER DEFAULT 0"
            )
        if "resume" not in colonnes:
            conn.execute("ALTER TABLE articles_raw ADD COLUMN resume TEXT")
        if "score_editorial" not in colonnes:
            conn.execute("ALTER TABLE articles_raw ADD COLUMN score_editorial REAL")
        if "selectionne" not in colonnes:
            conn.execute(
                "ALTER TABLE articles_raw ADD COLUMN selectionne INTEGER DEFAULT 0"
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS newsletters (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                contenu         TEXT NOT NULL,
                nb_articles     INTEGER NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'brouillon',
                date_generation TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def sauvegarder_article(titre, url, source_id, date_pub, contenu, score_pertinence):
    date_collecte = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO articles_raw
                (titre, url, source_id, date_pub, contenu, date_collecte, score_pertinence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (titre, url, source_id, date_pub, contenu, date_collecte, score_pertinence),
        )
        conn.commit()
    finally:
        conn.close()


def sauvegarder_resume(url, resume):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE articles_raw SET resume = ? WHERE url = ?",
            (resume, url),
        )
        conn.commit()
    finally:
        conn.close()


def sauvegarder_newsletter(contenu, nb_articles, statut="brouillon"):
    date_generation = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        curseur = conn.execute(
            """
            INSERT INTO newsletters (contenu, nb_articles, statut, date_generation)
            VALUES (?, ?, ?, ?)
            """,
            (contenu, nb_articles, statut, date_generation),
        )
        conn.commit()
        return curseur.lastrowid
    finally:
        conn.close()


def articles_a_resumer(seuil=SEUIL_PERTINENCE, limit=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        requete = """
            SELECT url, titre, contenu
            FROM articles_raw
            WHERE score_pertinence > ? AND resume IS NULL
        """
        params = [seuil]
        if limit is not None:
            requete += " LIMIT ?"
            params.append(limit)
        return conn.execute(requete, params).fetchall()
    finally:
        conn.close()


def articles_selectionnables(seuil=SEUIL_PERTINENCE, limit=None):
    conn = sqlite3.connect(DB_PATH)
    try:
        requete = """
            SELECT url, titre, contenu, source_id, date_pub, score_pertinence
            FROM articles_raw
            WHERE score_pertinence > ? AND resume IS NOT NULL AND selectionne = 0
        """
        params = [seuil]
        if limit is not None:
            requete += " LIMIT ?"
            params.append(limit)
        return conn.execute(requete, params).fetchall()
    finally:
        conn.close()


def marquer_selectionne(url, score_editorial):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE articles_raw SET selectionne = 1, score_editorial = ? WHERE url = ?",
            (score_editorial, url),
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

        sauvegarder_article(
            titre="IA révolutionne l'agriculture au Kenya",
            url="https://exemple.com/article-1",
            source_id="techpoint-africa",
            date_pub="2026-06-20",
            contenu="Des startups utilisent l'IA pour optimiser les rendements agricoles.",
            score_pertinence=55,
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

        assert article_existe("https://exemple.com/article-1"), \
            "Test 2 ECHOUE : article_existe() devrait retourner True"
        assert not article_existe("https://exemple.com/inexistant"), \
            "Test 2 ECHOUE : article_existe() devrait retourner False"
        print("Test 2 OK — article_existe() fonctionne correctement")

        conn = sqlite3.connect(test_db)
        colonnes = [row[1] for row in conn.execute("PRAGMA table_info(articles_raw)")]
        conn.close()
        assert "resume" in colonnes, "Test 3 ECHOUE : colonne resume absente après creer_base()"
        print("Test 3 OK — colonne resume présente après creer_base()")

        sauvegarder_resume("https://exemple.com/article-1", "Résumé généré par l'agent LLM.")
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT titre, resume FROM articles_raw WHERE url = ?",
            ("https://exemple.com/article-1",),
        ).fetchone()
        conn.close()

        assert row[1] == "Résumé généré par l'agent LLM.", \
            "Test 4 ECHOUE : sauvegarder_resume() n'a pas mis à jour le résumé"
        assert row[0] == "IA révolutionne l'agriculture au Kenya", \
            "Test 4 ECHOUE : sauvegarder_resume() a écrasé une autre colonne"
        print("Test 4 OK — sauvegarder_resume() met à jour resume sans écraser les autres colonnes")

        sauvegarder_article(
            titre="Article hors-sujet",
            url="https://exemple.com/article-2",
            source_id="techpoint-africa",
            date_pub="2026-06-21",
            contenu="Contenu peu pertinent.",
            score_pertinence=10,
        )
        sauvegarder_article(
            titre="Article pertinent pas encore résumé",
            url="https://exemple.com/article-3",
            source_id="techpoint-africa",
            date_pub="2026-06-22",
            contenu="Contenu pertinent à résumer.",
            score_pertinence=60,
        )

        a_resumer = articles_a_resumer(seuil=40)
        urls = [row[0] for row in a_resumer]
        assert "https://exemple.com/article-1" not in urls, \
            "Test 5 ECHOUE : article déjà résumé ne doit pas être sélectionné"
        assert "https://exemple.com/article-2" not in urls, \
            "Test 5 ECHOUE : article sous le seuil ne doit pas être sélectionné"
        assert "https://exemple.com/article-3" in urls, \
            "Test 5 ECHOUE : article pertinent sans résumé doit être sélectionné"
        print("Test 5 OK — articles_a_resumer() filtre bien par seuil et par resume IS NULL")

        a_resumer_limite = articles_a_resumer(seuil=40, limit=0)
        assert a_resumer_limite == [], \
            "Test 5b ECHOUE : limit=0 devrait retourner une liste vide"
        print("Test 5b OK — le paramètre limit est bien appliqué")

        conn = sqlite3.connect(test_db)
        colonnes = [row[1] for row in conn.execute("PRAGMA table_info(articles_raw)")]
        conn.close()
        assert "score_editorial" in colonnes, "Test 6 ECHOUE : colonne score_editorial absente"
        assert "selectionne" in colonnes, "Test 6 ECHOUE : colonne selectionne absente"
        print("Test 6 OK — colonnes score_editorial et selectionne présentes après creer_base()")

        sauvegarder_resume("https://exemple.com/article-3", "Résumé de l'article pertinent.")
        selectionnables = articles_selectionnables(seuil=40)
        urls_selectionnables = [row[0] for row in selectionnables]
        assert "https://exemple.com/article-1" in urls_selectionnables, \
            "Test 7 ECHOUE : article résumé et pertinent doit être sélectionnable"
        assert "https://exemple.com/article-2" not in urls_selectionnables, \
            "Test 7 ECHOUE : article sous le seuil ne doit pas être sélectionnable"
        assert "https://exemple.com/article-3" in urls_selectionnables, \
            "Test 7 ECHOUE : article tout juste résumé doit être sélectionnable"
        print("Test 7 OK — articles_selectionnables() filtre par seuil, resume et selectionne")

        marquer_selectionne("https://exemple.com/article-1", score_editorial=72.5)
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT selectionne, score_editorial FROM articles_raw WHERE url = ?",
            ("https://exemple.com/article-1",),
        ).fetchone()
        conn.close()
        assert row[0] == 1, "Test 8 ECHOUE : selectionne devrait valoir 1 après marquer_selectionne()"
        assert row[1] == 72.5, "Test 8 ECHOUE : score_editorial mal enregistré"
        urls_apres_marquage = [row[0] for row in articles_selectionnables(seuil=40)]
        assert "https://exemple.com/article-1" not in urls_apres_marquage, \
            "Test 8 ECHOUE : un article déjà sélectionné ne doit plus être proposé"
        print("Test 8 OK — marquer_selectionne() enregistre le score et exclut l'article des prochains tirages")

        newsletter_id = sauvegarder_newsletter("# AfroTech Pulse\n\nContenu factice.", nb_articles=3)
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT statut, nb_articles FROM newsletters WHERE id = ?", (newsletter_id,)
        ).fetchone()
        conn.close()
        assert row is not None, "Test 9 ECHOUE : newsletter introuvable après insertion"
        assert row[0] == "brouillon", "Test 9 ECHOUE : statut par défaut devrait être 'brouillon'"
        assert row[1] == 3, "Test 9 ECHOUE : nb_articles incorrect"
        print("Test 9 OK — sauvegarder_newsletter() insère bien avec le statut brouillon")

        print("\nTous les tests sont passés.")
    finally:
        DB_PATH = "afrotech.db"
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    creer_base()
    print(f"Base de données '{DB_PATH}' créée/ouverte sans erreur.")
    _run_tests()

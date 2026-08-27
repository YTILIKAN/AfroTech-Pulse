import sqlite3
from datetime import datetime, timezone

DB_PATH = "afrotech.db"
SEUIL_PERTINENCE = 40

TRANSITIONS_AUTORISEES = {
    "brouillon": {"en_revue"},
    "en_revue": {"validé", "rejeté"},
    "validé": {"publié"},
    "rejeté": set(),
    "publié": set(),
}

CANAUX_PUBLICATION = ("telegram", "email")
STATUTS_PUBLICATION_CANAL = {"en_attente", "publié", "echec"}


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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS newsletters_historique (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id   INTEGER NOT NULL,
                ancien_statut   TEXT NOT NULL,
                nouveau_statut  TEXT NOT NULL,
                auteur          TEXT NOT NULL,
                horodatage      TEXT NOT NULL,
                FOREIGN KEY (newsletter_id) REFERENCES newsletters(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS newsletters_publications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                newsletter_id   INTEGER NOT NULL,
                canal           TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'en_attente',
                tentatives      INTEGER NOT NULL DEFAULT 0,
                erreur          TEXT,
                horodatage      TEXT NOT NULL,
                FOREIGN KEY (newsletter_id) REFERENCES newsletters(id),
                UNIQUE (newsletter_id, canal)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS abonnes_email (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                email               TEXT NOT NULL UNIQUE,
                statut              TEXT NOT NULL DEFAULT 'actif',
                date_inscription    TEXT NOT NULL
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


def changer_statut_newsletter(newsletter_id, nouveau_statut, auteur):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Newsletter introuvable : id={newsletter_id}")

        statut_actuel = row[0]
        if nouveau_statut not in TRANSITIONS_AUTORISEES.get(statut_actuel, set()):
            raise ValueError(
                f"Transition interdite : {statut_actuel!r} → {nouveau_statut!r}"
            )

        horodatage = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE newsletters SET statut = ? WHERE id = ?",
            (nouveau_statut, newsletter_id),
        )
        conn.execute(
            """
            INSERT INTO newsletters_historique
                (newsletter_id, ancien_statut, nouveau_statut, auteur, horodatage)
            VALUES (?, ?, ?, ?, ?)
            """,
            (newsletter_id, statut_actuel, nouveau_statut, auteur, horodatage),
        )
        conn.commit()
    finally:
        conn.close()


def modifier_contenu_newsletter(newsletter_id, nouveau_contenu):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE newsletters SET contenu = ? WHERE id = ?",
            (nouveau_contenu, newsletter_id),
        )
        conn.commit()
    finally:
        conn.close()


def derniere_newsletter_brouillon():
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT id, contenu, nb_articles, statut, date_generation
            FROM newsletters
            WHERE statut = 'brouillon'
            ORDER BY date_generation DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()


def derniere_newsletter_validee():
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT id, contenu, nb_articles, statut, date_generation
            FROM newsletters
            WHERE statut = 'validé'
            ORDER BY date_generation DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()


def newsletter_par_id(newsletter_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT id, contenu, nb_articles, statut, date_generation
            FROM newsletters
            WHERE id = ?
            """,
            (newsletter_id,),
        ).fetchone()
    finally:
        conn.close()


def enregistrer_publication_canal(newsletter_id, canal, statut, tentatives, erreur=None):
    if statut not in STATUTS_PUBLICATION_CANAL:
        raise ValueError(f"Statut de publication inconnu : {statut!r}")

    horodatage = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO newsletters_publications
                (newsletter_id, canal, statut, tentatives, erreur, horodatage)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (newsletter_id, canal) DO UPDATE SET
                statut = excluded.statut,
                tentatives = excluded.tentatives,
                erreur = excluded.erreur,
                horodatage = excluded.horodatage
            """,
            (newsletter_id, canal, statut, tentatives, erreur, horodatage),
        )
        conn.commit()
    finally:
        conn.close()


def statuts_publication(newsletter_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT canal, statut, tentatives, erreur, horodatage
            FROM newsletters_publications
            WHERE newsletter_id = ?
            ORDER BY canal
            """,
            (newsletter_id,),
        ).fetchall()
    finally:
        conn.close()


def tous_canaux_publies(newsletter_id, canaux=CANAUX_PUBLICATION):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT canal, statut FROM newsletters_publications WHERE newsletter_id = ?",
            (newsletter_id,),
        ).fetchall()
    finally:
        conn.close()
    statuts = dict(rows)
    return all(statuts.get(canal) == "publié" for canal in canaux)


def ajouter_abonne_email(email):
    date_inscription = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO abonnes_email (email, statut, date_inscription)
            VALUES (?, 'actif', ?)
            """,
            (email, date_inscription),
        )
        conn.commit()
    finally:
        conn.close()


def lister_abonnes_actifs():
    conn = sqlite3.connect(DB_PATH)
    try:
        return [
            row[0] for row in conn.execute(
                "SELECT email FROM abonnes_email WHERE statut = 'actif' ORDER BY date_inscription"
            )
        ]
    finally:
        conn.close()


def desabonner_email(email):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE abonnes_email SET statut = 'inactif' WHERE email = ?", (email,))
        conn.commit()
    finally:
        conn.close()


def historique_newsletter(newsletter_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            """
            SELECT ancien_statut, nouveau_statut, auteur, horodatage
            FROM newsletters_historique
            WHERE newsletter_id = ?
            ORDER BY horodatage
            """,
            (newsletter_id,),
        ).fetchall()
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
            SELECT url, titre, contenu, source_id, date_pub, score_pertinence, resume
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

        changer_statut_newsletter(newsletter_id, "en_revue", "Alice")
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "en_revue", "Test 10 ECHOUE : le statut devrait être 'en_revue'"
        historique = historique_newsletter(newsletter_id)
        assert len(historique) == 1, "Test 10 ECHOUE : une transition devrait être historisée"
        assert historique[0] == ("brouillon", "en_revue", "Alice", historique[0][3]), \
            "Test 10 ECHOUE : entrée d'historique incorrecte"
        print("Test 10 OK — changer_statut_newsletter() applique une transition autorisée et l'historise")

        try:
            changer_statut_newsletter(newsletter_id, "publié", "Alice")
            assert False, "Test 11 ECHOUE : en_revue → publié devrait être interdit"
        except ValueError:
            pass
        print("Test 11 OK — changer_statut_newsletter() rejette une transition non prévue par la machine à états")

        changer_statut_newsletter(newsletter_id, "rejeté", "Bob")
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "rejeté", "Test 12 ECHOUE : le statut devrait être 'rejeté'"
        print("Test 12 OK — changer_statut_newsletter() autorise en_revue → rejeté")

        try:
            changer_statut_newsletter(newsletter_id, "publié", "Bob")
            assert False, "Test 13 ECHOUE : rejeté → publié devrait être interdit"
        except ValueError:
            pass
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "rejeté", "Test 13 ECHOUE : le statut ne doit pas bouger après une transition refusée"
        print("Test 13 OK — une newsletter rejetée ne peut pas être publiée")

        historique = historique_newsletter(newsletter_id)
        assert len(historique) == 2, "Test 14 ECHOUE : deux transitions valides auraient dû être historisées"
        assert [h[:3] for h in historique] == [
            ("brouillon", "en_revue", "Alice"),
            ("en_revue", "rejeté", "Bob"),
        ], "Test 14 ECHOUE : historique_newsletter() ne reflète pas les transitions dans l'ordre"
        print("Test 14 OK — historique_newsletter() ne retient que les transitions effectivement appliquées, dans l'ordre chronologique")

        newsletter_id_2 = sauvegarder_newsletter("# AfroTech Pulse\n\nBrouillon 2.", nb_articles=5)
        modifier_contenu_newsletter(newsletter_id_2, "# AfroTech Pulse\n\nContenu corrigé par l'éditeur.")
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT contenu, nb_articles, statut FROM newsletters WHERE id = ?", (newsletter_id_2,)
        ).fetchone()
        conn.close()
        assert row[0] == "# AfroTech Pulse\n\nContenu corrigé par l'éditeur.", \
            "Test 15 ECHOUE : modifier_contenu_newsletter() n'a pas mis à jour le contenu"
        assert row[1] == 5, "Test 15 ECHOUE : modifier_contenu_newsletter() a écrasé nb_articles"
        assert row[2] == "brouillon", "Test 15 ECHOUE : modifier_contenu_newsletter() a écrasé statut"
        print("Test 15 OK — modifier_contenu_newsletter() met à jour le contenu sans écraser les autres colonnes")

        derniere = derniere_newsletter_brouillon()
        assert derniere is not None, "Test 16 ECHOUE : une newsletter en brouillon devrait être trouvée"
        assert derniere[0] == newsletter_id_2, \
            "Test 16 ECHOUE : derniere_newsletter_brouillon() ne retourne pas la bonne newsletter"
        print("Test 16 OK — derniere_newsletter_brouillon() retourne la dernière newsletter en statut brouillon")

        newsletter_id_3 = sauvegarder_newsletter("# AfroTech Pulse\n\nBrouillon 3.", nb_articles=4)
        changer_statut_newsletter(newsletter_id_3, "en_revue", "Alice")
        changer_statut_newsletter(newsletter_id_3, "validé", "Alice")

        derniere_validee = derniere_newsletter_validee()
        assert derniere_validee is not None, "Test 17 ECHOUE : une newsletter validée devrait être trouvée"
        assert derniere_validee[0] == newsletter_id_3, \
            "Test 17 ECHOUE : derniere_newsletter_validee() ne retourne pas la bonne newsletter"
        print("Test 17 OK — derniere_newsletter_validee() retourne la dernière newsletter en statut validé")

        par_id = newsletter_par_id(newsletter_id_3)
        assert par_id is not None and par_id[0] == newsletter_id_3, \
            "Test 17b ECHOUE : newsletter_par_id() devrait retrouver la newsletter par son id"
        assert par_id[1] == "# AfroTech Pulse\n\nBrouillon 3.", \
            "Test 17b ECHOUE : newsletter_par_id() ne retourne pas le bon contenu"
        print("Test 17b OK — newsletter_par_id() retrouve une newsletter par son id quel que soit son statut")

        assert statuts_publication(newsletter_id_3) == [], \
            "Test 18 ECHOUE : aucune publication ne devrait exister avant tout envoi"
        assert not tous_canaux_publies(newsletter_id_3), \
            "Test 18 ECHOUE : tous_canaux_publies() devrait être False sans aucune publication enregistrée"
        print("Test 18 OK — aucune publication enregistrée par défaut pour une newsletter validée")

        enregistrer_publication_canal(newsletter_id_3, "telegram", "publié", tentatives=1)
        enregistrer_publication_canal(newsletter_id_3, "email", "echec", tentatives=3, erreur="Timeout API Resend")

        publications = dict(
            (canal, (statut, tentatives, erreur))
            for canal, statut, tentatives, erreur, _ in statuts_publication(newsletter_id_3)
        )
        assert publications["telegram"] == ("publié", 1, None), \
            "Test 19 ECHOUE : le statut Telegram devrait être 'publié' avec 1 tentative"
        assert publications["email"] == ("echec", 3, "Timeout API Resend"), \
            "Test 19 ECHOUE : le statut Email devrait refléter l'échec et son message d'erreur"
        assert not tous_canaux_publies(newsletter_id_3), \
            "Test 19 ECHOUE : tous_canaux_publies() doit être False si un canal est en échec"
        print("Test 19 OK — enregistrer_publication_canal() trace précisément un succès partiel (Telegram OK, Email KO)")

        changer_statut_newsletter(newsletter_id_3, "publié", "Alice")
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT statut FROM newsletters WHERE id = ?", (newsletter_id_3,)
        ).fetchone()
        conn.close()
        assert row[0] == "publié", "Test 20 ECHOUE : le statut global aurait dû passer à 'publié'"
        print("Test 20 OK — validé → publié reste une transition légale : c'est à publisher/publish.py de "
              "n'appeler changer_statut_newsletter() vers 'publié' que lorsque tous_canaux_publies() est vrai")

        newsletter_id_4 = sauvegarder_newsletter("# AfroTech Pulse\n\nBrouillon 4.", nb_articles=2)
        changer_statut_newsletter(newsletter_id_4, "en_revue", "Alice")
        changer_statut_newsletter(newsletter_id_4, "validé", "Alice")

        enregistrer_publication_canal(newsletter_id_4, "telegram", "echec", tentatives=1, erreur="Timeout")
        enregistrer_publication_canal(newsletter_id_4, "email", "echec", tentatives=1, erreur="Timeout")
        assert not tous_canaux_publies(newsletter_id_4), \
            "Test 21 ECHOUE : tous_canaux_publies() doit être False si les deux canaux ont échoué"

        enregistrer_publication_canal(newsletter_id_4, "telegram", "publié", tentatives=2)
        enregistrer_publication_canal(newsletter_id_4, "email", "publié", tentatives=2)
        assert tous_canaux_publies(newsletter_id_4), \
            "Test 21 ECHOUE : tous_canaux_publies() doit être True une fois les deux canaux republiés avec succès"

        publications_apres_retry = dict(
            (canal, tentatives) for canal, _, tentatives, _, _ in statuts_publication(newsletter_id_4)
        )
        assert publications_apres_retry == {"telegram": 2, "email": 2}, \
            "Test 21 ECHOUE : un nouvel appel à enregistrer_publication_canal() doit mettre à jour la ligne existante (upsert), pas en créer une nouvelle"
        print("Test 21 OK — republier un canal en échec met à jour sa ligne (upsert) sans dupliquer, et tous_canaux_publies() ne devient True qu'après succès des deux canaux")

        assert lister_abonnes_actifs() == [], "Test 22 ECHOUE : aucun abonné ne devrait exister par défaut"

        ajouter_abonne_email("test1@exemple.com")
        ajouter_abonne_email("test2@exemple.com")
        ajouter_abonne_email("test1@exemple.com")
        assert lister_abonnes_actifs() == ["test1@exemple.com", "test2@exemple.com"], \
            "Test 22 ECHOUE : ajouter_abonne_email() doit ignorer les doublons et lister les actifs par ordre d'inscription"
        print("Test 22 OK — ajouter_abonne_email() ajoute sans dupliquer, lister_abonnes_actifs() retourne les emails actifs")

        desabonner_email("test1@exemple.com")
        assert lister_abonnes_actifs() == ["test2@exemple.com"], \
            "Test 23 ECHOUE : desabonner_email() doit retirer l'email de la liste des actifs"
        print("Test 23 OK — desabonner_email() retire bien l'abonné de la liste des actifs")

        print("\nTous les tests sont passés.")
    finally:
        DB_PATH = "afrotech.db"
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    creer_base()
    print(f"Base de données '{DB_PATH}' créée/ouverte sans erreur.")
    _run_tests()

from datetime import datetime, timezone

import database
import pipeline.editor as editor_module
import pipeline.run_editor as run_editor_module
from pipeline.editor import score_editorial, selectionner_articles_semaine

MAINTENANT = datetime(2026, 8, 11, tzinfo=timezone.utc)


# --- score_editorial() : unitaires -----------------------------------------

def test_article_recent_a_un_bonus_de_fraicheur():
    score_recent = score_editorial(50, "2026-08-10T00:00:00", MAINTENANT)
    assert score_recent > 50, f"score={score_recent}, un article d'hier doit avoir un bonus > 0"


def test_article_ancien_n_a_aucun_bonus_de_fraicheur():
    score_ancien = score_editorial(50, "2026-07-20T00:00:00", MAINTENANT)
    assert score_ancien == 50, f"score={score_ancien}, un article de 3 semaines ne doit avoir aucun bonus"


def test_article_au_seuil_limite_de_fraicheur():
    date_pile_au_seuil = "2026-08-04T00:00:00"  # exactement JOURS_FRAICHEUR_MAX jours avant MAINTENANT
    score = score_editorial(50, date_pile_au_seuil, MAINTENANT)
    assert score == 50, f"score={score}, le bonus doit retomber à 0 pile au seuil"


def test_date_manquante_ne_plante_pas_et_bonus_nul():
    score = score_editorial(50, "", MAINTENANT)
    assert score == 50, f"score={score}, une date absente ne doit donner aucun bonus (mais ne doit pas planter)"


def test_date_invalide_ne_plante_pas_et_bonus_nul():
    score = score_editorial(50, "pas-une-date", MAINTENANT)
    assert score == 50, f"score={score}, une date mal formée ne doit donner aucun bonus (mais ne doit pas planter)"


# --- selectionner_articles_semaine() : unitaires (base mockée) -------------

def _candidat(url, titre, score_pertinence, date_pub="2026-08-10T00:00:00", source_id="src",
              resume="Résumé de test."):
    return (url, titre, titre, source_id, date_pub, score_pertinence, resume)


def test_moins_de_5_candidats_retourne_tout_sans_planter(monkeypatch):
    candidats = [
        _candidat("u1", "Nigeria startup news", 60),
        _candidat("u2", "Kenya AI pilot", 55),
    ]
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    assert len(selection) == 2


def test_exactement_7_candidats_diversifies_retourne_les_7(monkeypatch):
    # 2 Nigeria + 2 Kenya + 2 Ghana + 1 Sénégal = 7, compatible avec la règle
    # de diversité (max 2/pays) : aucun ne doit être écarté.
    candidats = (
        [_candidat(f"ng{i}", f"Nigeria article {i}", 60 + i) for i in range(2)]
        + [_candidat(f"ke{i}", f"Kenya article {i}", 55 + i) for i in range(2)]
        + [_candidat(f"gh{i}", f"Ghana article {i}", 50 + i) for i in range(2)]
        + [_candidat("sn0", "Senegal article", 45)]
    )
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    assert len(selection) == 7


def test_plus_de_7_candidats_diversifies_retourne_7_meilleurs(monkeypatch):
    candidats = (
        [_candidat(f"ng{i}", f"Nigeria article {i}", 90 - i) for i in range(3)]
        + [_candidat(f"ke{i}", f"Kenya article {i}", 85 - i) for i in range(3)]
        + [_candidat(f"gh{i}", f"Ghana article {i}", 80 - i) for i in range(3)]
        + [_candidat(f"za{i}", f"South Africa article {i}", 75 - i) for i in range(3)]
    )
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    assert len(selection) == 7
    compte_par_pays = {}
    for article in selection:
        compte_par_pays[article["pays"]] = compte_par_pays.get(article["pays"], 0) + 1
    for pays, compte in compte_par_pays.items():
        assert compte <= editor_module.MAX_ARTICLES_PAR_PAYS, \
            f"{pays} apparaît {compte} fois, la règle de diversité doit limiter à {editor_module.MAX_ARTICLES_PAR_PAYS}"


def test_tous_du_meme_pays_force_la_diversite_mais_atteint_le_minimum(monkeypatch):
    candidats = [_candidat(f"ng{i}", f"Nigeria article {i}", 90 - i) for i in range(9)]
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    # la règle de diversité (max 2/pays) ne permettrait que 2 articles :
    # le repli doit compléter jusqu'au minimum (5) plutôt que sous-livrer.
    assert len(selection) == editor_module.SELECTION_MIN
    urls = {a["url"] for a in selection}
    assert urls == {"ng0", "ng1", "ng2", "ng3", "ng4"}, \
        "le repli doit prendre les meilleurs scores restants, dans l'ordre"


def test_resume_du_candidat_est_reporte_dans_la_selection(monkeypatch):
    candidats = [_candidat("u1", "Nigeria startup news", 60, resume="Une startup nigériane lève des fonds.")]
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    assert selection[0]["resume"] == "Une startup nigériane lève des fonds.", \
        "le resume du candidat doit être reporté tel quel dans le dict de sélection, " \
        "sinon newsletter/writer.py reçoit un article sans contenu à rédiger"


def test_selection_est_triee_par_score_decroissant(monkeypatch):
    candidats = [
        _candidat("faible", "Kenya article faible", 40),
        _candidat("fort", "Nigeria article fort", 90),
        _candidat("moyen", "Ghana article moyen", 65),
    ]
    monkeypatch.setattr(editor_module.database, "articles_selectionnables", lambda seuil: candidats)

    selection = selectionner_articles_semaine(seuil=40, maintenant=MAINTENANT)

    urls_ordre = [a["url"] for a in selection]
    assert urls_ordre == ["fort", "moyen", "faible"]


# --- run_editor.py : intégration sur une vraie base ------------------------

def test_run_editor_bout_en_bout_sur_base_reelle(monkeypatch, tmp_path):
    test_db = tmp_path / "editor_integration_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(run_editor_module.database, "DB_PATH", str(test_db))

    database.creer_base()

    pays_disponibles = ["nigeria", "kenya", "ghana", "senegal", "rwanda", "maroc"]
    for i in range(30):
        pays = pays_disponibles[i % len(pays_disponibles)]
        titre = f"{pays.capitalize()} tech news item {i}"
        url = f"https://exemple.com/article-{i}"
        database.sauvegarder_article(
            titre=titre, url=url, source_id="source-test",
            date_pub="2026-08-10T00:00:00", contenu=titre,
            score_pertinence=40 + i,
        )
        database.sauvegarder_resume(url, "résumé de test")

    run_editor_module.run()

    conn = __import__("sqlite3").connect(str(test_db))
    rows = conn.execute(
        "SELECT titre, score_editorial FROM articles_raw WHERE selectionne = 1"
    ).fetchall()
    toutes_colonnes_intactes = conn.execute(
        "SELECT COUNT(*) FROM articles_raw WHERE contenu IS NULL OR resume IS NULL"
    ).fetchone()[0]
    conn.close()

    assert 5 <= len(rows) <= 7, f"{len(rows)} articles sélectionnés, attendu entre 5 et 7"
    assert all(score is not None for _, score in rows), "score_editorial ne doit pas être NULL pour un article sélectionné"
    assert toutes_colonnes_intactes == 0, \
        "la sélection ne doit pas effacer contenu/resume des articles existants (non-régression)"

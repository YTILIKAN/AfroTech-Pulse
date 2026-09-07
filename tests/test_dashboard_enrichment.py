from dashboard.enrichment import (
    SECTEUR_DEFAUT,
    classer_secteurs,
    detecter_pays,
    enrichir,
)


# --- Détection pays ---

def test_pays_detecte_dans_le_titre():
    assert detecter_pays("Une startup de Lagos, au Nigéria, lève des fonds") == ("Nigéria", "NGA")


def test_ville_compte_comme_une_mention_du_pays():
    assert detecter_pays("Nouveau hub tech à Cape Town") == ("Afrique du Sud", "ZAF")


def test_variantes_fr_en_donnent_le_meme_code():
    assert detecter_pays("AI in South Africa")[1] == detecter_pays("L'IA en Afrique du Sud")[1] == "ZAF"


def test_terme_generique_africa_ne_compte_pas_comme_un_pays():
    assert detecter_pays("African startups raise more funding this year") is None


def test_niger_ne_matche_pas_dans_nigeria():
    assert detecter_pays("Fintech boom in Nigeria") == ("Nigéria", "NGA")


def test_titre_prioritaire_sur_le_corps():
    pays = detecter_pays("Le Kenya en tête", "Des acteurs du Ghana et du Nigéria réagissent")
    assert pays == ("Kenya", "KEN")


# --- Classification secteurs ---

def test_secteur_fintech_par_mot_cle():
    assert classer_secteurs("Une fintech de paiement mobile à Dakar") == ["fintech"]


def test_article_multi_secteurs():
    secteurs = classer_secteurs("Du mobile money pour les farmers kényans")
    assert set(secteurs) == {"fintech", "agriculture"}


def test_indice_categorie_ajoute_le_secteur():
    assert "fintech" in classer_secteurs("Levée de fonds record", categorie="Fintech")


def test_article_sans_mot_cle_tombe_dans_generaliste():
    assert classer_secteurs("Sommet de l'Union africaine sur l'innovation") == [SECTEUR_DEFAUT]


def test_vocabulaire_ia_generique_ne_declenche_pas_education():
    # "machine learning" / "apprentissage automatique" ne doivent PAS classer en éducation
    assert classer_secteurs("A new machine learning model for deep learning research") == [SECTEUR_DEFAUT]
    assert classer_secteurs("Un modèle d'apprentissage automatique et d'apprentissage profond") == [SECTEUR_DEFAUT]


def test_secteur_sante_fr_et_en():
    assert classer_secteurs("A healthtech startup") == ["santé"]
    assert classer_secteurs("Une startup de télémédecine") == ["santé"]


# --- enrichir() ---

def test_enrichir_ajoute_les_champs_sans_muter_lentree():
    articles = [{"titre": "Fintech au Nigéria", "contenu": "", "resume": ""}]
    enrichis = enrichir(articles)
    assert enrichis[0]["pays_iso"] == "NGA"
    assert enrichis[0]["secteurs"] == ["fintech"]
    assert "pays_iso" not in articles[0], "enrichir() ne doit pas modifier la liste d'entrée"


def test_enrichir_article_sans_pays_detectable():
    enrichis = enrichir([{"titre": "OpenAI announces new model", "contenu": "", "resume": ""}])
    assert enrichis[0]["pays_iso"] is None
    assert enrichis[0]["pays_nom"] is None
    assert enrichis[0]["secteurs"] == [SECTEUR_DEFAUT]

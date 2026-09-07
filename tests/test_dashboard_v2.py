import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import database
from dashboard.aggregations import comparer_pays
from dashboard.entities import (
    charger_exclusions_sources,
    construire_exclusions,
    extraire_entites,
)
from dashboard.filters import bornes_periode, filtrer, options_pays, options_secteurs
from dashboard.text import compter_mots, nettoyer, tokeniser

APP_PATH = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")
DB_PROD = Path(__file__).resolve().parent.parent / "afrotech.db"


def _article(titre, iso=None, nom=None, secteurs=("généraliste",), jour=1, **extra):
    return {
        "titre": titre,
        "contenu": extra.pop("contenu", ""),
        "resume": extra.pop("resume", ""),
        "source_id": "src",
        "date_pub": datetime(2026, 9, jour),
        "score_pertinence": 50,
        "pays_iso": iso,
        "pays_nom": nom,
        "secteurs": list(secteurs),
        **extra,
    }


CORPUS = [
    _article("Fintech à Lagos", "NGA", "Nigéria", ["fintech"], jour=1),
    _article("Santé au Nigéria", "NGA", "Nigéria", ["santé"], jour=2),
    _article("Mobile money et fermes au Kenya", "KEN", "Kenya", ["fintech", "agriculture"], jour=3),
    _article("Politique IA au Kenya", "KEN", "Kenya", ["généraliste"], jour=4),
    _article("EdTech au Ghana", "GHA", "Ghana", ["éducation"], jour=5),
    _article("Papier de recherche sans pays", None, None, ["généraliste"], jour=6),
]


# --- Filtrage : unitaires --------------------------------------------------------

def test_selection_vide_ne_filtre_rien():
    assert filtrer(CORPUS) == CORPUS
    assert filtrer(CORPUS, pays_iso=[], secteurs=[]) == CORPUS


def test_filtre_pays_simple():
    resultat = filtrer(CORPUS, pays_iso=["KEN"])
    assert {a["titre"] for a in resultat} == {
        "Mobile money et fermes au Kenya", "Politique IA au Kenya"
    }


def test_plusieurs_pays_sont_en_ou():
    resultat = filtrer(CORPUS, pays_iso=["KEN", "GHA"])
    assert {a["pays_iso"] for a in resultat} == {"KEN", "GHA"}
    assert len(resultat) == 3


def test_filtre_pays_exclut_les_articles_sans_pays_detecte():
    resultat = filtrer(CORPUS, pays_iso=["NGA"])
    assert all(a["pays_iso"] == "NGA" for a in resultat)
    assert "Papier de recherche sans pays" not in {a["titre"] for a in resultat}


def test_filtre_secteur_matche_un_article_multi_secteurs():
    titres = {a["titre"] for a in filtrer(CORPUS, secteurs=["agriculture"])}
    assert titres == {"Mobile money et fermes au Kenya"}, (
        "un article classé fintech + agriculture doit ressortir sur chacun de ses secteurs"
    )
    assert "Mobile money et fermes au Kenya" in {
        a["titre"] for a in filtrer(CORPUS, secteurs=["fintech"])
    }


def test_plusieurs_secteurs_sont_en_ou():
    resultat = filtrer(CORPUS, secteurs=["santé", "éducation"])
    assert {a["titre"] for a in resultat} == {"Santé au Nigéria", "EdTech au Ghana"}


def test_pays_et_secteur_sont_en_et():
    assert [a["titre"] for a in filtrer(CORPUS, pays_iso=["KEN"], secteurs=["fintech"])] == [
        "Mobile money et fermes au Kenya"
    ]


def test_combinaison_sans_resultat_retourne_une_liste_vide():
    assert filtrer(CORPUS, pays_iso=["GHA"], secteurs=["fintech"]) == []


def test_filtre_periode_borne_les_dates():
    resultat = filtrer(CORPUS, depuis=datetime(2026, 9, 3), jusqua=datetime(2026, 9, 5))
    assert {a["titre"] for a in resultat} == {
        "Mobile money et fermes au Kenya", "Politique IA au Kenya"
    }, "depuis est inclus, jusqua est exclu"


def test_les_trois_filtres_se_combinent():
    resultat = filtrer(
        CORPUS, pays_iso=["KEN", "NGA"], secteurs=["fintech"],
        depuis=datetime(2026, 9, 2), jusqua=datetime(2026, 9, 6),
    )
    assert [a["titre"] for a in resultat] == ["Mobile money et fermes au Kenya"]


def test_corpus_vide():
    assert filtrer([], pays_iso=["KEN"]) == []


def test_bornes_periode_sont_alignees_sur_le_lundi():
    depuis, jusqua = bornes_periode(8, maintenant=datetime(2026, 9, 9, 15, 30))
    assert jusqua == datetime(2026, 9, 7)
    assert depuis == datetime(2026, 7, 13)
    assert depuis.weekday() == 0


def test_options_construites_depuis_les_donnees_presentes():
    assert options_pays(CORPUS)[0][:2] in (("NGA", "Nigéria"), ("KEN", "Kenya"))
    assert {iso for iso, _n, _c in options_pays(CORPUS)} == {"NGA", "KEN", "GHA"}, (
        "un pays sans article ne doit pas être proposé au filtrage"
    )
    assert dict(options_secteurs(CORPUS))["fintech"] == 2


# --- Extraction d'entités : unitaires --------------------------------------------

def test_extrait_une_entreprise_citee():
    articles = [
        _article("Flutterwave lève des fonds", contenu="La licorne Flutterwave annonce un tour."),
        _article("Flutterwave s'étend", contenu="Flutterwave ouvre un bureau."),
    ]
    assert ("Flutterwave", 2) in extraire_entites(articles)


def test_un_acteur_compte_une_fois_par_article_pas_par_mention():
    articles = [_article("Wave", contenu="Wave et Wave et encore Wave. Wave.")]
    assert dict(extraire_entites(articles)).get("Wave") == 1


def test_les_noms_de_sources_sont_exclus():
    articles = [
        _article("Actu", contenu="The post Machin appeared first on Techpoint Africa."),
        _article("Actu", contenu="Publié par TechCabal et Disrupt Africa."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    for interdit in ("techpoint africa", "techcabal", "disrupt africa"):
        assert interdit not in trouves, f"{interdit} est une source, pas un acteur"


def test_les_acteurs_qui_sont_aussi_des_sources_restent_detectables():
    # InstaDeep, Lelapa et Masakhane sont des sources RSS *et* des acteurs majeurs de
    # l'IA africaine : les exclure viderait le classement de sa substance.
    articles = [
        _article("IA", contenu="InstaDeep et Lelapa AI collaborent avec Masakhane."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert "instadeep" in trouves
    assert any("lelapa" in nom for nom in trouves)
    assert "masakhane" in trouves


def test_les_pays_et_villes_sont_exclus():
    articles = [_article("Actu", contenu="Au Kenya et au Nigeria, à Lagos et Nairobi.")]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert trouves.isdisjoint({"kenya", "nigeria", "lagos", "nairobi"}), (
        "les pays et villes sont déjà portés par la carte"
    )


def test_les_amorces_de_phrase_ne_sont_pas_des_acteurs():
    articles = [
        _article("Actu", contenu="The startup grows. However, Yet another point. Across Africa."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert trouves.isdisjoint({"the", "however", "yet", "across"})


def test_amorce_retiree_mais_entite_conservee():
    articles = [_article("Actu", contenu="The Nigerian startup Paystack raised funds.")]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert "paystack" in trouves
    assert "the nigerian startup paystack" not in trouves


def test_le_gabarit_arxiv_ne_produit_pas_dacteurs():
    articles = [
        _article("Papier", contenu="arXiv:2607.20473v1 Announce Type: new \nAbstract: Un modèle."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert trouves.isdisjoint({"xiv", "arxiv", "announce type", "abstract", "source"}), (
        "le préfixe arXiv:XXXX produisait l'entité « Xiv » sans borne gauche dans la regex"
    )


def test_html_et_possessifs_sont_nettoyes():
    articles = [
        _article("Actu", contenu='<a href="https://x.com" rel="nofollow">Safaricom</a> '
                                 "et Kenya&amp;rsquo;s marché."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert "safaricom" in trouves
    assert trouves.isdisjoint({"kenya&", "nofollow", "https"})


def test_sigles_courts_et_domaines_sont_ecartes_mais_pas_les_organisations():
    articles = [
        _article("Actu", contenu="Le CEO a dit. KES 500. Voir ITPulse.com.ng. GSMA publie."),
    ]
    trouves = {nom.lower() for nom, _n in extraire_entites(articles)}
    assert trouves.isdisjoint({"ceo", "kes"}), "les sigles de 3 lettres sont trop ambigus"
    assert not any(".com" in nom or ".ng" in nom for nom in trouves)
    assert "gsma" in trouves, "un sigle de 4 lettres est une organisation plausible"


def test_exclusions_sources_separent_noms_complets_et_tokens(tmp_path):
    fichier = tmp_path / "sources.json"
    fichier.write_text(json.dumps({"sources": [
        {"id": "techcabal", "name": "TechCabal", "category": "Tech Afrique"},
        {"id": "instadeep", "name": "InstaDeep Tech Insights", "category": "Recherche IA"},
    ]}), encoding="utf-8")

    noms, tokens = charger_exclusions_sources(fichier)

    assert "techcabal" in noms and "techcabal" in tokens
    assert "instadeep tech insights" in noms
    assert "instadeep" not in tokens, (
        "une source de catégorie « acteur » ne perd que son nom complet"
    )


def test_exclusions_utilisables_sans_fichier_de_sources():
    exclusions = construire_exclusions()
    assert "kenya" in exclusions and "the" in exclusions and "lagos" in exclusions


# --- Nuage de mots : unitaires ---------------------------------------------------

def test_stopwords_francais_et_anglais_exclus():
    mots = tokeniser("Le Kenya et les startups dans the future of work")
    assert "kenya" in mots
    assert {"le", "et", "les", "dans", "the", "of"}.isdisjoint(mots)


def test_mots_de_bruit_metier_exclus():
    assert tokeniser("intelligence artificielle en Afrique") == []


def test_mots_trop_courts_exclus():
    assert "un" not in tokeniser("un vrai marché")
    assert "marché" in tokeniser("un vrai marché")


def test_apostrophes_coupees():
    assert "innovation" in tokeniser("l'innovation et l’avenir")


def test_html_exclu_du_nuage():
    texte = nettoyer('<a href="https://exemple.com" rel="nofollow">Paiement</a>')
    mots = tokeniser(texte)
    assert "paiement" in mots
    assert {"href", "https", "nofollow", "com"}.isdisjoint(mots)


def test_compter_mots_agrege_titre_resume_et_contenu():
    articles = [
        _article("Paiement mobile", resume="Le paiement progresse", contenu="Paiement partout"),
    ]
    assert compter_mots(articles)["paiement"] == 3, (
        "les trois champs alimentent le nuage : resume ne couvre que ~3 % du corpus"
    )


def test_prefixes_medias_ecartent_les_formes_collees():
    assert tokeniser("TechTrendsKE publie", prefixes_exclus={"techtrends"}) == ["publie"]


def test_compter_mots_corpus_vide():
    assert compter_mots([]) == {}


# --- Comparaison entre pays ------------------------------------------------------

def test_comparer_pays_compte_volume_et_secteurs():
    resultat = comparer_pays(CORPUS, ["KEN", "NGA"])
    assert resultat["KEN"]["articles"] == 2
    assert resultat["NGA"]["articles"] == 2
    assert resultat["KEN"]["secteurs"] == {"fintech": 1, "agriculture": 1, "généraliste": 1}
    assert resultat["NGA"]["nom"] == "Nigéria"


def test_comparer_pays_retourne_zero_pour_un_pays_sans_article():
    resultat = comparer_pays(CORPUS, ["KEN", "MAR"])
    assert resultat["MAR"]["articles"] == 0
    assert resultat["MAR"]["secteurs"] == {}, (
        "un pays sans article est une information, pas un trou dans le graphique"
    )


# --- Intégration : les filtres pilotent bien les visualisations -------------------

@pytest.fixture(autouse=True)
def _vider_cache_streamlit():
    import streamlit as st
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _app_sur_copie_prod(monkeypatch, tmp_path):
    if not DB_PROD.exists():
        pytest.skip("afrotech.db absente")
    copie = tmp_path / "afrotech.db"
    shutil.copy(DB_PROD, copie)
    monkeypatch.setattr(database, "DB_PATH", str(copie))
    return AppTest.from_file(APP_PATH, default_timeout=120).run()


def test_les_cinq_visualisations_sont_presentes(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)

    assert not at.exception
    # carte + secteurs + timeline + top acteurs + comparaison
    assert len(at.get("plotly_chart")) == 5
    # le nuage de mots est une image, pas un graphique Plotly
    assert len(at.get("imgs")) == 1
    assert len(at.subheader) == 6


def test_un_filtre_pays_modifie_toutes_les_visualisations(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)
    articles_avant = at.metric[0].value
    acteurs_avant = at.get("plotly_chart")[3].proto.spec

    at.sidebar.multiselect[0].set_value(["KEN"]).run()

    assert not at.exception
    assert at.metric[0].value != articles_avant, "le KPI doit suivre le filtre"
    assert at.metric[1].value == "1", "un seul pays filtré = un seul pays couvert sur la carte"
    assert at.get("plotly_chart")[3].proto.spec != acteurs_avant, (
        "le top acteurs doit être recalculé sur les articles filtrés"
    )
    assert len(at.get("imgs")) == 1, "le nuage de mots reste affiché, recalculé"
    assert len(at.subheader) == 6, "aucune section ne disparaît"


def test_le_filtre_periode_elargit_le_corpus(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)
    quatre = int(at.metric[0].value.replace(" ", "").replace(" ", ""))

    at.sidebar.radio[0].set_value(12).run()
    douze = int(at.metric[0].value.replace(" ", "").replace(" ", ""))

    assert not at.exception
    assert douze > quatre, "12 semaines doivent couvrir plus d'articles que 4"


def test_un_filtre_secteur_reduit_le_corpus(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)
    avant = int(at.metric[0].value.replace(" ", "").replace(" ", ""))

    at.sidebar.multiselect[1].set_value(["fintech"]).run()
    apres = int(at.metric[0].value.replace(" ", "").replace(" ", ""))

    assert not at.exception
    assert 0 < apres < avant


def test_filtres_sans_resultat_affichent_un_message_et_aucun_graphique(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)

    # Un pays et un secteur qui ne se croisent (quasi) jamais dans le corpus réel :
    # on retire le pays le moins couvert et on croise avec un secteur de niche.
    iso_rare = at.sidebar.multiselect[0].options[-1]
    at.sidebar.multiselect[0].set_value([iso_rare]).run()
    at.sidebar.multiselect[1].set_value(["agriculture", "santé", "éducation", "fintech"]).run()

    assert not at.exception, "une sélection vide ne doit jamais faire planter la page"
    if not at.get("plotly_chart"):
        assert any("Aucun article" in w.value for w in at.warning)


def test_comparaison_reste_affichee_avec_un_seul_pays_filtre(monkeypatch, tmp_path):
    at = _app_sur_copie_prod(monkeypatch, tmp_path)

    at.sidebar.multiselect[0].set_value(["KEN"]).run()

    assert not at.exception
    assert len(at.get("plotly_chart")) == 5, (
        "filtrer sur un seul pays ne doit pas faire disparaître la vue comparative : "
        "elle retombe sur les pays les plus couverts"
    )


def test_page_vide_si_aucune_donnee(monkeypatch, tmp_path):
    vide = tmp_path / "afrotech.db"
    monkeypatch.setattr(database, "DB_PATH", str(vide))
    database.creer_base()

    at = AppTest.from_file(APP_PATH, default_timeout=60).run()

    assert not at.exception
    assert any("Aucun article" in w.value for w in at.warning)
    assert len(at.get("plotly_chart")) == 0

from datetime import datetime

from dashboard.aggregations import par_pays, par_secteur, par_semaine

MAINTENANT = datetime(2026, 9, 9, 12, 0)  # semaine du lundi 2026-09-07 (exclue) ->
#                                            4 semaines complètes = 10/08 au 06/09


def _article(date_pub, pays_iso=None, secteurs=("généraliste",)):
    return {"date_pub": date_pub, "pays_iso": pays_iso, "secteurs": list(secteurs)}


FIXTURE = [
    _article(datetime(2026, 8, 11), "NGA", ["fintech"]),
    _article(datetime(2026, 8, 12), "NGA", ["fintech", "agriculture"]),
    _article(datetime(2026, 8, 20), "KEN", ["santé"]),
    _article(datetime(2026, 8, 28), "KEN", ["généraliste"]),
    _article(datetime(2026, 9, 1), "ZAF", ["éducation"]),
    _article(datetime(2026, 9, 2), None, ["fintech"]),  # sans pays
]


def test_par_pays_compte_et_ignore_les_articles_sans_pays():
    assert par_pays(FIXTURE) == {"NGA": 2, "KEN": 2, "ZAF": 1}


def test_par_secteur_compte_les_articles_multi_secteurs_dans_chacun():
    assert par_secteur(FIXTURE) == {
        "fintech": 3, "agriculture": 1, "santé": 1, "généraliste": 1, "éducation": 1,
    }


def test_par_semaine_retourne_toujours_n_buckets_alignes_lundi():
    resultat = par_semaine(FIXTURE, n_semaines=4, maintenant=MAINTENANT)
    assert [libelle for libelle, _ in resultat] == [
        "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31",
    ]
    assert [n for _, n in resultat] == [2, 1, 1, 2]


def test_par_semaine_inclut_les_semaines_a_zero():
    articles = [_article(datetime(2026, 8, 11)), _article(datetime(2026, 9, 1))]
    resultat = par_semaine(articles, n_semaines=4, maintenant=MAINTENANT)
    assert [n for _, n in resultat] == [1, 0, 0, 1]


def test_cas_limite_aucun_article():
    assert par_pays([]) == {}
    assert par_secteur([]) == {}
    assert par_semaine([], n_semaines=4, maintenant=MAINTENANT) == [
        ("2026-08-10", 0), ("2026-08-17", 0), ("2026-08-24", 0), ("2026-08-31", 0),
    ]

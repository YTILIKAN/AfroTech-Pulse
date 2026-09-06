from pipeline.dedup import (
    hash_article,
    est_doublon_exact,
    est_quasi_doublon,
    deduplicate,
)


def test_hash_article_normalise_casse_et_espaces():
    h1 = hash_article("  Nigerian Fintech Startup Raises $10M  ", "https://a.com/1")
    h2 = hash_article("nigerian fintech startup raises $10m", "https://b.com/2")
    assert h1 == h2


def test_hash_article_ignore_ponctuation():
    h1 = hash_article("Kenya's AI Boom: What's Next?", "https://a.com/1")
    h2 = hash_article("Kenyas AI Boom Whats Next", "https://b.com/2")
    assert h1 == h2


def test_est_doublon_exact_meme_titre_url_differente():
    article = {
        "title": "Nigerian Fintech Startup Raises $10M",
        "url": "https://siteb.com/republication-10m",
        "content": "Peu importe, le titre suffit à détecter la republication.",
    }
    hashes_vus = {hash_article("Nigerian Fintech Startup Raises $10M", "https://sitea.com/original")}
    assert est_doublon_exact(article, hashes_vus)


def test_est_doublon_exact_titre_different():
    article = {
        "title": "Kenyan Agritech Platform Expands to Tanzania",
        "url": "https://siteb.com/agritech",
        "content": "Un article totalement différent.",
    }
    hashes_vus = {hash_article("Nigerian Fintech Startup Raises $10M", "https://sitea.com/original")}
    assert not est_doublon_exact(article, hashes_vus)


def test_est_quasi_doublon_meme_depeche_reformulee():
    article_a = {
        "title": "Nigerian fintech Moniepoint raises $10M in new funding round",
        "url": "https://techcabal.com/moniepoint-funding",
        "content": (
            "Moniepoint, la fintech nigériane, a annoncé une levée de fonds de 10 "
            "millions de dollars pour accélérer son expansion en Afrique de l'Ouest."
        ),
    }
    article_b = {
        "title": "Moniepoint secures $10 million funding to expand across West Africa",
        "url": "https://techpoint.africa/moniepoint-10m-raise",
        "content": (
            "La société fintech Moniepoint basée au Nigeria a levé 10 millions de "
            "dollars afin de renforcer sa présence en Afrique de l'Ouest."
        ),
    }
    assert est_quasi_doublon(article_b, [article_a])


def test_articles_differents_ne_sont_pas_quasi_doublons():
    article_a = {
        "title": "Moniepoint raises $10M to expand fintech services in West Africa",
        "url": "https://techcabal.com/moniepoint-funding",
        "content": "Une levée de fonds fintech au Nigeria.",
    }
    article_b = {
        "title": "Kenya launches national AI strategy for agriculture",
        "url": "https://techpoint.africa/kenya-ai-agriculture",
        "content": "Le gouvernement kényan lance une stratégie IA pour l'agriculture.",
    }
    assert not est_quasi_doublon(article_b, [article_a])


def test_deduplicate_combine_doublons_exacts_et_quasi_doublons():
    articles = [
        {
            "title": "Nigerian fintech Moniepoint raises $10M in new funding round",
            "url": "https://techcabal.com/moniepoint-funding",
            "content": (
                "Moniepoint, la fintech nigériane, a annoncé une levée de fonds de 10 "
                "millions de dollars pour accélérer son expansion en Afrique de l'Ouest."
            ),
        },
        {
            # Republication : même titre, URL différente -> doublon exact
            "title": "Nigerian fintech Moniepoint raises $10M in new funding round",
            "url": "https://mirror-site.com/moniepoint-funding-copy",
            "content": (
                "Moniepoint, la fintech nigériane, a annoncé une levée de fonds de 10 "
                "millions de dollars pour accélérer son expansion en Afrique de l'Ouest."
            ),
        },
        {
            # Même dépêche reformulée par un autre média -> quasi-doublon
            "title": "Moniepoint secures $10 million funding to expand across West Africa",
            "url": "https://techpoint.africa/moniepoint-10m-raise",
            "content": (
                "La société fintech Moniepoint basée au Nigeria a levé 10 millions de "
                "dollars afin de renforcer sa présence en Afrique de l'Ouest."
            ),
        },
        {
            # Article clairement différent -> conservé
            "title": "Kenya launches national AI strategy for agriculture",
            "url": "https://techpoint.africa/kenya-ai-agriculture",
            "content": "Le gouvernement kényan lance une stratégie IA pour l'agriculture.",
        },
    ]

    resultat = deduplicate(articles)

    assert len(resultat) == 2
    urls_conservees = {a["url"] for a in resultat}
    assert urls_conservees == {
        "https://techcabal.com/moniepoint-funding",
        "https://techpoint.africa/kenya-ai-agriculture",
    }


def test_liste_vide_ne_plante_pas():
    resultat = deduplicate([])
    assert resultat == []

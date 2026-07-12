from pipeline.filter import score_article


def test_article_africain_ville_et_startup():
    score = score_article(
        titre="How Lagos startup is disrupting fintech in Africa",
        contenu="A new startup based in Lagos, Nigeria is changing the way africans access financial services. This african tech company is a leading tech hub.",
        source_id="techpoint-africa"
    )
    assert score > 50, f"score={score}, attendu > 50"


def test_article_non_africain():
    score = score_article(
        titre="Apple launches new iPhone in California",
        contenu="Apple held its annual keynote in Cupertino, announcing the latest iPhone model.",
        source_id="wired"
    )
    assert score == 0, f"score={score}, attendu == 0"


def test_article_africa_et_ia():
    score = score_article(
        titre="Artificial intelligence is transforming education across Africa",
        contenu="Several african countries are adopting AI tools. Tech hubs in Nairobi and Kigali are leading this transformation.",
        source_id="techcrunch"
    )
    assert score > 30, f"score={score}, attendu > 30"


def test_bonus_source_africaine():
    score = score_article(
        titre="New developer tools released this week",
        contenu="Several new tools were announced for software developers.",
        source_id="techpoint-africa"
    )
    assert score > 0, f"score={score}, attendu > 0"

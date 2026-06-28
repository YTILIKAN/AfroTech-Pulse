# pipeline/filter.py — Filtrage de pertinence africaine (scoring keywords + embeddings)

# pipeline/filter.py

PAYS_AFRICAINS = [
    "nigeria", "kenya", "ghana", "sénégal", "senegal", "cameroun", "cameroon",
    "côte d'ivoire", "ivory coast", "ethiopie", "ethiopia", "tanzanie", "tanzania",
    "ouganda", "uganda", "rwanda", "mozambique", "zimbabwe", "zambie", "zambia",
    "angola", "mali", "burkina faso", "guinée", "guinea", "bénin", "benin",
    "togo", "niger", "tchad", "chad", "soudan", "sudan", "somalie", "somalia",
    "madagascar", "malawi", "namibie", "namibia", "botswana", "gabon",
    "congo", "drc", "rdc", "liberia", "sierra leone", "gambie", "gambia",
    "mauritanie", "mauritania", "djibouti", "érythrée", "eritrea", "lesotho",
    "eswatini", "swaziland", "comores", "comoros", "cap-vert", "cape verde",
    "south africa", "afrique du sud", "egypt", "egypte", "maroc", "morocco",
    "algérie", "algeria", "tunisie", "tunisia", "libye", "libya",
    "africa", "african", "afrique",
]

VILLES_AFRICAINES = [
    "lagos", "nairobi", "accra", "dakar", "cape town", "kigali", "abidjan",
    "addis abeba", "addis ababa", "johannesburg", "cairo", "le caire",
    "casablanca", "tunis", "alger", "algiers", "luanda", "dar es salaam",
    "kampala", "harare", "lusaka", "maputo", "antananarivo", "douala",
    "yaoundé", "yaounde", "bamako", "conakry", "ouagadougou", "niamey",
    "ndjamena", "bangui", "libreville", "brazzaville", "kinshasa", "bujumbura",
    "mogadishu", "mogadiscio", "djibouti", "asmara", "freetown", "monrovia",
    "abuja", "ibadan", "kano", "kumasi", "mombasa", "entebbe", "gaborone",
    "windhoek", "mbabane", "maseru", "porto-novo", "lomé", "lome",
]

ORGANISATIONS_AFRICAINES = [
    "union africaine", "african union", "afdb", "african development bank",
    "banque africaine de développement", "ecowas", "cedeao", "sadc", "igad",
    "smart africa", "au commission", "nepad", "agra", "afreximbank",
    "pan-african", "pan african", "africain", "africa50",
]

TERMES_TECH_AFRICAINS = [
    "african startup", "startup africa", "africa startup",
    "fintech africa", "african fintech", "africa fintech",
    "tech hub", "african tech", "afrotech", "africa tech",
    "silicon savannah", "silicon lagoon", "yabacon valley",
    "african innovation", "innovation africa",
    "africa digital", "digital africa", "african developer",
    "africa mobile", "mobile africa", "africa internet",
]

SOURCES_AFRICAINES = [
    "techpoint", "techcabal", "disrupt-africa", "weetracker",
    "benjamindada", "africanews", "ventures-africa", "itnewsafrica",
    "technext", "techeconomy", "nairobiwire", "bdafrica",
]


def score_article(titre: str, contenu: str, source_id: str) -> int:
    texte = (titre + " " + contenu).lower()
    score = 0

    # +20 si au moins un pays africain est mentionné
    for pays in PAYS_AFRICAINS:
        if pays in texte:
            score += 20
            break

    # +15 si au moins une ville africaine est mentionnée
    for ville in VILLES_AFRICAINES:
        if ville in texte:
            score += 15
            break

    # +15 si au moins une organisation africaine est mentionnée
    for org in ORGANISATIONS_AFRICAINES:
        if org in texte:
            score += 15
            break

    # +10 si au moins un terme tech africain est mentionné
    for terme in TERMES_TECH_AFRICAINS:
        if terme in texte:
            score += 10
            break

    # +10 bonus si la source est africaine
    for src in SOURCES_AFRICAINES:
        if src in source_id.lower():
            score += 10
            break

    return min(score, 100)
 


def _run_tests():
    # Test 1 : article mentionnant "Lagos" + "startup" → score > 50
    s1 = score_article(
        titre="How Lagos startup is disrupting fintech in Africa",
        contenu="A new startup based in Lagos, Nigeria is changing the way africans access financial services. This african tech company is a leading tech hub.",
        source_id="techpoint-africa"
    )
    assert s1 > 50, f"Test 1 ECHOUE : score={s1}, attendu > 50"
    print(f"Test 1 OK — article Lagos+startup : score={s1}")

    # Test 2 : article sur Apple en Californie → score == 0
    s2 = score_article(
        titre="Apple launches new iPhone in California",
        contenu="Apple held its annual keynote in Cupertino, announcing the latest iPhone model.",
        source_id="wired"
    )
    assert s2 == 0, f"Test 2 ECHOUE : score={s2}, attendu == 0"
    print(f"Test 2 OK — article Apple California : score={s2}")

    # Test 3 : article mentionnant "Africa" + "intelligence artificielle" → score > 30
    s3 = score_article(
        titre="Artificial intelligence is transforming education across Africa",
        contenu="Several african countries are adopting AI tools. Tech hubs in Nairobi and Kigali are leading this transformation.",
        source_id="techcrunch"
    )
    assert s3 > 30, f"Test 3 ECHOUE : score={s3}, attendu > 30"
    print(f"Test 3 OK — article Africa+IA : score={s3}")

    # Test 4 : article provenant de techpoint-africa → score > 0 (bonus source)
    s4 = score_article(
        titre="New developer tools released this week",
        contenu="Several new tools were announced for software developers.",
        source_id="techpoint-africa"
    )
    assert s4 > 0, f"Test 4 ECHOUE : score={s4}, attendu > 0"
    print(f"Test 4 OK — source techpoint-africa : score={s4}")

    print("\n4/4 tests passes - OK")


if __name__ == "__main__":
    _run_tests()


 
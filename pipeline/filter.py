# pipeline/filter.py — Filtrage de pertinence africaine

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


def detecter_pays(titre: str, contenu: str) -> str | None:
    """Retourne le premier pays africain détecté dans le texte, ou None."""
    texte = (titre + " " + contenu).lower()
    for pays in PAYS_AFRICAINS:
        if pays in texte:
            return pays
    return None


def score_article(titre: str, contenu: str, source_id: str) -> int:
    texte = (titre + " " + contenu).lower()
    score = 0

    if detecter_pays(titre, contenu):
        score += 20

    for ville in VILLES_AFRICAINES:
        if ville in texte:
            score += 15
            break

    for org in ORGANISATIONS_AFRICAINES:
        if org in texte:
            score += 15
            break

    for terme in TERMES_TECH_AFRICAINS:
        if terme in texte:
            score += 10
            break

    for src in SOURCES_AFRICAINES:
        if src in source_id.lower():
            score += 10
            break

    return min(score, 100)

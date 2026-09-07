# dashboard/enrichment.py — Enrichit chaque article : pays africain mentionné (code ISO-3
# pour la carte choroplèthe) et secteur(s) d'activité.
#
# La détection est volontairement simple (recherche de mots-clés) : rapide, sans dépendance,
# testable. Elle prolonge les listes de pipeline/filter.py avec les codes ISO nécessaires à Plotly.

import re

# --- Pays africains : variantes FR/EN -> (nom canonique, code ISO-3166-1 alpha-3) ---
_PAYS = {
    "algérie": ("Algérie", "DZA"), "algeria": ("Algérie", "DZA"),
    "angola": ("Angola", "AGO"),
    "bénin": ("Bénin", "BEN"), "benin": ("Bénin", "BEN"),
    "botswana": ("Botswana", "BWA"),
    "burkina faso": ("Burkina Faso", "BFA"),
    "burundi": ("Burundi", "BDI"),
    "cameroun": ("Cameroun", "CMR"), "cameroon": ("Cameroun", "CMR"),
    "cap-vert": ("Cap-Vert", "CPV"), "cape verde": ("Cap-Vert", "CPV"),
    "centrafrique": ("Centrafrique", "CAF"), "central african republic": ("Centrafrique", "CAF"),
    "tchad": ("Tchad", "TCD"), "chad": ("Tchad", "TCD"),
    "comores": ("Comores", "COM"), "comoros": ("Comores", "COM"),
    "côte d'ivoire": ("Côte d'Ivoire", "CIV"), "cote d'ivoire": ("Côte d'Ivoire", "CIV"),
    "ivory coast": ("Côte d'Ivoire", "CIV"),
    "rdc": ("RD Congo", "COD"), "drc": ("RD Congo", "COD"),
    "république démocratique du congo": ("RD Congo", "COD"),
    "democratic republic of the congo": ("RD Congo", "COD"),
    "congo-brazzaville": ("Congo", "COG"), "republic of the congo": ("Congo", "COG"),
    "djibouti": ("Djibouti", "DJI"),
    "égypte": ("Égypte", "EGY"), "egypte": ("Égypte", "EGY"), "egypt": ("Égypte", "EGY"),
    "guinée équatoriale": ("Guinée équatoriale", "GNQ"), "equatorial guinea": ("Guinée équatoriale", "GNQ"),
    "érythrée": ("Érythrée", "ERI"), "eritrea": ("Érythrée", "ERI"),
    "eswatini": ("Eswatini", "SWZ"), "swaziland": ("Eswatini", "SWZ"),
    "éthiopie": ("Éthiopie", "ETH"), "ethiopie": ("Éthiopie", "ETH"), "ethiopia": ("Éthiopie", "ETH"),
    "gabon": ("Gabon", "GAB"),
    "gambie": ("Gambie", "GMB"), "gambia": ("Gambie", "GMB"),
    "ghana": ("Ghana", "GHA"),
    "guinée-bissau": ("Guinée-Bissau", "GNB"), "guinea-bissau": ("Guinée-Bissau", "GNB"),
    "guinée": ("Guinée", "GIN"), "guinea": ("Guinée", "GIN"),
    "kenya": ("Kenya", "KEN"),
    "lesotho": ("Lesotho", "LSO"),
    "liberia": ("Libéria", "LBR"), "libéria": ("Libéria", "LBR"),
    "libye": ("Libye", "LBY"), "libya": ("Libye", "LBY"),
    "madagascar": ("Madagascar", "MDG"),
    "malawi": ("Malawi", "MWI"),
    "mali": ("Mali", "MLI"),
    "mauritanie": ("Mauritanie", "MRT"), "mauritania": ("Mauritanie", "MRT"),
    "maurice": ("Maurice", "MUS"), "mauritius": ("Maurice", "MUS"),
    "maroc": ("Maroc", "MAR"), "morocco": ("Maroc", "MAR"),
    "mozambique": ("Mozambique", "MOZ"),
    "namibie": ("Namibie", "NAM"), "namibia": ("Namibie", "NAM"),
    "niger": ("Niger", "NER"),
    "nigéria": ("Nigéria", "NGA"), "nigeria": ("Nigéria", "NGA"),
    "ouganda": ("Ouganda", "UGA"), "uganda": ("Ouganda", "UGA"),
    "rwanda": ("Rwanda", "RWA"),
    "sao tomé": ("Sao Tomé-et-Principe", "STP"), "sao tome": ("Sao Tomé-et-Principe", "STP"),
    "sénégal": ("Sénégal", "SEN"), "senegal": ("Sénégal", "SEN"),
    "seychelles": ("Seychelles", "SYC"),
    "sierra leone": ("Sierra Leone", "SLE"),
    "somalie": ("Somalie", "SOM"), "somalia": ("Somalie", "SOM"), "somaliland": ("Somalie", "SOM"),
    "afrique du sud": ("Afrique du Sud", "ZAF"), "south africa": ("Afrique du Sud", "ZAF"),
    "soudan du sud": ("Soudan du Sud", "SSD"), "south sudan": ("Soudan du Sud", "SSD"),
    "soudan": ("Soudan", "SDN"), "sudan": ("Soudan", "SDN"),
    "tanzanie": ("Tanzanie", "TZA"), "tanzania": ("Tanzanie", "TZA"),
    "togo": ("Togo", "TGO"),
    "tunisie": ("Tunisie", "TUN"), "tunisia": ("Tunisie", "TUN"),
    "zambie": ("Zambie", "ZMB"), "zambia": ("Zambie", "ZMB"),
    "zimbabwe": ("Zimbabwe", "ZWE"),
}

# Villes -> pays (une mention de ville vaut une mention du pays).
_VILLES = {
    "lagos": "NGA", "abuja": "NGA", "ibadan": "NGA", "kano": "NGA", "port harcourt": "NGA",
    "nairobi": "KEN", "mombasa": "KEN",
    "accra": "GHA", "kumasi": "GHA",
    "dakar": "SEN",
    "abidjan": "CIV",
    "le caire": "EGY", "cairo": "EGY",
    "casablanca": "MAR", "rabat": "MAR",
    "tunis": "TUN",
    "alger": "DZA", "algiers": "DZA",
    "johannesburg": "ZAF", "cape town": "ZAF", "le cap": "ZAF", "pretoria": "ZAF", "durban": "ZAF",
    "kigali": "RWA",
    "addis abeba": "ETH", "addis ababa": "ETH",
    "kampala": "UGA",
    "dar es salaam": "TZA", "dodoma": "TZA",
    "lusaka": "ZMB",
    "harare": "ZWE",
    "maputo": "MOZ",
    "luanda": "AGO",
    "kinshasa": "COD", "lubumbashi": "COD",
    "douala": "CMR", "yaoundé": "CMR", "yaounde": "CMR",
    "bamako": "MLI",
    "ouagadougou": "BFA",
    "cotonou": "BEN",
    "lomé": "TGO", "lome": "TGO",
    "niamey": "NER",
    "conakry": "GIN",
    "antananarivo": "MDG",
    "gaborone": "BWA",
    "windhoek": "NAM",
    "freetown": "SLE",
    "monrovia": "LBR",
    "nouakchott": "MRT",
}

_NOM_PAR_ISO = {iso: nom for nom, iso in _PAYS.values()}

# Terme (pays ou ville) -> ISO-3, trié du plus long au plus court pour que l'alternation
# regex privilégie "guinée équatoriale" sur "guinée", "soudan du sud" sur "soudan", etc.
_TERME_VERS_ISO = {terme: iso for terme, (_nom, iso) in _PAYS.items()}
_TERME_VERS_ISO.update(_VILLES)
_TERMES_TRIES = sorted(_TERME_VERS_ISO, key=len, reverse=True)

_BORD = r"(?<![a-zàâäéèêëïîôöùûüç0-9])"
_BORD_FIN = r"(?![a-zàâäéèêëïîôöùûüç0-9])"

_RE_PAYS = re.compile(
    _BORD + "(" + "|".join(re.escape(t) for t in _TERMES_TRIES) + ")" + _BORD_FIN
)

# --- Secteurs : mots-clés FR + EN (recherche sur mot entier, insensible à la casse) ---
# ⚠️ Éviter les mots qui collisionnent avec le vocabulaire IA générique : "learning"
# ("machine learning"), "apprentissage" ("apprentissage automatique/profond"),
# "formation" ("formation d'un modèle"), "prêt" ("prêt à"), "culture" (société).
SECTEURS_MOTS_CLES = {
    "fintech": [
        "fintech", "mobile money", "mobile-money", "paiement", "paiements", "payment",
        "payments", "banque", "bancaire", "banking", "crypto", "cryptomonnaie", "wallet",
        "lending", "microfinance", "microcrédit", "crédit", "remittance",
        "transfert d'argent", "assurtech", "insurtech", "néobanque", "neobank",
    ],
    "santé": [
        "santé", "health", "healthcare", "healthtech", "médical", "médicale", "medical",
        "médecine", "medicine", "hôpital", "hospital", "clinique", "clinic",
        "diagnostic", "diagnosis", "patient", "patients", "pharma", "pharmaceutical",
        "vaccin", "vaccine", "maladie", "disease", "télémédecine", "telemedicine", "biotech",
    ],
    "éducation": [
        "éducation", "éducatif", "éducative", "education", "educational", "edtech",
        "école", "écoles", "school", "schools", "scolaire", "université", "universitaire",
        "university", "universities", "e-learning", "cours en ligne", "mooc",
        "étudiant", "étudiants", "student", "students", "enseignant", "enseignants",
        "enseignement", "teacher", "teachers", "curriculum", "pédagogique",
        "littératie", "literacy", "alphabétisation",
    ],
    "agriculture": [
        "agriculture", "agricole", "agritech", "agtech", "agrifood", "agri-food",
        "farm", "farming", "farmer", "farmers", "agriculteur", "agriculteurs",
        "récolte", "récoltes", "harvest", "élevage", "livestock", "crop", "crops",
        "irrigation", "food security", "sécurité alimentaire", "agribusiness", "rural",
    ],
}

# Indice tiré de la catégorie de data/sources.json (source_id ou catégorie).
_CATEGORIE_SECTEUR = {
    "fintech": "fintech",
}

SECTEUR_DEFAUT = "généraliste"

_RE_SECTEUR = {
    secteur: re.compile(
        _BORD + "(" + "|".join(re.escape(m) for m in sorted(mots, key=len, reverse=True))
        + ")" + _BORD_FIN
    )
    for secteur, mots in SECTEURS_MOTS_CLES.items()
}


def _texte(*parties):
    return " ".join(p for p in parties if p).lower()


def detecter_pays(titre, contenu="", resume=""):
    """Retourne (nom_pays, code_iso3) du premier pays africain détecté, ou None.
    Le titre est prioritaire sur le corps. Les termes génériques ('africa', 'african')
    ne comptent pas comme un pays."""
    for texte in (titre.lower() if titre else "", _texte(contenu, resume)):
        if not texte:
            continue
        m = _RE_PAYS.search(texte)
        if m:
            iso = _TERME_VERS_ISO[m.group(1)]
            return (_NOM_PAR_ISO[iso], iso)
    return None


def classer_secteurs(titre, contenu="", resume="", categorie=""):
    """Retourne la liste des secteurs de l'article (peut être multiple).
    Jamais vide : si rien n'est détecté, retourne [SECTEUR_DEFAUT]."""
    texte = _texte(titre, contenu, resume)
    secteurs = [
        secteur for secteur, motif in _RE_SECTEUR.items() if motif.search(texte)
    ]

    indice = _CATEGORIE_SECTEUR.get((categorie or "").strip().lower())
    if indice and indice not in secteurs:
        secteurs.append(indice)

    return secteurs or [SECTEUR_DEFAUT]


def enrichir(articles):
    """Ajoute pays_nom, pays_iso et secteurs à chaque article (copie, n'altère pas l'entrée)."""
    enrichis = []
    for a in articles:
        pays = detecter_pays(a.get("titre", ""), a.get("contenu", ""), a.get("resume", ""))
        enrichis.append(
            {
                **a,
                "pays_nom": pays[0] if pays else None,
                "pays_iso": pays[1] if pays else None,
                "secteurs": classer_secteurs(
                    a.get("titre", ""), a.get("contenu", ""), a.get("resume", ""),
                    a.get("categorie", ""),
                ),
            }
        )
    return enrichis

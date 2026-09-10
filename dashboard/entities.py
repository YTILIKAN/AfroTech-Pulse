# dashboard/entities.py — Extraction des « acteurs » (entreprises, organisations) cités.
#
# Approche volontairement légère : repérage des séquences capitalisées, puis soustraction
# de listes d'exclusion. Pas de modèle NER — spaCy ajouterait ~500 Mo de dépendances et un
# téléchargement de modèle pour un dashboard qui doit rester déployable sans réseau.
# Le prix à payer est assumé : il reste des faux positifs résiduels, et les tests épinglent
# les familles connues (débuts de phrase, pays, noms de sources).

import json
import re
from pathlib import Path

from dashboard.enrichment import _PAYS, _VILLES
from dashboard.text import STOPWORDS, nettoyer

CHEMIN_SOURCES = Path(__file__).resolve().parent.parent / "data" / "sources.json"

# Catégories de data/sources.json qui désignent des **médias**. Pour celles-là, chaque mot
# du nom est exclu : dans le texte, une source apparaît rarement sous son nom exact
# (« Nairametrics Tech » dans le JSON, « Nairametrics » dans l'article ; « TechTrends Kenya »
# vs « TechTrendsKE »). Les autres catégories (Recherche IA, Startups, Institutions…) sont
# des **acteurs** autant que des sources — InstaDeep, Lelapa, Masakhane, GSMA, McKinsey —
# et ne perdent que leur nom complet.
CATEGORIES_MEDIAS = {"tech afrique", "grands médias", "podcasts"}

# Rattrapages manuels : acteurs réels rangés dans une catégorie média (Partech est un fonds
# d'investissement, pas un journal). À compléter si l'équipe en repère d'autres.
ACTEURS_AUTORISES = {"partech"}

# Gentilés : « Nigerian », « Kényane »… désignent un pays déjà porté par la carte,
# pas un acteur.
_GENTILES = {
    "african", "africaine", "africain", "africains", "africaines",
    "nigerian", "nigerians", "nigérian", "nigériane", "kenyan", "kenyans", "kényan",
    "kényane", "ghanaian", "ghanéen", "ghanéenne", "egyptian", "égyptien", "égyptienne",
    "moroccan", "marocain", "marocaine", "ethiopian", "éthiopien", "rwandan", "rwandais",
    "senegalese", "sénégalais", "ivorian", "ivoirien", "tanzanian", "tanzanien",
    "ugandan", "ougandais", "zambian", "zambien", "zimbabwean", "zimbabwéen",
    "tunisian", "tunisien", "algerian", "algérien", "cameroonian", "camerounais",
    "sud-africain", "sud-africaine",
}

_MOIS = {
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
    "octobre", "novembre", "décembre",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}

# Mots qui ouvrent très souvent une phrase ou un titre et ressortent capitalisés sans
# désigner personne.
_AMORCES = {
    "the", "this", "these", "that", "there", "here", "with", "without", "after", "before",
    "how", "why", "what", "when", "where", "who", "new", "top", "best", "first", "last",
    "next", "more", "most", "many", "some", "several", "according", "despite", "amid",
    "le", "la", "les", "un", "une", "des", "ce", "cette", "ces", "dans", "avec", "sans",
    "après", "avant", "comment", "pourquoi", "selon", "malgré", "voici", "plus", "moins",
    "nouveau", "nouvelle", "premier", "première", "dernier", "dernière",
    "however", "yet", "across", "while", "although", "though", "meanwhile", "moreover",
    "furthermore", "instead", "since", "unlike", "beyond", "within", "between", "during",
    "two", "three", "four", "five", "both", "each", "every", "other", "another", "such",
    "cependant", "toutefois", "néanmoins", "ainsi", "désormais", "aujourd'hui", "deux",
    "trois", "quatre", "cinq", "autre", "autres", "chaque", "plusieurs",
    "finally", "continue", "additionally", "notably", "importantly", "overall",
    "recently", "currently", "previously", "following", "including", "given",
    "enfin", "récemment", "actuellement", "notamment", "suite",
    "a", "an", "of", "in", "on", "at", "to", "for", "no", "so", "as", "by",
    "six", "seven", "eight", "nine", "ten", "hundred", "thousand",
    "founded", "second", "third", "fourth", "launched", "based", "led", "backed",
    "fondé", "fondée", "lancé", "lancée", "deuxième", "troisième",
}

# Titres et fonctions : « CEO », « Chief Executive Officer » ne nomment pas un acteur.
_FONCTIONS = {
    "ceo", "cto", "coo", "cfo", "chief executive", "chief executive officer",
    "managing director", "founder", "co-founder", "cofounder", "fondateur",
    "directeur général", "directrice générale", "président directeur",
    "vice president", "vice-président", "spokesperson", "porte-parole",
}

# Régions et ensembles géographiques : déjà portés par la carte, jamais des acteurs.
_REGIONS = {
    "east africa", "west africa", "north africa", "southern africa", "central africa",
    "east african", "west african", "north african", "sub-saharan africa", "sub saharan",
    "sub-saharan", "subsaharan africa", "afrique de l'ouest", "afrique de l'est",
    "afrique centrale", "afrique australe", "afrique subsaharienne", "afrique du nord",
    "middle east", "moyen-orient", "democratic republic", "république démocratique",
    "united states", "états-unis", "european union", "union européenne",
    "congo", "dr congo", "ceuta", "melilla", "sahel", "maghreb", "corne de l'afrique",
    # Géographie hors Afrique : contexte d'un article, jamais l'acteur qu'on classe ici.
    "china", "chine", "europe", "asia", "asie", "india", "inde", "japan", "japon",
    "brazil", "brésil", "canada", "germany", "allemagne", "united kingdom", "royaume-uni",
    "america", "amérique", "australia", "australie", "russia", "russie", "israel",
    "israël", "turkey", "turquie", "singapore", "singapour", "dubai", "dubaï",
    "africans", "europeans", "americans", "russian", "russians", "spanish", "chinese",
    "french", "british", "american", "indian", "européen", "européenne", "américain",
    "américaine", "chinois", "chinoise", "russe", "espagnol", "français", "française",
}

# Habillage des flux RSS : arXiv préfixe chaque contenu par « arXiv:XXXX Announce Type: new
# / Abstract: … », d'autres flux ajoutent « Source », « Read More », « Featured »…
_BOILERPLATE = {
    "abstract", "announce", "announce type", "type", "source", "sources", "arxiv",
    "read more", "read", "more", "continue reading", "featured", "featuredvisual",
    "latest", "share", "comments", "advertisement", "sponsored", "image", "photo",
    "credit", "getty", "reuters", "afp", "subscribe", "newsletter", "copyright",
}

# Noms communs fréquemment capitalisés dans les titres, qui ne désignent personne seuls.
_NOMS_COMMUNS = {
    "business", "bank", "central bank", "government", "gouvernement", "ministry",
    "ministère", "president", "président", "minister", "ministre", "politics",
    "politique", "financial", "finance", "market", "markets", "marché", "company",
    "companies", "entreprise", "entreprises", "group", "groupe", "report", "rapport",
    "study", "étude", "project", "projet", "programme", "program", "summit", "sommet",
    "conference", "conférence", "award", "awards", "prix", "million", "milliard",
    "billion", "percent", "data", "données", "internet", "mobile", "digital",
    "numérique", "innovation", "research", "recherche", "university", "université",
    "school", "école", "health", "santé", "education", "éducation", "agriculture",
    "energy", "énergie", "climate", "climat", "security", "sécurité", "development",
    "développement", "investment", "investissement", "funding", "financement",
    "authority", "autorité", "collaboration", "partnership", "partenariat", "head",
    "team", "équipe", "board", "conseil", "council", "agency", "agence", "commission",
    "association", "federation", "fédération", "institute", "institut", "center",
    "centre", "network", "réseau", "platform", "plateforme", "service", "services",
    "solution", "solutions", "system", "systems", "système", "coding school",
    "school", "startup hub", "hub", "lab", "labs", "laboratoire",
    # Vocabulaire arXiv qui remonte des papiers de recherche du corpus.
    "gaussian", "transformer", "transformers", "neural", "benchmark", "dataset",
    "datasets", "model", "models", "modèle", "modèles", "framework", "algorithm",
    "algorithme", "training", "inference",
    # Santé : nommées dans les articles, mais ce ne sont pas des acteurs.
    "ebola", "covid", "covid-19", "malaria", "paludisme", "hiv", "vih", "mpox",
    "tuberculosis", "tuberculose", "cholera", "choléra",
    "learning", "today", "yesterday", "tomorrow", "women", "men", "youth", "jeunes",
    "years", "year", "année", "années", "week", "semaine", "month", "mois",
    "people", "population", "citizens", "citoyens", "users", "utilisateurs",
    "world", "monde", "future", "avenir", "growth", "croissance", "future of work",
}

# Adjectifs composés capitalisés en tête de titre : « AI-powered », « Africa-focused ».
_SUFFIXES_ADJECTIFS = (
    "-powered", "-based", "-driven", "-led", "-backed", "-focused", "-owned", "-born",
    "-native", "-first", "-ready", "-enabled", "-related",
)

# Plateformes : citées partout, ne disent rien sur un acteur du secteur.
_PLATEFORMES = {
    "twitter", "linkedin", "facebook", "instagram", "youtube", "whatsapp", "telegram",
    "tiktok", "github",
}

LONGUEUR_MIN = 3
LIMITE_DEFAUT = 15

# La borne gauche empêche de capturer un fragment interne : sans elle, « arXiv:2607 »
# produit l'entité « Xiv ».
_RE_ENTITE = re.compile(
    r"(?<![A-Za-zÀ-ÿ0-9])"
    r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿ0-9&.'’-]*(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÿ0-9&.'’-]*){0,2}"
)
_RE_ESPACES = re.compile(r"\s+")
# Noms de domaine (« ITPulse.com.ng ») : une source, pas un acteur.
_RE_DOMAINE = re.compile(r"\.(com|net|org|ng|ke|za|gh|ci|sn|ma|tn|eg|io|ai|co|fr|africa)\b")
# Sigles courts (« CEO », « KES », « AFC », « LLM ») : trop ambigus. À 4 lettres et plus on
# garde (« GSMA », « UNDP », « AFDB » sont de vraies organisations).
LONGUEUR_MIN_SIGLE = 4


def _normaliser(candidat):
    """Forme comparable : espaces compressés, ponctuation de bord retirée, minuscules."""
    return _RE_ESPACES.sub(" ", candidat).strip(" .,;:!?&'’-").lower()


def charger_exclusions_sources(chemin=None):
    """(noms complets, tokens) à exclure, construits depuis data/sources.json.

    Le **nom complet** de chaque source est toujours exclu. Les **tokens** ne le sont que
    pour les catégories médias (cf. CATEGORIES_MEDIAS) et pour les noms tenant en un seul
    mot : exclure tous les tokens de tous les noms composés détruirait de vrais acteurs —
    InstaDeep, Lelapa, Masakhane, GSMA sont à la fois des sources et des acteurs majeurs
    de l'IA africaine, précisément ce que « top acteurs » doit faire remonter.
    """
    chemin = Path(chemin) if chemin else CHEMIN_SOURCES
    with open(chemin, "r", encoding="utf-8") as f:
        sources = json.load(f)["sources"]

    noms_complets = set()
    tokens = set()
    for source in sources:
        nom = _normaliser(source.get("name", ""))
        if not nom:
            continue
        noms_complets.add(nom)

        mots = nom.split()
        media = _normaliser(source.get("category", "")) in CATEGORIES_MEDIAS
        if len(mots) == 1 or media:
            tokens.update(mots)
        # L'identifiant porte souvent la forme courte réellement citée dans les articles
        # (« techtrends-kenya » -> « techtrends », qui apparaît en « TechTrendsKE »).
        if media:
            tokens.update(m for m in _normaliser(source.get("id", "")).split("-") if m)

    tokens -= ACTEURS_AUTORISES
    noms_complets -= ACTEURS_AUTORISES
    return noms_complets, tokens


def charger_prefixes_medias(chemin=None):
    """Tokens de médias servant de préfixe pour rattraper les formes collées.

    Les flux citent parfois leur propre marque sans séparateur (« TechTrendsKE » pour la
    source « TechTrends Kenya »), forme qu'aucune liste d'exclusion exacte ne peut prévoir.
    """
    _noms, tokens = charger_exclusions_sources(chemin)
    return {t for t in tokens if len(t) >= 5}


def construire_exclusions(chemin_sources=None):
    """Ensemble complet des formes normalisées à ne jamais retenir comme acteur."""
    noms_sources, tokens_sources = charger_exclusions_sources(chemin_sources)
    return (
        set(_PAYS)            # pays, variantes FR/EN
        | set(_VILLES)        # villes : déjà portées par la carte
        | _REGIONS
        | _GENTILES
        | _MOIS
        | _AMORCES
        | _BOILERPLATE
        | _NOMS_COMMUNS
        | _PLATEFORMES
        | _FONCTIONS
        | STOPWORDS
        | noms_sources
        | tokens_sources
    ) - ACTEURS_AUTORISES


def _sequences(brut):
    """Découpe une suite capitalisée en séquences ne franchissant pas de fin de phrase.

    Sans ça, « ITPulse.com.ng. GSMA publie » forme un seul candidat : le domaine fait
    rejeter l'ensemble et GSMA disparaît avec lui.
    """
    courante = []
    for mot in _RE_ESPACES.sub(" ", brut).strip().split():
        courante.append(mot)
        if mot.endswith("."):
            yield courante
            courante = []
    if courante:
        yield courante


def _retenir(mots, exclusions, prefixes_medias):
    """(forme normalisée, forme affichée) si la séquence est un acteur plausible, sinon None."""
    # « The Nigerian startup Flutterwave » → on retire les amorces de bord plutôt que de
    # jeter la séquence entière.
    while mots and _normaliser(mots[0]) in _AMORCES:
        mots = mots[1:]
    while mots and _normaliser(mots[-1]) in _AMORCES:
        mots = mots[:-1]
    if not mots:
        return None

    normalise = _normaliser(" ".join(mots))
    if not normalise or normalise in exclusions:
        return None
    if len(normalise.replace(" ", "")) < LONGUEUR_MIN:
        return None
    if normalise.replace(" ", "").isdigit():
        return None
    if _RE_DOMAINE.search(normalise):
        return None
    if normalise.endswith(_SUFFIXES_ADJECTIFS):
        return None

    # Sigle court : « CEO », « KES », « AFC » sont ambigus, « GSMA » ne l'est pas.
    # Le « s » de pluriel est retiré avant la mesure, pour attraper « SMEs ».
    colle = "".join(mots).rstrip(".")
    sigle = colle[:-1] if colle.endswith("s") else colle
    if sigle.isupper() and len(sigle) < LONGUEUR_MIN_SIGLE:
        return None

    # Forme collée d'un média : « TechTrendsKE » pour la source « TechTrends Kenya ».
    if len(mots) == 1 and any(normalise.startswith(t) for t in prefixes_medias):
        return None

    # Séquence dont chaque mot est lui-même exclu (« South Africa », « Le Kenya ») :
    # aucun acteur là-dedans.
    if all(_normaliser(mot) in exclusions for mot in mots):
        return None

    return normalise, " ".join(mots).rstrip(".")


def _candidats(texte, exclusions, prefixes_medias=()):
    for brut in _RE_ENTITE.findall(texte or ""):
        for mots in _sequences(brut):
            retenu = _retenir(mots, exclusions, prefixes_medias)
            if retenu is not None:
                yield retenu


def extraire_entites(
    articles, limite=LIMITE_DEFAUT, exclusions=None, prefixes_medias=None, chemin_sources=None
):
    """[(nom affiché, nombre d'articles)] des acteurs les plus cités.

    Un acteur compte **une fois par article**, pas une fois par mention : un communiqué
    qui répète dix fois le même nom ne doit pas écraser le classement.
    """
    if exclusions is None:
        exclusions = construire_exclusions(chemin_sources)
    if prefixes_medias is None:
        prefixes_medias = charger_prefixes_medias(chemin_sources)

    comptes = {}
    formes = {}
    for article in articles:
        # Séparateur de phrase entre les champs : sans lui, le titre « Actu » et le début
        # du contenu « Safaricom annonce… » forment la fausse entité « Actu Safaricom ».
        texte = nettoyer(" . ".join(
            p for p in (
                article.get("titre", ""),
                article.get("resume", ""),
                article.get("contenu", ""),
            ) if p
        ))
        vus = set()
        for normalise, forme in _candidats(texte, exclusions, prefixes_medias):
            formes.setdefault(normalise, {})
            formes[normalise][forme] = formes[normalise].get(forme, 0) + 1
            if normalise not in vus:
                vus.add(normalise)
                comptes[normalise] = comptes.get(normalise, 0) + 1

    classement = sorted(comptes.items(), key=lambda kv: (-kv[1], kv[0]))[:limite]
    return [
        (max(formes[normalise].items(), key=lambda kv: kv[1])[0], n)
        for normalise, n in classement
    ]

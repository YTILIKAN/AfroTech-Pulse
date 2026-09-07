# dashboard/text.py — Préparation du texte pour le nuage de mots.
#
# Les stopwords sont codés en dur plutôt que tirés de nltk : nltk.download('stopwords')
# exige un accès réseau au premier lancement, ce qu'un dashboard public ne doit pas
# supposer. Même parti pris que pipeline/filter.py et dashboard/enrichment.py, qui
# portent aussi leurs listes de mots-clés en dur.

import html
import re

# --- Stopwords français ---
_STOPWORDS_FR = {
    "alors", "au", "aucun", "aussi", "autre", "autres", "aux", "avait", "avant", "avec",
    "avoir", "bon", "car", "ce", "cela", "ces", "cet", "cette", "ceux", "chaque", "chez",
    "comme", "comment", "dans", "de", "des", "deux", "doit", "donc", "dont", "du", "elle",
    "elles", "en", "encore", "entre", "est", "et", "eu", "fait", "faire", "fois", "font",
    "hors", "ici", "il", "ils", "je", "juste", "la", "le", "les", "leur", "leurs", "lui",
    "là", "ma", "mais", "me", "mes", "moins", "mon", "même", "mêmes", "ne", "ni", "non",
    "nos", "notre", "nous", "nouveau", "nouvelle", "on", "ont", "ou", "où", "par", "parce",
    "pas", "peu", "peut", "peuvent", "plus", "plupart", "pour", "pourquoi", "près", "quand",
    "que", "quel", "quelle", "quelles", "quels", "qui", "quoi", "sa", "sans", "se", "sera",
    "ses", "seulement", "si", "sien", "son", "sont", "sous", "soyez", "sujet", "sur", "ta",
    "tandis", "tels", "tes", "ton", "tous", "tout", "toute", "toutes", "trop", "très", "tu",
    "un", "une", "vers", "voit", "vont", "vos", "votre", "vous", "étaient", "état", "étée",
    "être", "déjà", "après", "ainsi", "cela", "celui", "depuis", "selon", "aujourd", "hui",
}

# --- Stopwords anglais : la majorité des titres collectés sont en anglais ---
_STOPWORDS_EN = {
    "about", "above", "after", "again", "against", "all", "also", "among", "and", "any",
    "are", "aren", "because", "been", "before", "being", "below", "between", "both", "but",
    "can", "could", "did", "does", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "her", "here", "hers", "him", "his",
    "how", "into", "its", "itself", "just", "more", "most", "much", "must", "new", "nor",
    "not", "now", "off", "once", "one", "only", "other", "others", "our", "ours", "out",
    "over", "own", "same", "says", "she", "should", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "then", "there", "these", "they", "this", "those", "through",
    "too", "under", "until", "use", "used", "using", "very", "was", "way", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will", "with", "would", "you",
    "your", "yours", "get", "got", "make", "makes", "made", "may", "might", "top", "via",
}

# --- Bruit métier ---
# Le corpus porte *par construction* sur l'IA en Afrique : ces mots écrasent le nuage
# sans rien apprendre. Les retirer laisse remonter les vrais sujets de la période.
MOTS_BRUIT = {
    "ia", "ai", "intelligence", "artificielle", "artificial", "artificiel",
    "afrique", "africa", "african", "africaine", "africains", "africaines", "africain",
    "tech", "technologie", "technologies", "technology", "technologies", "technological",
    "article", "articles", "news", "actualité", "actualités", "read", "lire",
    "startup", "startups",
    # Résidus de balisage : les flux RSS livrent du HTML, et certains encodent deux fois.
    "https", "http", "href", "www", "com", "org", "net", "rel", "nofollow", "target",
    "blank", "src", "img", "span", "div", "class", "style", "amp", "quot", "nbsp",
    "gt", "lt", "utm", "feedburner", "rsquo", "lsquo", "ldquo", "rdquo", "hellip",
    # Pied de page systématique de nombreux flux : « The post X appeared first on Y ».
    "post", "posts", "appeared", "first", "continue", "reading", "via",
    # Gabarit des flux arXiv : « arXiv:XXXX Announce Type: new / Abstract: … ».
    "arxiv", "announce", "abstract", "type", "types", "source", "sources", "subjects",
    # Chevilles de récit, très fréquentes et sans valeur de tendance.
    "across", "two", "three", "four", "five", "years", "year", "week", "weeks",
    "month", "months", "day", "days", "time", "times", "said", "says", "told",
    "according", "including", "also", "however", "while", "since", "well",
}

STOPWORDS = _STOPWORDS_FR | _STOPWORDS_EN | MOTS_BRUIT

LONGUEUR_MIN = 3

# Les apostrophes sont coupées avant tokenisation : « l'intelligence » doit donner
# « intelligence », pas « l'intelligence ».
_APOSTROPHES = str.maketrans({"'": " ", "’": " ", "`": " "})
_RE_MOT = re.compile(r"[a-zà-öø-ÿ][a-zà-öø-ÿ0-9-]*")

_RE_BALISE = re.compile(r"<[^>]+>")
_RE_URL = re.compile(r"https?://\S+|www\.\S+")
_RE_POSSESSIF = re.compile(r"['’]s\b")


def nettoyer(texte):
    """Prépare un texte de flux RSS : entités HTML décodées, balises, URLs et possessifs retirés.

    Les flux livrent du HTML brut (`<a href="https://…" rel="nofollow">`) et certains
    double-encodent leurs entités. Sans ce nettoyage, « href », « https » et « nofollow »
    arrivent en tête du nuage de mots, et « Kenya&amp;rsquo;s » produit l'entité « Kenya& ».
    """
    if not texte:
        return ""
    texte = html.unescape(html.unescape(texte))
    texte = _RE_BALISE.sub(" ", texte)
    texte = _RE_URL.sub(" ", texte)
    return _RE_POSSESSIF.sub("", texte)


def texte_article(article):
    """Texte retenu pour le nuage : titre + résumé + contenu.

    Le champ `resume` (rédigé par le LLM) ne couvre que ~3 % des articles collectés :
    s'y limiter donnerait un nuage construit sur les seuls titres. `contenu` (l'extrait
    RSS) est renseigné sur la quasi-totalité du corpus et prend le relais.
    """
    return nettoyer(" ".join(
        p for p in (
            article.get("titre", ""),
            article.get("resume", ""),
            article.get("contenu", ""),
        ) if p
    ))


def tokeniser(texte, stopwords=None, longueur_min=LONGUEUR_MIN, prefixes_exclus=()):
    """Mots normalisés d'un texte, stopwords et mots trop courts retirés.

    `prefixes_exclus` rattrape les marques de médias soudées à un suffixe
    (« techtrendske » pour la source « TechTrends Kenya »), qu'aucune liste exacte
    ne peut anticiper.
    """
    stopwords = STOPWORDS if stopwords is None else stopwords
    mots = _RE_MOT.findall(texte.lower().translate(_APOSTROPHES))
    return [
        mot for mot in mots
        if len(mot) >= longueur_min
        and mot not in stopwords
        and not any(mot.startswith(p) for p in prefixes_exclus)
    ]


def compter_mots(articles, stopwords=None, longueur_min=LONGUEUR_MIN, prefixes_exclus=()):
    """{mot: fréquence} sur l'ensemble des articles fournis.

    Retourne un dict simple (et non un Counter) : c'est ce qu'attend
    WordCloud.generate_from_frequencies().
    """
    frequences = {}
    for article in articles:
        for mot in tokeniser(texte_article(article), stopwords, longueur_min, prefixes_exclus):
            frequences[mot] = frequences.get(mot, 0) + 1
    return frequences

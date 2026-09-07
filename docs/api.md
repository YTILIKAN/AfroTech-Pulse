# Référence API — AfroTech Pulse

Toutes les fonctions publiques de `database.py`, `pipeline/`, `publisher/` et
`archive/search.py`. Pour la vue d'ensemble et l'enchaînement des étapes, voir
[architecture.md](architecture.md).

Les exemples supposent qu'on travaille depuis la racine du projet, environnement virtuel
activé. Ceux qui écrivent en base sont à exécuter sur une base de test, pas sur
`afrotech.db` : les fonctions ci-dessous ne demandent aucune confirmation.

---

## Sommaire

- [database.py](#databasepy)
- [pipeline/filter.py](#pipelinefilterpy)
- [pipeline/dedup.py](#pipelinededuppy)
- [pipeline/summarize.py](#pipelinesummarizepy)
- [pipeline/editor.py](#pipelineeditorpy)
- [pipeline/run_summarize.py](#pipelinerun_summarizepy)
- [pipeline/run_editor.py](#pipelinerun_editorpy)
- [publisher/publish.py](#publisherpublishpy)
- [publisher/telegram_client.py](#publishertelegram_clientpy)
- [publisher/email_client.py](#publisheremail_clientpy)
- [publisher/run_publish.py](#publisherrun_publishpy)
- [archive/search.py](#archivesearchpy)

---

## database.py

Toutes les fonctions ouvrent et referment leur propre connexion SQLite sur
`database.DB_PATH`. Aucune connexion n'est partagée entre appels.

### Constantes

| Nom | Valeur | Rôle |
|---|---|---|
| `DB_PATH` | `"afrotech.db"` | Chemin de la base. Les tests le remplacent par un fichier temporaire. |
| `SEUIL_PERTINENCE` | `40` | Score minimum pour qu'un article soit résumé puis sélectionnable. |
| `TRANSITIONS_AUTORISEES` | dict | Machine à états des newsletters. |
| `CANAUX_PUBLICATION` | `("telegram",)` | Canaux actifs. `"email"` est retiré tant que le domaine n'est pas vérifié. |
| `STATUTS_PUBLICATION_CANAL` | `{"en_attente", "publié", "echec"}` | Valeurs admises par canal. |

### `creer_base()`

Crée les tables si elles n'existent pas et applique les migrations de colonnes.

| | |
|---|---|
| **Paramètres** | aucun |
| **Retour** | `None` |

Idempotent, à appeler au début de chaque point d'entrée. Les colonnes ajoutées après coup
(`score_pertinence`, `resume`, `score_editorial`, `selectionne`) sont détectées via
`PRAGMA table_info` puis créées si absentes — faire évoluer le schéma ne demande pas de
script de migration.

```python
import database
database.creer_base()
```

### `sauvegarder_article(titre, url, source_id, date_pub, contenu, score_pertinence)`

Insère un article collecté, sans écraser un article déjà présent.

| Paramètre | Type | Description |
|---|---|---|
| `titre` | `str` | Titre de l'article |
| `url` | `str` | Url canonique — **clé d'unicité** |
| `source_id` | `str` | Identifiant de la source dans `data/sources.json` |
| `date_pub` | `str \| None` | Date de publication ISO 8601 |
| `contenu` | `str` | Extrait ou corps de l'article |
| `score_pertinence` | `int` | Score africain 0–100 issu de `score_article()` |

**Retour** — `None`. `date_collecte` est horodatée automatiquement en UTC.

`INSERT OR IGNORE` sur `url` : recollecter un article ne lui fait perdre ni son résumé ni
son score éditorial.

```python
database.sauvegarder_article(
    titre="Une fintech kényane lève 20 M$",
    url="https://exemple.com/fintech-kenya",
    source_id="techpoint-africa",
    date_pub="2026-09-01T09:00:00",
    contenu="La startup annonce une levée de fonds…",
    score_pertinence=55,
)
```

### `sauvegarder_resume(url, resume)`

Enregistre le résumé LLM d'un article.

| Paramètre | Type | Description |
|---|---|---|
| `url` | `str` | Article ciblé |
| `resume` | `str` | Résumé en 3 lignes produit par Gemini |

**Retour** — `None`. Seule la colonne `resume` est touchée.

```python
database.sauvegarder_resume("https://exemple.com/fintech-kenya", "Trois lignes de résumé.")
```

### `sauvegarder_newsletter(contenu, nb_articles, statut="brouillon")`

Insère une newsletter et retourne son identifiant.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `contenu` | `str` | — | Markdown complet de l'édition |
| `nb_articles` | `int` | — | Nombre d'articles retenus |
| `statut` | `str` | `"brouillon"` | Statut initial |

**Retour** — `int`, l'identifiant créé.

Laisser le statut par défaut : `brouillon` est le seul point d'entrée légal de la machine
à états.

```python
newsletter_id = database.sauvegarder_newsletter("## Édito\n…", nb_articles=6)
```

### `changer_statut_newsletter(newsletter_id, nouveau_statut, auteur)`

Applique une transition de statut et l'historise.

| Paramètre | Type | Description |
|---|---|---|
| `newsletter_id` | `int` | Newsletter concernée |
| `nouveau_statut` | `str` | Statut cible |
| `auteur` | `str` | Qui décide — tracé dans l'historique |

**Retour** — `None`.
**Lève** — `ValueError` si la newsletter est introuvable, ou si la transition n'est pas
dans `TRANSITIONS_AUTORISEES`. Rien n'est modifié dans ce cas.

La mise à jour du statut et l'écriture de l'historique sont dans la même transaction.

```python
database.changer_statut_newsletter(newsletter_id, "en_revue", "Alice")
database.changer_statut_newsletter(newsletter_id, "validé", "Alice")
# database.changer_statut_newsletter(newsletter_id, "brouillon", "Alice")  → ValueError
```

### `modifier_contenu_newsletter(newsletter_id, nouveau_contenu)`

Remplace le contenu d'une newsletter.

**Retour** — `None`. `statut` et `nb_articles` sont préservés.

```python
database.modifier_contenu_newsletter(newsletter_id, "## Édito\nVersion corrigée…")
```

### `derniere_newsletter_brouillon()`

Retourne la newsletter en `brouillon` la plus récente.

**Retour** — tuple `(id, contenu, nb_articles, statut, date_generation)`, ou `None`.

```python
brouillon = database.derniere_newsletter_brouillon()
if brouillon:
    print(f"Newsletter #{brouillon[0]} à valider ({brouillon[2]} articles)")
```

### `derniere_newsletter_validee()`

Retourne la newsletter en `validé` la plus récente.

**Retour** — tuple `(id, contenu, nb_articles, statut, date_generation)`, ou `None`.
C'est la newsletter que `monday_publish.yml` enverra.

### `newsletter_par_id(newsletter_id)`

Retourne une newsletter par son identifiant, quel que soit son statut.

**Retour** — tuple `(id, contenu, nb_articles, statut, date_generation)`, ou `None`.

```python
statut = database.newsletter_par_id(newsletter_id)[3]
```

### `lister_editions_publiees()`

Retourne toutes les newsletters `publié`, de la plus récente à la plus ancienne.

**Retour** — liste de tuples `(id, contenu, nb_articles, statut, date_generation)`.
Source de l'index de recherche de l'archive.

### `enregistrer_publication_canal(newsletter_id, canal, statut, tentatives, erreur=None)`

Enregistre ou met à jour le résultat d'un envoi sur un canal.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `newsletter_id` | `int` | — | Newsletter concernée |
| `canal` | `str` | — | `"telegram"`, `"email"`… |
| `statut` | `str` | — | Doit appartenir à `STATUTS_PUBLICATION_CANAL` |
| `tentatives` | `int` | — | Compteur cumulatif d'essais |
| `erreur` | `str \| None` | `None` | Message d'erreur si échec |

**Retour** — `None`.
**Lève** — `ValueError` si `statut` est inconnu.

Upsert sur `(newsletter_id, canal)` : republier met à jour la ligne au lieu d'en créer une
seconde.

```python
database.enregistrer_publication_canal(newsletter_id, "telegram", "echec", 1, "Timeout")
database.enregistrer_publication_canal(newsletter_id, "telegram", "publié", 2)
```

### `statuts_publication(newsletter_id)`

Retourne l'état de publication par canal, trié par canal.

**Retour** — liste de tuples `(canal, statut, tentatives, erreur, horodatage)`.

```python
for canal, statut, tentatives, erreur, _ in database.statuts_publication(newsletter_id):
    print(f"{canal}: {statut} ({tentatives} tentative(s)) {erreur or ''}")
```

### `tous_canaux_publies(newsletter_id, canaux=CANAUX_PUBLICATION)`

Indique si tous les canaux attendus ont le statut `publié`.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `newsletter_id` | `int` | — | Newsletter concernée |
| `canaux` | `tuple[str]` | `CANAUX_PUBLICATION` | Canaux à exiger |

**Retour** — `bool`. C'est la condition vérifiée avant de faire passer une newsletter en
`publié`.

```python
if database.tous_canaux_publies(newsletter_id):
    database.changer_statut_newsletter(newsletter_id, "publié", "orchestrateur")
```

### `ajouter_abonne_email(email)`

Inscrit une adresse email, sans erreur ni doublon.

**Retour** — `None`.

### `lister_abonnes_actifs()`

Retourne les emails au statut `actif`, par ordre d'inscription.

**Retour** — `list[str]`.

### `desabonner_email(email)`

Passe un abonné au statut `inactif` sans supprimer sa ligne.

**Retour** — `None`. Conserver la ligne évite qu'un import ultérieur ne le réinscrive.

### `historique_newsletter(newsletter_id)`

Retourne les transitions de statut, par ordre chronologique.

**Retour** — liste de tuples `(ancien_statut, nouveau_statut, auteur, horodatage)`. Seules
les transitions réellement appliquées y figurent.

```python
for ancien, nouveau, auteur, quand in database.historique_newsletter(newsletter_id):
    print(f"{quand} — {auteur} : {ancien} → {nouveau}")
```

### `articles_a_resumer(seuil=SEUIL_PERTINENCE, limit=None)`

Retourne les articles pertinents sans résumé.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `seuil` | `int` | `40` | Score strictement dépassé (`>`) |
| `limit` | `int \| None` | `None` | Borne le nombre d'articles, donc la consommation Gemini |

**Retour** — liste de tuples `(url, titre, contenu)`.

```python
for url, titre, contenu in database.articles_a_resumer(limit=10):
    ...
```

### `articles_selectionnables(seuil=SEUIL_PERTINENCE, limit=None)`

Retourne les articles candidats à la newsletter.

**Retour** — liste de tuples
`(url, titre, contenu, source_id, date_pub, score_pertinence, resume)`, filtrée sur score,
`resume IS NOT NULL` et `selectionne = 0` : un article déjà publié ne peut pas ressortir.

### `marquer_selectionne(url, score_editorial)`

Marque un article comme retenu et fige son score éditorial.

| Paramètre | Type | Description |
|---|---|---|
| `url` | `str` | Article retenu |
| `score_editorial` | `float` | Score calculé par `score_editorial()` |

**Retour** — `None`. À n'appeler qu'après une rédaction réussie.

### `article_existe(url)`

Indique si un article est déjà en base.

**Retour** — `bool`.

---

## pipeline/filter.py

Scoring purement lexical : aucun appel réseau, aucun LLM.

### `detecter_pays(titre, contenu)`

Retourne le premier pays africain détecté dans le texte.

**Retour** — `str | None`, le terme trouvé en minuscules.

```python
from pipeline.filter import detecter_pays
detecter_pays("Une startup de Lagos", "")        # → 'lagos' n'est pas un pays : None
detecter_pays("Fintech au Nigeria", "")          # → 'nigeria'
```

### `score_article(titre, contenu, source_id)`

Retourne le score de pertinence africaine, de 0 à 100.

| Paramètre | Type | Description |
|---|---|---|
| `titre` | `str` | Titre de l'article |
| `contenu` | `str` | Corps ou extrait |
| `source_id` | `str` | Identifiant de la source |

**Retour** — `int`. Bonus cumulés une seule fois chacun : pays (20), ville (15),
organisation panafricaine (15), terme tech africain (10), source africaine (10), plafonné
à 100.

```python
from pipeline.filter import score_article
score_article("AI hub opens in Nairobi", "Kenyan startups…", "techpoint-africa")  # → 55
```

---

## pipeline/dedup.py

### `hash_article(titre, url)`

Retourne l'empreinte MD5 du titre normalisé.

**Retour** — `str`. `url` est accepté pour l'homogénéité des appels mais **n'entre pas**
dans l'empreinte : deux urls différentes pour un même titre sont un doublon.

### `est_doublon_exact(article, hashes_vus)`

Indique si le titre de l'article a déjà été vu.

| Paramètre | Type | Description |
|---|---|---|
| `article` | `dict` | Doit porter `title` et `url` |
| `hashes_vus` | `set[str]` | Empreintes déjà rencontrées |

**Retour** — `bool`.

### `est_quasi_doublon(article, articles_vus, seuil=SEUIL_QUASI_DOUBLON)`

Indique si l'article traite du même sujet qu'un article déjà retenu.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `article` | `dict` | — | Article candidat |
| `articles_vus` | `list[dict]` | — | Articles déjà conservés |
| `seuil` | `float` | `0.85` | Similarité cosinus à partir de laquelle c'est un doublon |

**Retour** — `bool`. Charge le modèle `sentence-transformers` au premier appel (plusieurs
centaines de Mo, mis en cache ensuite).

### `deduplicate(articles)`

Retourne les articles débarrassés de leurs doublons, dans l'ordre d'entrée.

**Retour** — `list[dict]`. Deux passes : empreinte de titre, puis similarité sémantique.

> La déduplication est **locale à la liste fournie**. `orchestrator.run()` l'applique source
> par source : deux sources relayant la même dépêche passent toutes les deux.

```python
from pipeline.dedup import deduplicate
retenus = deduplicate([{"title": "A", "url": "u1", "content": "…"}, …])
```

---

## pipeline/summarize.py

### `get_client()`

Retourne le client HTTP Gemini, créé au premier appel puis réutilisé.

**Retour** — `httpx.Client`.
**Lève** — `RuntimeError` si `GEMINI_API_KEY` est absente.

Mis en cache dans un global, contrairement aux clients de publication.

### `summarize_article(titre, contenu)`

Retourne le résumé en 3 lignes d'un article.

| Paramètre | Type | Description |
|---|---|---|
| `titre` | `str` | Titre de l'article |
| `contenu` | `str` | Corps à résumer (moins de 50 caractères → ignoré) |

**Retour** — `str | None`. `None` si l'article est trop court, si Gemini renvoie une
réponse inexploitable, ou après 3 tentatives infructueuses. Ne lève jamais.

```python
from pipeline.summarize import summarize_article
resume = summarize_article("Fintech au Kenya", "La startup annonce…")
if resume:
    database.sauvegarder_resume(url, resume)
```

---

## pipeline/editor.py

### `score_editorial(score_pertinence, date_pub, maintenant=None)`

Retourne le score éditorial d'un article : pertinence + bonus de fraîcheur.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `score_pertinence` | `int` | — | Score africain 0–100 |
| `date_pub` | `str` | — | Date ISO ; absente ou illisible → bonus nul |
| `maintenant` | `datetime \| None` | `None` | Injectable pour les tests |

**Retour** — `float` arrondi à 2 décimales. Le bonus vaut 20 points au maximum, décroissant
linéairement sur 7 jours.

```python
from pipeline.editor import score_editorial
score_editorial(60, "2026-09-06T10:00:00", maintenant=datetime(2026, 9, 6, 10))  # → 80.0
```

### `selectionner_articles_semaine(seuil=None, maintenant=None)`

Sélectionne 5 à 7 articles pour l'édition de la semaine.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `seuil` | `int \| None` | `SEUIL_PERTINENCE` | Score minimum |
| `maintenant` | `datetime \| None` | `None` | Injectable pour les tests |

**Retour** — liste de dicts `{url, titre, resume, source_id, pays, score_editorial}`, triés
par score décroissant. Quota de 2 articles par pays, relâché si le minimum de 5 n'est pas
atteignable autrement.

**Fonction pure** : n'écrit rien en base. Le marquage revient à l'appelant via
`marquer_selectionne()`.

---

## pipeline/run_summarize.py

### `run(limit=None)`

Résume en batch tous les articles pertinents sans résumé.

**Retour** — `None`. Affiche le décompte des succès et des échecs.

### `main()`

Point d'entrée CLI : `python -m pipeline.run_summarize [--limit N]`.

---

## pipeline/run_editor.py

### `run(seuil=None)`

Sélectionne les articles de la semaine et les marque en base, sans rédiger.

**Retour** — `None`.

### `main()`

Point d'entrée CLI : `python -m pipeline.run_editor [--seuil N]`.

---

## publisher/publish.py

### `publish_newsletter(auteur="orchestrateur")`

Publie la dernière newsletter validée sur tous les canaux actifs.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `auteur` | `str` | `"orchestrateur"` | Tracé dans l'historique de statut |

**Retour** — `dict[str, bool]` — `{canal: succès}`, ou `{}` si aucune newsletter validée.

**Ne lève jamais.** Chaque canal est isolé : une panne réseau sur l'un n'empêche pas de
tenter les autres, et ne fait pas planter l'interface Streamlit qui appelle cette fonction
depuis un bouton. Le statut ne passe à `publié` que si tous les canaux ont réussi.

> ⚠️ Envoie un message **réel** aux abonnés.

```python
from publisher.publish import publish_newsletter
resultats = publish_newsletter(auteur="Alice")   # → {'telegram': True}
```

### `republier_canal(newsletter_id, canal, auteur="orchestrateur")`

Réémet une newsletter sur un seul canal.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `newsletter_id` | `int` | — | Newsletter concernée |
| `canal` | `str` | — | Doit être dans `CANAUX_PUBLICATION` |
| `auteur` | `str` | `"orchestrateur"` | Tracé dans l'historique |

**Retour** — `bool`.
**Lève** — `ValueError` si le canal est inconnu ou désactivé, si la newsletter est
introuvable, ou si son statut n'est pas `validé`.

Le canal déjà publié n'est pas renvoyé et son compteur de tentatives n'est pas incrémenté.

---

## publisher/telegram_client.py

### `get_client()`

Retourne un client HTTP Telegram **neuf à chaque appel**.

**Retour** — `httpx.Client`.
**Lève** — `RuntimeError` si `TELEGRAM_BOT_TOKEN` est absent.

Volontairement non mis en cache : `review_ui.py` tourne en continu et un token modifié dans
`.env` resterait sinon périmé jusqu'au redémarrage.

### `envoyer_telegram(contenu)`

Publie une newsletter markdown sur le canal Telegram.

| Paramètre | Type | Description |
|---|---|---|
| `contenu` | `str` | Markdown de la newsletter |

**Retour** — `bool`.
**Lève** — `RuntimeError` si `TELEGRAM_CHANNEL_ID` est absent.

Le markdown est converti en HTML Telegram plutôt que passé en mode Markdown natif, qui
échoue dès qu'un underscore n'est pas fermé. Les messages de plus de 4096 caractères sont
découpés à un point qui préserve l'équilibre des balises.

---

## publisher/email_client.py

Canal développé et testé, **désactivé en production** (absent de `CANAUX_PUBLICATION`).

### `get_client()`

Retourne un client HTTP Resend neuf à chaque appel.

**Lève** — `RuntimeError` si `RESEND_API_KEY` est absente.

### `envoyer_email(contenu)`

Envoie la newsletter aux abonnés actifs.

**Retour** — `bool`.
**Lève** — `RuntimeError` si `RESEND_FROM_EMAIL` est absent ou si aucun abonné n'est actif.

Les destinataires sont en copie cachée ; `to` pointe sur l'expéditeur, exigence de l'API
Resend.

---

## publisher/run_publish.py

### `run(auteur="github-actions")`

Publie la newsletter validée et retourne un code de sortie.

**Retour** — `int` : `0` si la publication a réussi ou s'il n'y avait rien à publier, `1` si
un canal a échoué (le run GitHub Actions vire alors au rouge, et une alerte Telegram part
vers le groupe de l'équipe).

C'est la raison d'être du module : `publish_newsletter()` ne lève jamais, un échec passerait
donc « vert » dans le workflow.

```bash
python -m publisher.run_publish   # echo $? → 0 ou 1
```

---

## archive/search.py

### Constantes

| Nom | Valeur | Rôle |
|---|---|---|
| `INDEX_DIR` | `"archive/index_whoosh"` | Dossier de l'index Whoosh (gitignoré, régénérable) |
| `LONGUEUR_EXTRAIT` | `300` | Longueur de l'aperçu quand la requête est vide |

### `indexer_editions()`

(Ré)indexe toutes les newsletters publiées.

**Retour** — `int`, le nombre d'éditions indexées.

Idempotent : `id` est un champ unique et `update_document()` remplace le document existant
au lieu d'en ajouter un second. Les éditions qui ne sont plus `publié` sont retirées de
l'index — une édition dépubliée disparaît de l'archive publique.

Appelée automatiquement après chaque publication réussie ; l'appel manuel sert à rattraper
une base modifiée à la main.

```python
from archive.search import indexer_editions
indexer_editions()   # → 12
```

### `rechercher(query="", limit=None)`

Retourne les éditions publiées correspondant à la requête.

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `query` | `str` | `""` | Mots-clés. Vide ou blanc → toutes les éditions |
| `limit` | `int \| None` | `None` | Nombre maximum de résultats |

**Retour** — liste de dicts
`{id, titre, contenu, date_generation, nb_articles, extrait, score}`.

- requête vide → toutes les éditions publiées, de la plus récente à la plus ancienne ;
- requête renseignée → résultats par pertinence, `extrait` portant le mot-clé en `**gras**`
  markdown ;
- l'index est construit à la volée s'il est absent (il est gitignoré, un clone frais n'en a
  pas) ;
- la recherche ignore les accents : `energie` retrouve `énergie`.

```python
from archive.search import rechercher
for edition in rechercher("fintech"):
    print(edition["titre"], "—", edition["extrait"][:80])
```

### `format_token(text, token, replace=False)`

Rend un mot trouvé en `**gras**` markdown. Surcharge du formateur Whoosh, utilisée en
interne par `rechercher()` — le formateur HTML par défaut obligerait l'archive à rendre du
HTML brut issu du contenu des newsletters.

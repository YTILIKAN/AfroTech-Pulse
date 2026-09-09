# Référence des fonctions internes

Ce document décrit les fonctions publiques des modules clés du pipeline :
`database.py`, `pipeline/`, `newsletter/`, `publisher/`, `scraper/`.

Il complète le [README](../README.md) (vue d'ensemble, structure du projet,
architecture du pipeline, commandes).

Chaque module porte aussi une docstring de tête et chaque fonction publique une
docstring — ce fichier en est la synthèse navigable.

---

## Table des matières

- [Conventions](#conventions)
- [`database.py`](#databasepy)
- [`scraper/main.py`](#scrapermainpy)
- [`pipeline/filter.py`](#pipelinefilterpy)
- [`pipeline/dedup.py`](#pipelinededuppy)
- [`pipeline/summarize.py`](#pipelinesummarizepy)
- [`pipeline/editor.py`](#pipelineeditorpy)
- [`newsletter/writer.py`](#newsletterwriterpy)
- [`publisher/publish.py`](#publisherpublishpy)
- [`publisher/telegram_client.py`](#publishertelegram_clientpy)
- [`publisher/email_client.py`](#publisheremail_clientpy)
- [`notifier.py`](#notifierpy)
- [Points d'entrée `run_*`](#points-dentrée-run_)

---

## Conventions

- **Persistance** : tout passe par `database.py`. Aucun autre module n'ouvre de
  connexion `sqlite3`.
- **Résilience réseau** : les clients LLM et Telegram/email retentent 3 fois avec
  un backoff exponentiel (2s / 4s / 8s) sur les erreurs `429` et `5xx` et les
  timeouts, puis abandonnent proprement (`None` ou `False`, jamais d'exception
  propagée jusqu'au cron). Voir la section « Stabilité et limites connues » du
  README.
- **Secrets** : lus via `os.getenv(...)`. Une variable manquante lève
  `RuntimeError` avec un message explicite.
- **Tuples** : les lectures `database.py` renvoient des tuples SQLite bruts —
  l'ordre des colonnes est documenté ci-dessous pour chaque fonction.

---

## `database.py`

Point d'entrée unique de la persistance (SQLite, fichier `DB_PATH`).

### Constantes

| Nom | Rôle |
|---|---|
| `DB_PATH` | Chemin du fichier SQLite (`"afrotech.db"`). Redirigé en test. |
| `SEUIL_PERTINENCE` | Score minimal (0-100) pour qu'un article soit résumé puis éligible. `40`. |
| `TRANSITIONS_AUTORISEES` | Machine à états du statut d'une newsletter. Toute transition absente est refusée. `rejeté` et `publié` sont terminaux. |
| `CANAUX_PUBLICATION` | Canaux actifs — `("telegram",)`. `email` sera réactivé après vérification du domaine. |
| `STATUTS_PUBLICATION_CANAL` | `{"en_attente", "publié", "echec"}`. |

Machine à états :

```
brouillon ──▶ en_revue ──▶ validé ──▶ publié
                   └──────▶ rejeté
```

### Schéma

| Table | Contenu |
|---|---|
| `articles_raw` | Article collecté : `titre`, `url` (unique), `source_id`, `date_pub`, `contenu`, `date_collecte`, `score_pertinence`, `resume`, `score_editorial`, `selectionne`. |
| `newsletters` | `contenu`, `nb_articles`, `statut`, `date_generation`. |
| `newsletters_historique` | Une ligne par transition de statut : `newsletter_id`, `ancien_statut`, `nouveau_statut`, `auteur`, `horodatage`. |
| `newsletters_publications` | Résultat par canal, upsert sur `(newsletter_id, canal)` : `statut`, `tentatives`, `erreur`, `horodatage`. |
| `abonnes_email` | `email` (unique), `statut` (`actif`/`inactif`), `date_inscription`. |

### Fonctions

| Fonction | Description |
|---|---|
| `creer_base()` | Crée les tables et applique les migrations de colonnes. Idempotent, appelé au démarrage de chaque point d'entrée. |
| `sauvegarder_article(titre, url, source_id, date_pub, contenu, score_pertinence)` | Insère un article. `INSERT OR IGNORE` sur `url` : un doublon est sans effet. |
| `sauvegarder_resume(url, resume)` | Attache le résumé LLM à l'article. |
| `sauvegarder_newsletter(contenu, nb_articles, statut="brouillon")` | Insère une newsletter, **retourne son `id`**. |
| `changer_statut_newsletter(newsletter_id, nouveau_statut, auteur)` | Applique une transition et l'historise (atomique). `ValueError` si newsletter absente ou transition interdite. |
| `modifier_contenu_newsletter(newsletter_id, nouveau_contenu)` | Remplace le corps. Ne touche pas au statut. |
| `derniere_newsletter_brouillon()` | Dernière newsletter `brouillon` → `(id, contenu, nb_articles, statut, date_generation)` ou `None`. |
| `derniere_newsletter_validee()` | Idem pour `validé`. Lue par la publication du lundi. |
| `newsletter_par_id(newsletter_id)` | Newsletter par id, tout statut → tuple à 5 champs ou `None`. |
| `lister_editions_publiees()` | Toutes les newsletters `publié`, plus récente d'abord. Sert à l'archive. |
| `enregistrer_publication_canal(newsletter_id, canal, statut, tentatives, erreur=None)` | Upsert du résultat d'un envoi. Rejouer un canal met à jour sa ligne. `ValueError` si `statut` inconnu. |
| `statuts_publication(newsletter_id)` | `[(canal, statut, tentatives, erreur, horodatage), ...]` trié par canal. |
| `tous_canaux_publies(newsletter_id, canaux=CANAUX_PUBLICATION)` | `True` si chaque canal a le statut `publié`. Garde-fou avant `validé → publié`. |
| `ajouter_abonne_email(email)` | Ajoute un abonné `actif`. `INSERT OR IGNORE`. |
| `lister_abonnes_actifs()` | `list[str]` des emails `actif`, par ordre d'inscription. |
| `desabonner_email(email)` | Passe l'abonné à `inactif` (pas de suppression). |
| `historique_newsletter(newsletter_id)` | `[(ancien, nouveau, auteur, horodatage), ...]` dans l'ordre chronologique. |
| `articles_a_resumer(seuil=SEUIL_PERTINENCE, limit=None)` | Articles au-dessus de `seuil` sans résumé → `[(url, titre, contenu), ...]`. |
| `articles_selectionnables(seuil=SEUIL_PERTINENCE, limit=None)` | Candidats newsletter (au-dessus du seuil, résumés, pas encore sélectionnés) → `[(url, titre, contenu, source_id, date_pub, score_pertinence, resume), ...]`. |
| `marquer_selectionne(url, score_editorial)` | Marque l'article comme retenu + enregistre son score éditorial. Il sort de `articles_selectionnables()`. |
| `article_existe(url)` | `bool`. Utilisé par l'orchestrateur pour éviter les doublons. |

---

## `scraper/main.py`

Collecte des articles depuis les sources RSS.

| Fonction | Description |
|---|---|
| `load_sources()` | Lit `data/sources.json`, retourne la liste des sources `type == "rss"` actives avec une URL. |
| `scrape_rss(source)` | Visite l'URL de `source`, parse le flux, retourne `list[dict]` `{title, url, content, published, source_id}`. Gère timeout / erreur réseau / flux invalide → `[]` (jamais d'exception). |
| `main()` | Point d'entrée CLI : parcourt toutes les sources et affiche un récapitulatif. |

`source` est un dict de `sources.json` : `{name, url, type, category, active, ...}`.

---

## `pipeline/filter.py`

Filtre de pertinence africaine — recherche de mots-clés, déterministe, sans réseau.

| Fonction | Description |
|---|---|
| `detecter_pays(titre, contenu)` | Premier pays africain trouvé dans le texte, ou `None`. |
| `score_article(titre, contenu, source_id)` | Score `0-100` : pays `+20`, ville `+15`, organisation `+15`, terme tech africain `+10`, source africaine `+10` (chaque catégorie une seule fois), plafonné à 100. |

---

## `pipeline/dedup.py`

Déduplication d'un lot d'articles. **Intra-lot uniquement** (pas de comparaison à
la base).

| Fonction | Description |
|---|---|
| `hash_article(titre, url)` | Hash MD5 du titre normalisé (minuscules, sans ponctuation). `url` ignorée. |
| `est_doublon_exact(article, hashes_vus)` | `True` si le hash du titre est déjà dans `hashes_vus`. |
| `est_quasi_doublon(article, articles_vus, seuil=SEUIL_QUASI_DOUBLON)` | `True` si la similarité cosinus d'embedding avec un article déjà vu ≥ `seuil` (`0.85`). |
| `deduplicate(articles)` | Retourne `articles` sans doublons exacts ni quasi-doublons, premier exemplaire conservé. Dicts attendus : `title`, `url`, `content`. |

Le modèle `sentence-transformers` est chargé au premier appel de `est_quasi_doublon` / `deduplicate`.

---

## `pipeline/summarize.py`

Résumé LLM (Gemini) : 3 lignes, angle africain obligatoire, français.

| Fonction | Description |
|---|---|
| `get_client()` | Client `httpx` Gemini (mis en cache). `RuntimeError` si `GEMINI_API_KEY` absente. |
| `summarize_article(titre, contenu)` | Résumé en 3 lignes, ou `None` (contenu trop court, réponse vide, ou échec après 3 tentatives). |

---

## `pipeline/editor.py`

Sélection éditoriale hebdomadaire des 5 à 7 meilleurs articles. **Fonction pure** :
aucune écriture en base (le marquage est fait par `run_editor.py`).

| Fonction | Description |
|---|---|
| `score_editorial(score_pertinence, date_pub, maintenant=None)` | Score éditorial = pertinence (S3) + bonus de fraîcheur (jusqu'à `+20`, décroissant sur 7 jours). |
| `selectionner_articles_semaine(seuil=None, maintenant=None)` | Trie les candidats par score éditorial, applique une diversité géographique (`MAX_ARTICLES_PAR_PAYS = 2`), complète jusqu'à `SELECTION_MIN` si la diversité bloque. Retourne `list[dict]` `{url, titre, resume, source_id, pays, score_editorial}`. |

---

## `newsletter/writer.py`

Rédaction de la newsletter complète (charte Y'TILIKAN).

| Fonction | Description |
|---|---|
| `get_client()` | Client `httpx` Gemini (mis en cache). `RuntimeError` si `GEMINI_API_KEY` absente. |
| `compter_articles(newsletter)` | Nombre de blocs `### ` dans le Markdown. |
| `structure_respectee(newsletter, nb_articles_attendu)` | `True` si les 3 sections (`## Édito`, `## Cette semaine`, `## Conclusion`) sont présentes et le nombre de blocs article correct. |
| `generer_newsletter(articles)` | Markdown de la newsletter, ou `None`. Un écart de structure est signalé, pas bloquant. Chaque `article` : `titre`/`title`, `url`, `resume`/`contenu`. |

---

## `publisher/publish.py`

Orchestration multicanal. Aucune fonction ne lève — erreurs capturées et loguées.

| Fonction | Description |
|---|---|
| `publish_newsletter(auteur="orchestrateur")` | Publie la dernière newsletter `validé` sur tous les canaux actifs. Retourne `{canal: bool}`, ou `{}` s'il n'y a rien à publier. Ne passe la newsletter à `publié` (et ne réindexe l'archive) que si **tous** les canaux réussissent. |
| `republier_canal(newsletter_id, canal, auteur="orchestrateur")` | Rejoue **un** canal pour une newsletter encore `validé`. `ValueError` si canal inconnu, newsletter absente, ou statut ≠ `validé`. |

---

## `publisher/telegram_client.py`

Canal actif. Publie sur le canal public `TELEGRAM_CHANNEL_ID`.

| Fonction | Description |
|---|---|
| `envoyer_telegram(contenu)` | Convertit le Markdown en HTML Telegram, découpe sous 4096 caractères sans casser de balise, envoie chaque morceau (3 tentatives + backoff). Un **seul** client HTTP par appel, fermé explicitement. `True` si tout est passé. `RuntimeError` si `TELEGRAM_CHANNEL_ID` absent. |
| `get_client()` | Client `httpx` Telegram, **non mis en cache** (un token changé dans `.env` est repris sans redémarrage). `RuntimeError` si `TELEGRAM_BOT_TOKEN` absent. |

---

## `publisher/email_client.py`

Canal **désactivé** (`email` absent de `CANAUX_PUBLICATION` tant que le domaine
Resend n'est pas vérifié). Code fonctionnel et testé.

| Fonction | Description |
|---|---|
| `envoyer_email(contenu)` | Envoie à tous les abonnés actifs en `bcc`. `True` si l'API accepte. `RuntimeError` si `RESEND_FROM_EMAIL` absent ou aucun abonné actif. |
| `get_client()` | Client `httpx` Resend, non mis en cache. `RuntimeError` si `RESEND_API_KEY` absente. |

---

## `notifier.py`

Notifications internes vers le **groupe privé** de l'équipe (`TELEGRAM_ADMIN_CHAT_ID`).
Distinct de `publisher/telegram_client.py` (canal public). Rien de ce qui passe
ici n'est visible des abonnés : rappels de validation, alertes d'échec de
publication.

---

## Points d'entrée `run_*`

Modules exécutables (`python -m ...`) qui enchaînent la logique métier et gèrent
le code de sortie. Utilisés tels quels par les workflows GitHub Actions.

| Commande | Rôle | Code de sortie |
|---|---|---|
| `python orchestrator.py` | Collecte + filtrage + dédup + stockage | — |
| `python -m pipeline.run_summarize [--limit N]` | Résume les articles pertinents non résumés | — |
| `python -m pipeline.run_editor [--seuil S]` | Marque en base la sélection éditoriale (sans rédiger) | — |
| `python -m newsletter.run_writer [--seuil S]` | Sélection + rédaction → newsletter `brouillon` | — |
| `python -m notifier` | Rappel Telegram à l'équipe s'il reste un brouillon | `1` si un brouillon attend mais l'envoi échoue |
| `python -m publisher.run_publish` | Publie la newsletter `validé` | `1` si un canal échoue (run GitHub Actions rouge + alerte) |

Interfaces Streamlit (pas des `run_*`) : `validation/review_ui.py`,
`dashboard/app.py`, `archive/app.py`.

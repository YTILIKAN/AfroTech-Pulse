# Architecture — AfroTech Pulse

Comment le projet est organisé, comment les modules s'articulent, et où intervenir pour
modifier un comportement donné.

Documents liés : [api.md](api.md) pour la référence des fonctions publiques,
[format_newsletter.md](format_newsletter.md) pour le gabarit de sortie du rédacteur,
[audit_securite.md](audit_securite.md) pour l'état avant publication open source.

---

## Sommaire

- [Principe général](#principe-général)
- [Le pipeline en 10 étapes](#le-pipeline-en-10-étapes)
- [Dépendances entre fichiers](#dépendances-entre-fichiers)
- [Comment les modules s'articulent](#comment-les-modules-sarticulent)
- [Machine à états des newsletters](#machine-à-états-des-newsletters)
- [Workflows GitHub Actions](#workflows-github-actions)
- [Schéma de la base](#schéma-de-la-base)
- [Points d'entrée](#points-dentrée)

---

## Principe général

Trois règles structurent tout le code.

**SQLite est le seul état partagé.** Aucun module ne parle à un autre en mémoire : chacun
lit et écrit dans `afrotech.db`, et les étapes s'enchaînent par l'état de la base. C'est ce
qui permet à des workflows GitHub Actions séparés dans le temps de former une chaîne
cohérente, et de rejouer une étape isolément sans rejouer les précédentes.

**Chaque étage isole ses erreurs.** Une source RSS en panne, un résumé LLM refusé, un canal
de publication injoignable : rien de tout cela n'interrompt le reste. Les erreurs sont
journalisées avec un préfixe explicite (`[TIMEOUT]`, `[ERREUR RÉSEAU]`, `[ÉCHEC]`), jamais
avalées silencieusement.

**Une seule décision est humaine.** La validation du lundi. Tout le reste est automatique,
y compris la publication.

---

## Le pipeline en 10 étapes

| # | Étape | Module | Déclencheur |
|---|---|---|---|
| 1 | Collecte | `scraper/main.py` | `daily_scrape.yml`, 6h UTC |
| 2 | Filtrage de pertinence | `pipeline/filter.py` | idem, dans le même run |
| 3 | Déduplication | `pipeline/dedup.py` | idem |
| 4 | Résumé LLM | `pipeline/summarize.py` | idem, après `orchestrator.py` |
| 5 | Sélection éditoriale | `pipeline/editor.py` | `weekly_editor.yml`, dimanche 20h UTC |
| 6 | Rédaction | `newsletter/writer.py` | idem, dans le même run |
| 7 | Validation humaine | `validation/review_ui.py` | manuel, lundi (~15 min) |
| 8 | Publication | `publisher/publish.py` | `monday_publish.yml`, lundi 13h UTC |
| 9 | Dashboard | `dashboard/app.py` | à la demande, lecture seule |
| 10 | Archive | `archive/search.py` | après chaque publication réussie |

### Étapes 1 à 3 — collecte, filtrage, déduplication

`orchestrator.run()` enchaîne les trois dans un seul passage, source par source :

```
pour chaque source RSS active :
    scrape_rss(source)          → liste d'articles bruts
    deduplicate(articles)       → doublons exacts puis quasi-doublons retirés
    score_article(...)          → score de pertinence africaine, 0 à 100
    sauvegarder_article(...)    → insertion si l'url n'est pas déjà connue
```

Le scoring est purement lexical : pays, villes, organisations panafricaines, termes tech,
origine de la source. Aucun appel réseau, aucun LLM — donc gratuit et rejouable.

> **Limite connue** : `deduplicate()` est appelé *à l'intérieur* de la boucle sur les
> sources, donc lot par lot. Deux sources différentes relayant la même dépêche passent
> toutes les deux, et rien n'est comparé contre les articles déjà en base.

### Étape 4 — résumé LLM

`pipeline/run_summarize.py` prend les articles dont le score dépasse
`database.SEUIL_PERTINENCE` (40) et qui n'ont pas encore de résumé, puis appelle Gemini
pour chacun. Trois tentatives avec backoff exponentiel sur les 429 et 5xx ; les autres
codes HTTP sont abandonnés immédiatement, réessayer ne changerait rien.

### Étapes 5 et 6 — sélection et rédaction

`newsletter/run_writer.py` enchaîne les deux :

```
selectionner_articles_semaine()   → 5 à 7 articles, score éditorial + quota par pays
generer_newsletter(selection)     → markdown complet via Gemini
marquer_selectionne(...)          → seulement si la rédaction a réussi
sauvegarder_newsletter(...)       → statut 'brouillon'
```

L'ordre compte : les articles ne sont consommés qu'après une rédaction réussie, sinon un
échec de Gemini les brûlerait sans rien produire.

Le score éditorial vaut pertinence + bonus de fraîcheur (20 points au maximum, décroissant
linéairement sur 7 jours). Un quota de 2 articles par pays force la diversité géographique ;
si ce quota empêche d'atteindre le minimum de 5 articles, il est relâché — une édition
déséquilibrée vaut mieux qu'une édition trop courte.

### Étape 7 — validation humaine

`validation/review_ui.py` a deux visages selon l'état de la base : s'il existe un brouillon,
elle affiche l'éditeur (Édition, Aperçu, Historique) et les boutons Valider / Modifier /
Rejeter ; s'il n'y a pas de brouillon mais une newsletter validée, elle bascule sur un
panneau de publication protégé par une checklist.

> **Étape manuelle indispensable** : après validation, il faut pousser `afrotech.db` vers
> le dépôt. La publication automatique lit la base depuis GitHub, pas depuis le poste du
> validateur.

### Étape 8 — publication

```
run_publish.run()               → traduit le résultat en code de sortie pour la CI
  publish_newsletter()          → boucle sur les canaux actifs
    _publier_canal()            → envoi + trace en base, erreurs isolées
    _finaliser_si_complet()     → 'publié' seulement si TOUS les canaux ont réussi
      indexer_editions()        → réindexation de l'archive (étape 10)
```

Chaque canal est tracé séparément dans `newsletters_publications`. Un succès partiel laisse
la newsletter en `validé` et permet une republication ciblée par `republier_canal()`, qui ne
renvoie pas sur le canal déjà réussi.

`run_publish` existe parce que `publish_newsletter()` ne lève jamais d'exception : sans
cette enveloppe, un échec Telegram passerait « vert » dans GitHub Actions.

### Étapes 9 et 10 — dashboard et archive

Les deux sont en lecture seule et n'écrivent jamais dans le pipeline. Le dashboard charge
une fenêtre de 12 semaines, l'enrichit (pays ISO-3, secteurs) et dérive tous les filtres en
mémoire. L'archive maintient un index Whoosh, réindexé automatiquement à chaque publication
réussie et reconstruit à la volée s'il est absent.

---

## Dépendances entre fichiers

Extrait des `import` réels du code. Les flèches se lisent « dépend de ».

```
                            ┌──────────────┐
                            │  database.py │  ← état partagé, ne dépend de rien
                            └──────▲───────┘
                                   │ (tous les modules ci-dessous en dépendent)

   COLLECTE ─────────────────────────────────────────────────────────────────────
   orchestrator.py ──┬──> scraper/main.py
                     ├──> pipeline/filter.py
                     └──> pipeline/dedup.py

   TRAITEMENT ───────────────────────────────────────────────────────────────────
   pipeline/run_summarize.py ──> pipeline/summarize.py
   pipeline/run_editor.py    ──> pipeline/editor.py ──> pipeline/filter.py

   RÉDACTION ────────────────────────────────────────────────────────────────────
   newsletter/run_writer.py ──┬──> newsletter/writer.py
                              └──> pipeline/editor.py

   VALIDATION ───────────────────────────────────────────────────────────────────
   validation/review_ui.py ──> publisher/publish.py

   PUBLICATION ──────────────────────────────────────────────────────────────────
   publisher/run_publish.py ──┬──> publisher/publish.py ──┬──> publisher/telegram_client.py
                              │                           ├──> publisher/email_client.py
                              └──> notifier.py            └──> archive/search.py

   ARCHIVE ──────────────────────────────────────────────────────────────────────
   archive/app.py ──> archive/search.py

   DASHBOARD ────────────────────────────────────────────────────────────────────
   dashboard/app.py ──┬──> dashboard/filters.py ──────> dashboard/data.py
                      ├──> dashboard/aggregations.py ──┘
                      ├──> dashboard/entities.py ──┬──> dashboard/enrichment.py
                      ├──> dashboard/text.py <─────┘
                      └──> dashboard/theme.py
```

Deux propriétés à préserver en modifiant le code :

- **`database.py` ne dépend d'aucun autre module du projet.** Toute logique métier qui y
  remonterait créerait un cycle.
- **`dashboard/data.py` est le seul module du dashboard qui touche SQLite.** Les autres sont
  des fonctions pures sur des listes de dicts, ce qui les rend testables sans base.

Un lien mérite d'être signalé : `publisher/publish.py` importe `archive/search.py` **à
l'intérieur** de la fonction, pas en tête de module. C'est délibéré — ça évite un cycle
`publish → search → database` et garde `publish.py` importable sans Whoosh installé.

---

## Comment les modules s'articulent

### Le contrat de données entre étapes

| Étape | Lit | Écrit |
|---|---|---|
| Collecte | `data/sources.json` | `articles_raw` (titre, url, contenu, score) |
| Résumé | `articles_raw` où `score > 40` et `resume IS NULL` | `articles_raw.resume` |
| Sélection | `articles_raw` résumés et non sélectionnés | `articles_raw.selectionne`, `score_editorial` |
| Rédaction | sélection en mémoire | `newsletters` (statut `brouillon`) |
| Validation | `newsletters` | `newsletters.statut`, `newsletters_historique` |
| Publication | `newsletters` où statut `validé` | `newsletters_publications`, `newsletters.statut` |
| Archive | `newsletters` où statut `publié` | `archive/index_whoosh/` (hors base) |
| Dashboard | `articles_raw` où `score >= 1` | rien |

### Les quatre clients HTTP

`get_client()` existe dans quatre modules, avec **deux stratégies opposées** — la différence
est intentionnelle :

| Module | Stratégie | Pourquoi |
|---|---|---|
| `pipeline/summarize.py` | mis en cache dans un global | script de batch, process court |
| `newsletter/writer.py` | mis en cache dans un global | idem |
| `publisher/telegram_client.py` | recréé à chaque appel | `review_ui.py` tourne en continu : un token changé dans `.env` doit être pris en compte sans redémarrage |
| `publisher/email_client.py` | recréé à chaque appel | idem |

---

## Machine à états des newsletters

Définie dans `database.TRANSITIONS_AUTORISEES`. Toute transition non prévue lève une
`ValueError` **sans rien modifier**, et chaque transition appliquée est historisée avec son
auteur dans `newsletters_historique`.

```
   sauvegarder_newsletter()
             │
             ▼
      ┌─────────────┐
      │  brouillon  │  généré par run_writer, en attente de relecture
      └──────┬──────┘
             │ un validateur ouvre la newsletter
             ▼
      ┌─────────────┐
      │  en_revue   │  prise en charge, décision en cours
      └──┬───────┬──┘
         │       │
    Valider   Rejeter
         │       │
         ▼       ▼
   ┌────────┐  ┌─────────┐
   │ validé │  │ rejeté  │  état terminal
   └───┬────┘  └─────────┘
       │ tous les canaux ont réussi
       ▼
   ┌─────────┐
   │ publié  │  état terminal, déclenche la réindexation de l'archive
   └─────────┘
```

Trois conséquences pratiques :

- **Pas de raccourci.** On ne peut pas passer de `brouillon` à `publié`. Un test qui prépare
  une newsletter publiée doit enchaîner tout le cycle. `review_ui._finaliser()` fait de même
  en appliquant deux transitions successives.
- **`rejeté` et `publié` sont terminaux.** Une newsletter rejetée ne peut plus être publiée,
  même par erreur de manipulation.
- **`validé` est le seul état publiable.** `republier_canal()` le vérifie explicitement.

---

## Workflows GitHub Actions

Quatre crons, tous en UTC, tous déclenchables à la main (`workflow_dispatch`).

| Workflow | Cron | Commande | Rôle |
|---|---|---|---|
| `daily_scrape.yml` | `0 6 * * *` | `orchestrator.py` puis `pipeline.run_summarize` | Étapes 1 à 4 |
| `weekly_editor.yml` | `0 20 * * 0` | `newsletter.run_writer` | Étapes 5 et 6 |
| `monday_reminder.yml` | `0 11 * * 1` | `notifier.py` | Rappel de validation à l'équipe |
| `monday_publish.yml` | `0 13 * * 1` | `publisher.run_publish` | Étape 8 |

**La persistance passe par Git.** `daily_scrape.yml` et `weekly_editor.yml` recommitent
`afrotech.db` via `git-auto-commit-action` : c'est ce qui permet à des runs successifs de
partager un état, GitHub Actions ne conservant rien entre deux exécutions. Conséquence
directe sur le lundi : la validation humaine se fait en local, mais `monday_publish.yml`
lit la base depuis le dépôt — sans `git push` de `afrotech.db` avant 13h UTC, rien ne part.

> Les implications de ce choix pour une publication open source sont documentées dans
> [audit_securite.md](audit_securite.md).

**Les échecs sont bruyants par construction.** `run_publish` et `notifier` retournent un code
de sortie non nul quand une action attendue échoue, ce qui fait virer le run au rouge et
déclenche une alerte Telegram vers le groupe privé de l'équipe.

---

## Schéma de la base

```
articles_raw                        newsletters
├── id                              ├── id
├── titre                           ├── contenu           (markdown)
├── url                UNIQUE       ├── nb_articles
├── source_id                       ├── statut            (machine à états)
├── date_pub                        └── date_generation
├── contenu                                 │
├── date_collecte                           │ 1..n
├── score_pertinence   (0 à 100)            ├─────────────────┐
├── resume             (LLM)                ▼                 ▼
├── score_editorial    (pertinence   newsletters_        newsletters_
│                       + fraîcheur)   historique         publications
└── selectionne        (0 / 1)       ├── newsletter_id   ├── newsletter_id
                                     ├── ancien_statut   ├── canal
abonnes_email                        ├── nouveau_statut  ├── statut
├── id                               ├── auteur          ├── tentatives
├── email              UNIQUE        └── horodatage      ├── erreur
├── statut  (actif / inactif)                            └── horodatage
└── date_inscription                                     UNIQUE (newsletter_id, canal)
```

`creer_base()` est idempotent et gère les migrations de colonnes : les colonnes ajoutées
après coup sont détectées via `PRAGMA table_info` puis créées si absentes. Faire évoluer le
schéma ne demande donc pas de script de migration séparé.

---

## Points d'entrée

```bash
python orchestrator.py                  # étapes 1 à 3
python -m pipeline.run_summarize        # étape 4
python -m pipeline.run_editor           # étape 5 seule
python -m newsletter.run_writer         # étapes 5 et 6
streamlit run validation/review_ui.py   # étape 7
python -m publisher.run_publish         # étape 8 (avec code de sortie)
python -m publisher.publish             # étape 8 (sans code de sortie)
python notifier.py                      # rappel de validation
streamlit run dashboard/app.py          # étape 9
streamlit run archive/app.py            # étape 10
python archive/search.py                # réindexation manuelle de l'archive
python database.py                      # création de la base + auto-tests
```

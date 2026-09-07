# AfroTech Pulse

AfroTech Pulse est un agent de veille automatisé dédié à l'intelligence artificielle en Afrique.

Chaque semaine, le système parcourt 50 sources RSS internationales, filtre ce qui compte réellement
pour le continent africain, et produit une newsletter en français publiée chaque lundi sur le canal
Telegram Y'TILIKAN — sans intervention manuelle, hormis une validation humaine de 15 minutes.

AfroTech Pulse est la voix numérique de la communauté Y'TILIKAN.
Conçu pour informer, construit pour durer, publié chaque semaine sans exception.

---

## Table des matières

- [Vision](#vision)
- [Livrables](#livrables)
- [Architecture du pipeline](#architecture-du-pipeline)
- [Cycle horaire complet](#cycle-horaire-complet)
- [Stabilité et limites connues](#stabilité-et-limites-connues)
- [Structure du projet](#structure-du-projet)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Lancer chaque composant](#lancer-chaque-composant)
- [Cycle de vie d'une newsletter](#cycle-de-vie-dune-newsletter)
- [Automatisations GitHub Actions](#automatisations-github-actions)
- [Variables d'environnement](#variables-denvironnement)
- [Tests](#tests)
- [Stabilité et limites connues](#stabilité-et-limites-connues)
- [Sources surveillées](#sources-surveillées)
- [Documentation technique](#documentation-technique)
- [Contribuer](#contribuer)
- [Licence](#licence)

---

## Vision

AfroTech Pulse n'est pas un simple agrégateur de flux RSS. C'est un agent IA doté d'une logique
de pertinence africaine : il surveille des dizaines de sources mondiales, sélectionne ce qui impacte
réellement le continent, contextualise avec un angle africain, rédige en français accessible et
publie automatiquement chaque lundi.

---

## Livrables

### 1. Newsletter automatisée
Publiée chaque lundi sur le Channel Telegram Y'TILIKAN. Entièrement générée par un agent LLM
(Google Gemini), avec une validation humaine de 15 minutes avant publication.

> **Canaux de publication** : Telegram est le canal actif en production. Email (via Resend) est
> développé et testé mais désactivé en attendant la mise en place d'une liste d'abonnés et la
> vérification du domaine d'envoi. LinkedIn et le site web sont des évolutions futures — le scope
> initial (WhatsApp Channel + LinkedIn) a été révisé suite à des blocages administratifs
> (vérification d'entreprise Meta/LinkedIn).

### 2. Archive publique consultable
Toutes les éditions publiées sont indexées dans un moteur de recherche full-text (Whoosh) et
consultables via une interface Streamlit dédiée.

### 3. Dashboard public interactif
Visualisation des tendances IA en Afrique en temps réel : carte géographique, graphiques par
secteur, timeline, top acteurs, nuage de mots.

Filtres combinables (période de 4, 8 ou 12 semaines, pays, secteur) appliqués
simultanément à toutes les visualisations, et vue comparative entre plusieurs pays.

---

## Architecture du pipeline

Le projet fonctionne comme une chaîne de production automatique en 10 étapes.
Le détail des modules et de leurs dépendances est dans [docs/architecture.md](docs/architecture.md).

```
CHAQUE JOUR (cron 0 6 * * *  —  daily_scrape.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 1 — Collecte
  └── Le scraper visite les 50 sources RSS actives
      et sauvegarde les articles bruts dans SQLite

  Étape 2 — Filtrage
  └── Chaque article reçoit un score de pertinence africaine (0 à 100)
      calculé sur pays, villes, organisations, termes tech et source
      Seuls les articles au-dessus de 40 sont résumés

  Étape 3 — Déduplication
  └── Doublons exacts (hash titre + URL) et quasi-doublons
      (similarité sémantique > 0.85) supprimés au sein du batch du jour

  Étape 4 — Résumé LLM
  └── Gemini résume chaque article pertinent en 3 lignes en français
      avec angle africain obligatoire

CHAQUE DIMANCHE SOIR (cron 0 20 * * 0  —  weekly_editor.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 5 — Sélection éditoriale
  └── Sélection des 5 à 7 meilleurs articles de la semaine
      Score éditorial = pertinence + bonus fraîcheur (max 20 points sur 7 jours)
      Quota de 2 articles maximum par pays, pour la diversité géographique

  Étape 6 — Rédaction newsletter
  └── Gemini rédige la newsletter complète (édito + articles + conclusion)
      et la sauvegarde en statut 'brouillon'

CHAQUE LUNDI MATIN (cron 0 11 * * 1  —  monday_reminder.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Rappel automatique
  └── Si une newsletter est en 'brouillon', un message Telegram
      prévient l'équipe qu'une validation est attendue

CHAQUE LUNDI (manuel, ~15 min — seul geste humain du cycle)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 7 — Validation humaine
  └── Un membre de l'équipe lit la newsletter (validation/review_ui.py),
      appuie sur Valider / Modifier / Rejeter, PUIS pousse afrotech.db
      vers le repo (git add afrotech.db && git commit && git push) —
      la publication automatique lit la base depuis GitHub, pas le poste

CHAQUE LUNDI (cron 0 13 * * 1  —  monday_publish.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 8 — Publication automatique
  └── Si une newsletter 'validé' existe (database.derniere_newsletter_validee()),
      publisher/run_publish.py l'envoie sur le canal Telegram Y'TILIKAN.
      Aucune newsletter validée -> rien ne part. Chaque canal est tracé
      séparément : un échec laisse la newsletter en 'validé', fait échouer
      le run GitHub Actions et alerte l'équipe sur Telegram (jamais
      silencieux), et permet de republier canal par canal.
      Email, LinkedIn et site web : en évolution

EN CONTINU
━━━━━━━━━━
  Étape 9 — Dashboard
  └── Mise à jour en temps réel des visualisations publiques

  Étape 10 — Archive
  └── Chaque publication réussie réindexe automatiquement l'archive
      full-text, consultable publiquement
```

### Cycle horaire complet

Tous les crons GitHub Actions sont en **UTC** et peuvent démarrer avec 5 à 20 min de retard
aux heures de pointe. Les heures locales ci-dessous sont celles de Montréal (heure de l'Est) :
elles glissent d'1 h en hiver, GitHub Actions ne gérant pas le changement d'heure.

| Workflow | Cron (UTC) | Heure Montréal (été / hiver) | Rôle |
|---|---|---|---|
| `daily_scrape.yml`    | `0 6 * * *`  | 02h / 01h, tous les jours | Collecte + filtrage + dédup + résumé LLM |
| `weekly_editor.yml`   | `0 20 * * 0` | dimanche 16h / 15h        | Sélection éditoriale + rédaction → brouillon |
| `monday_reminder.yml` | `0 11 * * 1` | lundi 07h / 06h           | Rappel Telegram à l'équipe : newsletter à valider |
| `monday_publish.yml`  | `0 13 * * 1` | lundi 09h / 08h           | Publication auto de la newsletter validée |

Intervention humaine : **~15 min le lundi** (relecture + clic Valider + `git push` de `afrotech.db`).

---

## Stabilité et limites connues

`tests/test_pipeline_stability.py` rejoue 4 cycles hebdomadaires consécutifs sur la même
base (scrape → résumé → sélection/rédaction → validation → publication), en injectant à
chaque semaine une panne réellement rencontrée en production : source RSS qui timeout,
coupure réseau, erreur inattendue du scraper, rate limit/timeout Gemini, échec Telegram
transitoire puis prolongé. `tests/test_scraper_stability.py` couvre isolément la
résilience de `scrape_rss()` à chacune de ces pannes réseau.

**Ce que ces tests garantissent :**
- une source, un résumé ou une publication en échec n'interrompt jamais le reste du
  pipeline (chaque étage isole ses erreurs et continue) ;
- toute erreur rencontrée est loguée (`[TIMEOUT]`, `[ERREUR RÉSEAU]`, `[RATE LIMIT/SERVEUR …]`,
  `[ÉCHEC] …`) — aucune ne passe silencieusement ;
- aucune fuite de ressources sur la durée : connexions SQLite toutes refermées, un seul
  client HTTP Telegram ouvert (et refermé) par tentative de publication.

**Correctif issu de ce travail de stabilisation :** `publisher/telegram_client.py` ouvrait
un nouveau client HTTP à chaque tentative d'envoi (y compris chaque retry) sans jamais le
fermer — une fuite de connexion par retry sur les publications en échec transitoire. Un
seul client est maintenant ouvert par appel à `envoyer_telegram()`, réutilisé pour tous les
morceaux/tentatives, et explicitement refermé à la fin (cf. `tests/test_telegram_client.py::test_un_seul_client_ouvert_puis_ferme_meme_avec_retries`).

**Limites connues (non résolues, par conception ou par contrainte de ressources) :**
- **Dédup intra-batch uniquement** — `orchestrator.py` déduplique les articles collectés le
  même jour entre eux, mais ne compare jamais un nouvel article contre ceux déjà en base :
  un même article republié par une source des semaines plus tard peut réapparaître sous une
  URL différente.
- **Quotas gratuits externes** — Gemini (résumé + rédaction) et l'API Bot Telegram tournent
  sur des paliers gratuits avec un rate limit par minute non documenté publiquement de façon
  stable ; le pipeline absorbe les 429/5xx transitoires via 3 tentatives et un backoff
  exponentiel (2s/4s/8s) par appel, mais une panne qui dépasse cette fenêtre fait échouer
  l'article ou la publication du jour (pas de file d'attente ni de retry inter-jours).
- **Panne prolongée (> quelques minutes)** — un service externe indisponible plus longtemps
  que les 3 tentatives ne bloque jamais le run (celui-ci se termine et alerte l'équipe via
  `notifier.py`), mais rien ne retente automatiquement le lendemain : l'article reste sans
  résumé, ou la newsletter validée reste au statut `validé` jusqu'à une republication
  manuelle (`streamlit run validation/review_ui.py`).
- **Pas de circuit breaker inter-runs** — chaque exécution de `daily_scrape.yml` retente
  toutes les sources actives depuis zéro, y compris celles en échec depuis plusieurs jours ;
  c'est simple et sans état à maintenir, mais ça veut dire qu'une source durablement morte
  continue de consommer un appel réseau (10s de timeout) à chaque run tant qu'elle n'est pas
  désactivée manuellement dans `data/sources.json`.

---

## Structure du projet

```
AfroTech-Pulse/
│
├── orchestrator.py          ← Point d'entrée quotidien : collecte + filtrage + dédup
├── database.py              ← Schéma SQLite, machine à états, toutes les requêtes
│
├── scraper/
│   └── main.py              ← Collecte les articles depuis les sources RSS
│
├── pipeline/
│   ├── filter.py            ← Score la pertinence africaine (0 à 100)
│   ├── dedup.py             ← Supprime doublons exacts et quasi-doublons
│   ├── summarize.py         ← Résume un article via Gemini (3 lignes, français)
│   ├── run_summarize.py     ← Résume en batch tous les articles pertinents non résumés
│   ├── editor.py            ← Sélectionne les 5-7 meilleurs articles de la semaine
│   └── run_editor.py        ← Lance la sélection éditoriale seule
│
├── newsletter/
│   ├── writer.py            ← Rédige la newsletter complète via Gemini
│   └── run_writer.py        ← Chaîne sélection + rédaction, sauvegarde en brouillon
│
├── validation/
│   └── review_ui.py         ← Validation humaine + panneau de publication assistée
│
├── publisher/
│   ├── publish.py           ← Orchestrateur multicanal + réindexation de l'archive
│   ├── run_publish.py       ← Point d'entrée de la publication auto (code de sortie + alerte)
│   ├── telegram_client.py   ← Canal actif — Telegram Bot API
│   └── email_client.py      ← En évolution — Resend (désactivé, domaine à vérifier)
│
├── notifier.py              ← Notifications internes à l'équipe (rappel, alerte d'échec)
│
├── archive/
│   ├── search.py            ← Index Whoosh et moteur de recherche full-text
│   └── app.py               ← Archive publique Streamlit
│
├── dashboard/
│   ├── app.py               ← Page Streamlit publique (5 visualisations + filtres)
│   ├── data.py              ← Seul module du dashboard qui touche SQLite
│   ├── enrichment.py        ← Détection pays (ISO-3) et secteurs
│   ├── aggregations.py      ← Agrégations pures : pays, secteurs, semaines, comparaison
│   ├── filters.py           ← Filtres période / pays / secteur
│   ├── entities.py          ← Extraction des acteurs cités
│   ├── text.py              ← Stopwords et comptage pour le nuage de mots
│   └── theme.py             ← Charte visuelle et gabarit Plotly
│
├── tests/                   ← Suite pytest complète
│
├── docs/
│   ├── architecture.md      ← Vue d'ensemble, dépendances, machine à états
│   ├── api.md               ← Référence des fonctions publiques
│   ├── audit_securite.md    ← Constats avant passage en open source
│   └── format_newsletter.md ← Gabarit de sortie du rédacteur LLM
│
├── data/
│   └── sources.json         ← Catalogue des sources surveillées
│
├── .github/workflows/
│   ├── daily_scrape.yml     ← Cron quotidien 6h UTC — collecte + résumés
│   ├── weekly_editor.yml    ← Cron dominical 20h UTC — sélection + rédaction
│   ├── monday_reminder.yml  ← Cron lundi 11h UTC — rappel de validation à l'équipe
│   └── monday_publish.yml   ← Cron lundi 13h UTC — publication automatique
│
├── .env.example             ← Modèle des variables d'environnement (à copier en .env)
├── requirements.txt         ← Dépendances Python
├── PRIVACY.md               ← Politique de confidentialité
├── CONTRIBUTING.md          ← Guide de contribution
└── README.md                ← Ce fichier
```

---

## Stack technique

| Niveau | Technologie | Usage |
|---|---|---|
| Collecte | feedparser + requests | Lecture des flux RSS |
| Traitement | sentence-transformers | Déduplication par similarité sémantique |
| Intelligence | Google Gemini API (`gemini-3.6-flash`) | Résumés + rédaction newsletter |
| Stockage | SQLite | Base de données locale des articles et éditions |
| Interfaces | Streamlit | Validation, archive, dashboard |
| Dashboard | Plotly | Carte choroplèthe, barres, timeline |
| Dashboard | wordcloud | Nuage de mots des tendances |
| Archive | Whoosh | Moteur de recherche full-text |
| Automatisation | GitHub Actions | Cron gratuit (2000 min/mois) |
| Publication | Telegram Bot API | Distribution de la newsletter (canal actif) |
| Publication (évolution) | Resend (email) + LinkedIn API | Développés/testés, désactivés en attendant liste d'abonnés / entité légale vérifiée |
| Configuration | python-dotenv | Lecture des clés API depuis `.env` |
| Tests | pytest | Suite de tests unitaires et d'intégration |

---

## Installation

**Prérequis** : Python 3.11 ou supérieur (la CI GitHub Actions tourne en 3.11) et Git.

```bash
# 1. Cloner le repo
git clone <url-repo>
cd AfroTech-Pulse

# 2. Créer et activer un environnement virtuel
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Ouvrir .env et remplir les clés API (voir la section Variables d'environnement)

# 5. Créer la base de données
python database.py

# 6. Vérifier que tout fonctionne
python -m pytest tests/ -v
```

> Le premier lancement du pipeline télécharge le modèle `sentence-transformers` utilisé par la
> déduplication (quelques centaines de Mo). C'est long une seule fois, puis mis en cache.

---

## Lancer chaque composant

Toutes les commandes se lancent depuis la racine du projet, environnement virtuel activé.

### Collecte quotidienne

```bash
python orchestrator.py
```
Visite les 50 sources RSS actives, score chaque article, déduplique le batch du jour et sauvegarde
les nouveaux articles dans `articles_raw`. Ne consomme aucun crédit LLM.

### Résumés LLM

```bash
python -m pipeline.run_summarize
python -m pipeline.run_summarize --limit 5     # limiter la consommation d'API
```
Résume tous les articles au-dessus du seuil de pertinence qui n'ont pas encore de résumé.
Nécessite `GEMINI_API_KEY`.

### Sélection éditoriale et rédaction

```bash
python -m newsletter.run_writer                # sélection + rédaction → brouillon
python -m newsletter.run_writer --seuil 50     # relever le seuil de pertinence

python -m pipeline.run_editor                  # sélection seule, sans rédaction
```
`run_writer` produit une newsletter complète en statut `brouillon`. Nécessite `GEMINI_API_KEY`.

### Validation humaine

```bash
streamlit run validation/review_ui.py
```
Affiche le dernier brouillon : édition du contenu, aperçu, historique des transitions, puis
Valider / Modifier / Rejeter. Une fois la newsletter validée, la même interface bascule sur un
panneau de publication avec checklist de sécurité avant envoi réel.

### Publication

```bash
python -m publisher.run_publish     # point d'entrée utilisé par le cron du lundi
python -m publisher.publish         # publication directe, sans code de sortie ni alerte
```
Publie la dernière newsletter validée sur tous les canaux actifs. `run_publish` est la variante
appelée par `monday_publish.yml` : elle sort en code d'erreur et alerte l'équipe sur Telegram si un
canal échoue. En pratique, la publication se déclenche soit par le cron du lundi, soit depuis
l'interface de validation ci-dessus. Nécessite `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHANNEL_ID`
(plus `TELEGRAM_ADMIN_CHAT_ID` pour les alertes).

> ⚠️ Cette commande envoie un message **réel** sur le canal Telegram, visible par tous les abonnés.

### Archive publique

```bash
streamlit run archive/app.py
```
Recherche full-text dans toutes les éditions publiées. Champ vide : toutes les éditions, de la plus
récente à la plus ancienne. L'index est construit automatiquement s'il est absent, et réindexé après
chaque publication réussie. Pour le régénérer à la main :

```bash
python archive/search.py
```

### Dashboard public

```bash
streamlit run dashboard/app.py
```
Carte choroplèthe des pays mentionnés, répartition sectorielle, timeline hebdomadaire, nuage
de mots et top acteurs cités. Les filtres de la barre latérale (période, pays, secteur) se
combinent et s'appliquent à l'ensemble des visualisations.

---

## Cycle de vie d'une newsletter

Chaque newsletter suit une machine à états stricte, définie dans `database.py`. Toute transition non
prévue lève une `ValueError`, et chaque transition appliquée est historisée avec son auteur.

```
brouillon ──→ en_revue ──→ validé ──→ publié
                   │
                   └─────→ rejeté
```

- **brouillon** — généré par `run_writer`, en attente de relecture
- **en_revue** — pris en charge par un validateur
- **validé** — prêt à publier ; c'est le seul statut depuis lequel la publication est autorisée
- **publié** — tous les canaux actifs ont réussi ; déclenche la réindexation de l'archive
- **rejeté** — état terminal, ne peut plus être publié

Un échec partiel de publication (un canal sur deux) laisse la newsletter en `validé` et permet de
republier uniquement le canal en échec, sans renvoyer sur celui qui a déjà réussi.

---

## Automatisations GitHub Actions

| Workflow | Déclenchement | Ce qu'il fait |
|---|---|---|
| `daily_scrape.yml` | Cron `0 6 * * *` (6h UTC, tous les jours) | `orchestrator.py` puis `pipeline.run_summarize`, et commit de `afrotech.db` |
| `weekly_editor.yml` | Cron `0 20 * * 0` (20h UTC, dimanche) | `newsletter.run_writer`, et commit de `afrotech.db` |
| `monday_reminder.yml` | Cron `0 11 * * 1` (11h UTC, lundi) | Alerte Telegram à l'équipe s'il reste une newsletter en `brouillon` à valider |
| `monday_publish.yml` | Cron `0 13 * * 1` (13h UTC, lundi) | `publisher.run_publish` : publie la newsletter `validé` si elle existe, sinon ne fait rien |

Les quatre workflows acceptent aussi un déclenchement manuel (`workflow_dispatch`) depuis l'onglet
Actions de GitHub. Les secrets `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID` et
`TELEGRAM_ADMIN_CHAT_ID` doivent être configurés dans le dépôt
(*Settings → Secrets and variables → Actions*).

> **La publication automatique lit la base depuis GitHub, pas depuis ton poste.** Après avoir
> validé une newsletter dans `review_ui.py`, il faut pousser `afrotech.db` (`git add afrotech.db
> && git commit && git push`) avant 13h UTC le lundi, sinon `monday_publish.yml` ne verra aucune
> newsletter validée et ne publiera rien.

> **Note sur la persistance** : la base `afrotech.db` est volontairement suivie par Git — c'est ce
> qui permet aux crons GitHub Actions de conserver l'état entre deux exécutions. Voir
> [docs/audit_securite.md](docs/audit_securite.md) pour les implications de ce choix avant tout
> passage du dépôt en public.

---

## Variables d'environnement

Copier `.env.example` en `.env` et remplir chaque valeur. Le fichier `.env` est ignoré par Git et
ne doit **jamais** être commité.

| Variable | Requise pour | Description | Où l'obtenir |
|---|---|---|---|
| `GEMINI_API_KEY` | Résumés et rédaction | Clé API Google Gemini | aistudio.google.com (gratuit, sans carte bancaire) |
| `TELEGRAM_BOT_TOKEN` | Publication | Token du bot qui publie sur le canal | @BotFather sur Telegram |
| `TELEGRAM_CHANNEL_ID` | Publication | Identifiant du canal (ex. `@ytilikan`) | Nom d'utilisateur choisi à la création du canal |
| `TELEGRAM_ADMIN_CHAT_ID` | Notifications internes | Conversation privée où `notifier.py` envoie les rappels de validation et les alertes d'échec | @userinfobot sur Telegram |
| `RESEND_API_KEY` | Email *(désactivé)* | Clé Resend | resend.com |
| `RESEND_FROM_EMAIL` | Email *(désactivé)* | Adresse d'expédition | Domaine vérifié dans Resend |
| `TWITTER_BEARER_TOKEN` | *(inutilisée)* | Prévue pour la collecte Twitter/X, aucun code ne la lit à ce jour | developer.twitter.com |

Sans `GEMINI_API_KEY`, la collecte (`orchestrator.py`) fonctionne normalement : seules les étapes de
résumé et de rédaction échouent avec un message explicite.

---

## Tests

```bash
python -m pytest tests/ -v          # toute la suite
python -m pytest tests/ -q          # sortie compacte
python -m pytest tests/test_publish.py -v   # un seul fichier
```

Les tests n'appellent aucune API externe et n'écrivent jamais dans la vraie base : chaque test
utilise une base SQLite temporaire et simule les clients réseau. Toute contribution doit laisser la
suite au vert.

---

## Stabilité et limites connues

`tests/test_pipeline_stability.py` rejoue 4 cycles hebdomadaires consécutifs sur la même
base (scrape → résumé → sélection/rédaction → validation → publication), en injectant à
chaque semaine une panne réellement rencontrée en production : source RSS qui timeout,
coupure réseau, erreur inattendue du scraper, rate limit/timeout Gemini, échec Telegram
transitoire puis prolongé. `tests/test_scraper_stability.py` couvre isolément la
résilience de `scrape_rss()` à chacune de ces pannes réseau.

**Ce que ces tests garantissent :**
- une source, un résumé ou une publication en échec n'interrompt jamais le reste du
  pipeline (chaque étage isole ses erreurs et continue) ;
- toute erreur rencontrée est loguée (`[TIMEOUT]`, `[ERREUR RÉSEAU]`, `[RATE LIMIT/SERVEUR …]`,
  `[ÉCHEC] …`) — aucune ne passe silencieusement ;
- aucune fuite de ressources sur la durée : connexions SQLite toutes refermées, un seul
  client HTTP Telegram ouvert (et refermé) par tentative de publication.

**Correctif issu de ce travail de stabilisation :** `publisher/telegram_client.py` ouvrait
un nouveau client HTTP à chaque tentative d'envoi (y compris chaque retry) sans jamais le
fermer — une fuite de connexion par retry sur les publications en échec transitoire. Un
seul client est maintenant ouvert par appel à `envoyer_telegram()`, réutilisé pour tous les
morceaux/tentatives, et explicitement refermé à la fin (cf. `tests/test_telegram_client.py::test_un_seul_client_ouvert_puis_ferme_meme_avec_retries`).

**Limites connues (non résolues, par conception ou par contrainte de ressources) :**
- **Dédup intra-batch uniquement** — `orchestrator.py` déduplique les articles collectés le
  même jour entre eux, mais ne compare jamais un nouvel article contre ceux déjà en base :
  un même article republié par une source des semaines plus tard peut réapparaître sous une
  URL différente.
- **Quotas gratuits externes** — Gemini (résumé + rédaction) et l'API Bot Telegram tournent
  sur des paliers gratuits avec un rate limit par minute non documenté publiquement de façon
  stable ; le pipeline absorbe les 429/5xx transitoires via 3 tentatives et un backoff
  exponentiel (2s/4s/8s) par appel, mais une panne qui dépasse cette fenêtre fait échouer
  l'article ou la publication du jour (pas de file d'attente ni de retry inter-jours).
- **Panne prolongée (> quelques minutes)** — un service externe indisponible plus longtemps
  que les 3 tentatives ne bloque jamais le run (celui-ci se termine et alerte l'équipe via
  `notifier.py`), mais rien ne retente automatiquement le lendemain : l'article reste sans
  résumé, ou la newsletter validée reste au statut `validé` jusqu'à une republication
  manuelle (`streamlit run validation/review_ui.py`).
- **Pas de circuit breaker inter-runs** — chaque exécution de `daily_scrape.yml` retente
  toutes les sources actives depuis zéro, y compris celles en échec depuis plusieurs jours ;
  c'est simple et sans état à maintenir, mais ça veut dire qu'une source durablement morte
  continue de consommer un appel réseau (10s de timeout) à chaque run tant qu'elle n'est pas
  désactivée manuellement dans `data/sources.json`.

---

## Sources surveillées

Le catalogue `data/sources.json` recense 86 sources réparties en 9 catégories. À ce jour, le scraper
ne collecte que les sources de type `rss` marquées actives, soit **50 sources**. Les 32 sources de
type web, API et PDF sont cataloguées pour une évolution future mais ne sont pas encore visitées.

| Catégorie | Exemples | Sources |
|---|---|---|
| Tech Afrique | Techpoint Africa, TechCabal, Disrupt Africa | 28 |
| Grands médias | MIT Tech Review, Wired | 17 |
| Recherche IA | arXiv, Hugging Face, Masakhane | 10 |
| Startups | Crunchbase, Y Combinator Africa | 10 |
| Institutions | Union Africaine, Banque Mondiale | 9 |
| Fintech | GSMA Mobile Economy Africa | 3 |
| Social | Twitter/X #AIAfrica, LinkedIn | 3 |
| Podcasts | The Flip Africa | 3 |
| Rapports | McKinsey | 3 |

---

## Documentation technique

| Document | Contenu |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Le pipeline en 10 étapes, l'articulation des modules, le graphe de dépendances entre fichiers, la machine à états des newsletters et les 4 workflows GitHub Actions |
| [docs/api.md](docs/api.md) | Référence des fonctions publiques de `database.py`, `pipeline/`, `publisher/` et `archive/search.py` — signature, paramètres, retour, exemple |
| [docs/format_newsletter.md](docs/format_newsletter.md) | Gabarit markdown imposé au rédacteur LLM |
| [docs/audit_securite.md](docs/audit_securite.md) | Constats de sécurité à traiter avant de rendre le dépôt public |

Pour comprendre le projet, lire `architecture.md` en premier : il donne la carte, `api.md`
donne le détail.

---

## Contribuer

Les contributions sont les bienvenues. Le guide complet — conventions de branches et de commits,
procédure de pull request, lancement des tests — est dans [CONTRIBUTING.md](CONTRIBUTING.md).

En résumé : brancher depuis `develop`, nommer la branche `feat/sNN-description` ou
`fix/description`, préfixer les commits (`feat`, `fix`, `docs`, `test`, `chore`), ouvrir la PR vers
`develop` avec la suite de tests au vert et une review approuvée.

---

## Licence

Licence non encore définie. En l'absence de fichier `LICENSE`, le code reste par défaut sous droits
réservés : personne ne peut légalement le réutiliser, le modifier ou le redistribuer. Une licence
doit être choisie avant tout passage du dépôt en public.

---

*Projet réalisé par l'Équipe Gamma — juin → septembre 2026*

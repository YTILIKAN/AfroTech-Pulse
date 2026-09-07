# AfroTech Pulse

AfroTech Pulse is an intelligent monitoring agent dedicated to Artificial Intelligence in Africa.

Every week, the system scans 50+ international sources, filters what truly matters for the African
continent, and automatically delivers a curated newsletter in French every Monday — no manual effort
required. A live public dashboard tracks the pulse of AI across Africa in real time: which countries
are leading, which sectors are rising, and which players are shaping the future.

AfroTech Pulse is the digital voice of the Y'TILIKAN community.
Built to inform, designed to last, published every week without exception.

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
- [Variables d'environnement](#variables-denvironnement)
- [Sources surveillées](#sources-surveillées)

---

## Vision

AfroTech Pulse n'est pas un simple agrégateur de flux RSS. C'est un agent IA doté d'une logique
de pertinence africaine : il surveille 50+ sources mondiales, sélectionne ce qui impacte réellement
le continent, contextualise avec un angle africain, rédige en français accessible et publie
automatiquement chaque lundi.

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

### 2. Dashboard public interactif
Visualisation des tendances IA en Afrique (`streamlit run dashboard/app.py`), sur les
4 dernières semaines :
- **V1 (livré)** : carte choroplèthe des pays mentionnés, répartition par secteur
  (fintech, santé, éducation, agriculture), volume hebdomadaire d'articles
- **V2 (à venir, S11)** : top acteurs mentionnés, nuage de mots, comparaison pays, filtres

Détails de conception : [`docs/s10_dashboard.md`](docs/s10_dashboard.md).

---

## Architecture du pipeline

Le projet fonctionne comme une chaîne de production automatique en 10 étapes.

```
CHAQUE JOUR (cron 0 6 * * *  —  daily_scrape.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 1 — Collecte
  └── Le scraper visite 50+ sources (RSS, sites web, APIs, PDFs)
      et sauvegarde les articles bruts dans SQLite

  Étape 2 — Filtrage
  └── Chaque article reçoit un score de pertinence africaine (0 à 1)
      Les articles sous 0.3 sont éliminés

  Étape 3 — Déduplication
  └── Les doublons exacts (même titre) et quasi-doublons
      (même sujet, mots différents) sont supprimés

  Étape 4 — Résumé LLM
  └── Gemini résume chaque article en 3 lignes en français
      avec angle africain obligatoire

CHAQUE DIMANCHE (cron 0 20 * * 0  —  weekly_editor.yml)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 5 — Sélection éditoriale
  └── Sélection des 5-7 meilleurs articles de la semaine
      selon : impact Afrique, nouveauté, diversité géographique

  Étape 6 — Rédaction newsletter
  └── Gemini rédige la newsletter complète, sauvegardée en 'brouillon'
      (intro édito + articles résumés + conclusion)

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
      Aucune newsletter validée -> rien ne part. Échec d'un canal -> run
      GitHub Actions en échec + alerte Telegram à l'équipe (jamais silencieux).
      Email, LinkedIn et site web : en évolution

EN CONTINU
━━━━━━━━━━
  Étape 9 — Dashboard
  └── Mise à jour en temps réel des visualisations publiques

  Étape 10 — Archive
  └── Toutes les éditions sont indexées et consultables publiquement
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
├── scraper/
│   └── main.py              ← Collecte les articles depuis 50+ sources
│
├── pipeline/
│   ├── filter.py            ← Score la pertinence africaine de chaque article
│   ├── dedup.py             ← Supprime les doublons
│   ├── summarize.py         ← Résume chaque article via Gemini (3 lignes, français)
│   └── editor.py            ← Sélectionne les 5-7 meilleurs articles de la semaine
│
├── newsletter/
│   ├── writer.py            ← Rédige la newsletter complète via Gemini
│   └── run_writer.py        ← Chaîne sélection éditoriale + rédaction, sauvegarde en brouillon
│
├── dashboard/
│   ├── app.py               ← Page Streamlit publique (KPIs + 3 graphiques Plotly)
│   ├── data.py              ← Accès SQLite + fenêtre 4 semaines complètes
│   ├── enrichment.py        ← Détection pays (ISO-3) + classification secteur
│   ├── aggregations.py      ← Agrégations par pays / secteur / semaine
│   └── theme.py             ← Palette de marque + gabarit Plotly commun
│
├── validation/
│   └── review_ui.py         ← Validation humaine + panneau de publication assistée
│
├── publisher/
│   ├── publish.py           ← Orchestrateur multicanal (marquage newsletters.statut)
│   ├── run_publish.py       ← Point d'entrée publication auto (exit code + alerte si échec)
│   ├── telegram_client.py   ← Canal actif — Telegram Bot API
│   └── email_client.py      ← En évolution — Resend (désactivé, domaine à vérifier)
│
├── notifier.py              ← Notifications internes équipe (rappel validation, alerte échec)
│
├── archive/
│   └── search.py            ← Moteur de recherche sur toutes les éditions passées
│
├── data/
│   └── sources.json         ← Liste des 50+ sources configurées
│
├── .github/
│   └── workflows/
│       ├── daily_scrape.yml    ← Cron quotidien — collecte + résumé
│       ├── weekly_editor.yml   ← Cron dimanche — sélection + rédaction
│       ├── monday_reminder.yml ← Cron lundi matin — rappel de validation à l'équipe
│       └── monday_publish.yml  ← Cron lundi — publication auto de la newsletter validée
│
├── .env.example             ← Modèle des variables d'environnement (à copier en .env)
├── requirements.txt         ← Toutes les dépendances Python à installer
└── README.md                ← Ce fichier
```

---

## Stack technique

| Niveau | Technologie | Usage |
|---|---|---|
| Collecte | feedparser | Lecture des flux RSS |
| Collecte | requests + BeautifulSoup4 | Scraping des sites web |
| Traitement | sentence-transformers | Déduplication par similarité sémantique |
| Intelligence | Google Gemini API (gemini-3.6-flash) | Résumés + sélection + rédaction newsletter |
| Stockage | SQLite | Base de données locale des articles |
| Dashboard | Streamlit + Plotly | Interface publique et visualisations |
| Automatisation | GitHub Actions | Cron quotidien gratuit (2000 min/mois) |
| Publication | Telegram Bot API | Distribution de la newsletter (canal actif) |
| Publication (évolution) | Resend (email) + LinkedIn API | Développés/testés, désactivés en attendant liste d'abonnés / entité légale vérifiée |
| Archive | Whoosh | Moteur de recherche full-text |
| Configuration | python-dotenv | Lecture sécurisée des clés API |

---

## Installation

```bash
# 1. Cloner le repo
git clone <url-repo>
cd AfroTech-Pulse

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Ouvrir .env et remplir les clés API

# 4. Lancer le scraper manuellement
python scraper/main.py

# 5. Lancer le dashboard
streamlit run dashboard/app.py
```

---

## Variables d'environnement

Copier `.env.example` en `.env` et remplir chaque valeur.

| Variable | Description | Où l'obtenir |
|---|---|---|
| `GEMINI_API_KEY` | Clé API Google Gemini pour les résumés/rédaction LLM | aistudio.google.com (gratuit, sans carte bancaire) |
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram qui publie sur le canal | @BotFather sur Telegram |
| `TELEGRAM_CHANNEL_ID` | Identifiant du canal Telegram **public** où est publiée la newsletter (ex. `@ytilikan`) | Nom d'utilisateur choisi à la création du canal |
| `TELEGRAM_ADMIN_CHAT_ID` | Identifiant du groupe **privé** de l'équipe (rappels de validation, alertes d'échec) — jamais visible des abonnés | Ajouter le bot au groupe, puis lire `chat.id` via `getUpdates` |
| `TWITTER_BEARER_TOKEN` | Token Twitter API v2 (lecture seule) | developer.twitter.com |
| `RESEND_API_KEY` | Clé Resend pour les emails *(en évolution, pas encore actif)* | resend.com |
| `RESEND_FROM_EMAIL` | Adresse d'expédition *(en évolution, domaine à vérifier)* | Domaine vérifié dans Resend |


---

## Sources surveillées

50+ sources réparties en 8 catégories dans `data/sources.json` :

| Catégorie | Exemples | Type |
|---|---|---|
| Recherche IA | arXiv, Hugging Face, Masakhane | RSS / Web |
| Tech Afrique | Techpoint Africa, Disrupt Africa | RSS |
| Fintech | GSMA Mobile Economy Africa | PDF |
| Startups | Crunchbase, Y Combinator Africa | API / Web |
| Grands médias | MIT Tech Review, Wired | RSS |
| Institutions | Union Africaine, Banque Mondiale | Web / PDF |
| Social | Twitter/X #AIAfrica, LinkedIn | API |
| Podcasts & Rapports | The Flip Africa, McKinsey | RSS / PDF |

---

*Projet réalisé par l'Équipe Gamma — juin → septembre 2025*

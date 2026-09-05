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
- [Structure du projet](#structure-du-projet)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Variables d'environnement](#variables-denvironnement)
- [Sources surveillées](#sources-surveillées)
- [Planning](#planning)

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
Visualisation des tendances IA en Afrique en temps réel :
- Carte géographique des pays les plus mentionnés
- Graphiques par secteur (fintech, santé, éducation, agriculture)
- Timeline des articles
- Top acteurs mentionnés
- Nuage de mots tendances

---

## Architecture du pipeline

Le projet fonctionne comme une chaîne de production automatique en 10 étapes.

```
CHAQUE JOUR (6h UTC automatique)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

CHAQUE DIMANCHE SOIR (automatique)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 5 — Sélection éditoriale
  └── Sélection des 5-7 meilleurs articles de la semaine
      selon : impact Afrique, nouveauté, diversité géographique

  Étape 6 — Rédaction newsletter
  └── Gemini rédige la newsletter complète
      (intro édito + articles résumés + conclusion)

CHAQUE LUNDI MATIN (manuel, 15 min)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 7 — Validation humaine
  └── Un membre de l'équipe lit la newsletter générée
      et appuie sur Valider / Modifier / Rejeter

CHAQUE LUNDI 9H (automatique après validation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 8 — Publication
  └── Envoi sur le Channel Telegram Y'TILIKAN (canal actif)
      Email, LinkedIn et site web : en évolution

EN CONTINU
━━━━━━━━━━
  Étape 9 — Dashboard
  └── Mise à jour en temps réel des visualisations publiques

  Étape 10 — Archive
  └── Toutes les éditions sont indexées et consultables publiquement
```

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
│   └── app.py               ← Interface Streamlit publique (carte + graphiques)
│
├── validation/
│   └── review_ui.py         ← Validation humaine + panneau de publication assistée
│
├── publisher/
│   ├── publish.py           ← Orchestrateur multicanal (marquage newsletters.statut)
│   ├── telegram_client.py   ← Canal actif — Telegram Bot API
│   └── email_client.py      ← En évolution — Resend (désactivé, domaine à vérifier)
│
├── archive/
│   └── search.py            ← Moteur de recherche sur toutes les éditions passées
│
├── data/
│   └── sources.json         ← Liste des 50+ sources configurées
│
├── .github/
│   └── workflows/
│       └── daily_scrape.yml ← Cron GitHub Actions — déclenche le scraper chaque jour à 6h UTC
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
| `TELEGRAM_CHANNEL_ID` | Identifiant du canal Telegram (ex. `@ytilikan`) | Nom d'utilisateur choisi à la création du canal |
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

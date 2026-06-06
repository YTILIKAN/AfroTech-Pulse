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
Publiée chaque lundi sur WhatsApp Channel, LinkedIn et le site web. Entièrement générée par un
agent LLM (Mistral), avec une validation humaine de 15 minutes avant publication.

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
  └── Mistral résume chaque article en 3 lignes en français
      avec angle africain obligatoire

CHAQUE DIMANCHE SOIR (automatique)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 5 — Sélection éditoriale
  └── Mistral sélectionne les 5-7 meilleurs articles de la semaine
      selon : impact Afrique, nouveauté, diversité géographique

  Étape 6 — Rédaction newsletter
  └── Mistral rédige la newsletter complète
      (intro édito + articles résumés + conclusion)

CHAQUE LUNDI MATIN (manuel, 15 min)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 7 — Validation humaine
  └── Un membre de l'équipe lit la newsletter générée
      et appuie sur Valider / Modifier / Rejeter

CHAQUE LUNDI 9H (automatique après validation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Étape 8 — Publication
  └── Envoi simultané sur WhatsApp Channel + LinkedIn + site web

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
│   ├── summarize.py         ← Résume chaque article via Mistral (3 lignes, français)
│   └── editor.py            ← Sélectionne les 5-7 meilleurs articles de la semaine
│
├── newsletter/
│   └── writer.py            ← Rédige la newsletter complète via Mistral
│
├── dashboard/
│   └── app.py               ← Interface Streamlit publique (carte + graphiques)
│
├── validation/
│   └── review_ui.py         ← Interface de validation humaine (lundi matin, 15 min)
│
├── publisher/
│   └── publish.py           ← Publie sur WhatsApp + LinkedIn + site web
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
| Intelligence | Mistral API (mistral-small-latest) | Résumés + sélection + rédaction newsletter |
| Stockage | SQLite | Base de données locale des articles |
| Dashboard | Streamlit + Plotly | Interface publique et visualisations |
| Automatisation | GitHub Actions | Cron quotidien gratuit (2000 min/mois) |
| Publication | WhatsApp Business API + LinkedIn API | Distribution de la newsletter |
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
| `MISTRAL_API_KEY` | Clé API Mistral pour les résumés LLM | console.mistral.ai |
| `WHATSAPP_TOKEN` | Token WhatsApp Business API | Meta for Developers |
| `LINKEDIN_TOKEN` | Token LinkedIn API | LinkedIn Developers |
| `TWITTER_BEARER_TOKEN` | Token Twitter API v2 (lecture seule) | developer.twitter.com |
| `RESEND_API_KEY` | Clé Resend pour les emails | resend.com |


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

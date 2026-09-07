# S10 — Dashboard V1 : notes de conception

Livrable : `dashboard/app.py` + package `dashboard/` (structure, carte, secteurs, timeline).

## Périmètre des données affichées

- **Fenêtre** : les 4 dernières semaines **complètes** (lundi → dimanche). La semaine en
  cours est partielle et exclue — sinon la dernière barre de la timeline serait toujours
  quasi vide (`lundi_courant()` = borne haute exclue).
- **Filtre de pertinence** : seuls les articles avec `score_pertinence >= 1` — au moins un
  signal africain détecté par `pipeline/filter.py` (pays, ville, organisation, source
  africaine). `score == 0` = aucun lien Afrique (ex. un papier arXiv de ML générique) →
  hors sujet pour un dashboard « IA **en Afrique** ». Sur la base actuelle : ~600 articles
  retenus sur ~1200 collectés.
- Conséquence visible : la timeline montre une **forte croissance** (≈18 → ≈430
  articles/semaine) — c'est réel, la collecte a monté en puissance début septembre 2026.

## Architecture

| Module | Responsabilité | Testé par |
|---|---|---|
| `dashboard/data.py` | Seul accès SQLite. `charger_articles(db_path, depuis)` + `fenetre_semaines()` | `test_dashboard_data.py` |
| `dashboard/enrichment.py` | `detecter_pays()` (→ ISO-3), `classer_secteurs()`, `enrichir()` | `test_dashboard_enrichment.py` |
| `dashboard/aggregations.py` | `par_pays()`, `par_secteur()`, `par_semaine()` — fonctions pures | `test_dashboard_aggregations.py` |
| `dashboard/theme.py` | Palette de marque + gabarit Plotly commun (`.streamlit/config.toml` pour le thème Streamlit) | — |
| `dashboard/app.py` | Page Streamlit (KPIs + 3 graphiques Plotly), `@st.cache_data` | `test_dashboard_integration.py` |

## Détection du pays (carte choroplèthe)

- Mapping codé en dur dans `enrichment.py` : ~55 pays africains, variantes FR/EN → code
  ISO-3166-1 alpha-3 (attendu par `plotly.express.choropleth(scope="africa")`).
- Table villes → pays (Lagos → NGA, Cape Town → ZAF, …) : une mention de ville vaut
  une mention du pays.
- Recherche par **mot entier** (regex avec bornes) : « niger » ne matche pas dans
  « nigeria », « mali » ne matche pas dans « e-mail ».
- Une seule regex alternation compilée par catégorie (perf, cf. plus bas).
- Les termes génériques (`africa`, `african`, `afrique`) **ne comptent pas** comme un pays.
- Titre prioritaire sur le corps ; termes les plus longs prioritaires
  (« guinée équatoriale » avant « guinée »).

## Classification par secteur

- 4 secteurs cibles : `fintech`, `santé`, `éducation`, `agriculture`.
- Mots-clés **FR + EN** par secteur (`SECTEURS_MOTS_CLES`).
- ⚠️ Les mots collisionnant avec le vocabulaire IA générique sont **exclus** : `learning`
  (« machine learning »), `apprentissage` (« apprentissage automatique »), `formation`
  (« formation d'un modèle »), `culture` (société), `prêt` (« prêt à »). Sans ça, tous les
  papiers arXiv cs.LG tombaient en « éducation ».
- Indice tiré de la catégorie `data/sources.json` : catégorie `Fintech` → force `fintech`.
- Un article peut appartenir à **plusieurs** secteurs (compté dans chacun).
- **Aucun secteur détecté → `["généraliste"]`** : garantit le critère d'acceptation
  « chaque article est classé dans au moins un secteur ». Le KPI « secteurs identifiés »
  exclut `généraliste`.

## Performance (`test_dashboard_perf.py`)

Mesure : chargement + enrichissement + 3 agrégations sur la base de production.

| Version | Articles (fenêtre 4 sem.) | Durée | Seuil |
|---|---|---|---|
| regex par mot-clé (naïf), sans filtre pertinence | 1195 | ~5,6 s | 3,0 s ❌ |
| **regex alternation compilée + filtre `score >= 1`** | **~610** | **~0,06 s** | 3,0 s ✅ |

Le test échoue si la durée dépasse 3 s — garde-fou contre une régression de perf si la
liste de mots-clés grossit.

## Hors périmètre (→ S11 / #38)

Nuage de mots, top acteurs mentionnés, comparaison pays, filtres interactifs.

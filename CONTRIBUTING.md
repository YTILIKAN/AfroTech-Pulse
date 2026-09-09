# Contribuer à AfroTech Pulse

Merci de votre intérêt pour le projet. Ce guide décrit comment mettre en place
l'environnement, la convention de code, et la procédure de pull request.

---

## Table des matières

- [Mise en place](#mise-en-place)
- [Organisation du dépôt](#organisation-du-dépôt)
- [Workflow Git](#workflow-git)
- [Convention de commits](#convention-de-commits)
- [Convention de code](#convention-de-code)
- [Tests](#tests)
- [Procédure de pull request](#procédure-de-pull-request)
- [Signaler un bug ou proposer une évolution](#signaler-un-bug-ou-proposer-une-évolution)

---

## Mise en place

Prérequis : **Python 3.11** et **git**.

```bash
git clone <url-repo>
cd AfroTech-Pulse

python -m venv .venv
source .venv/bin/activate           # Windows : .venv\Scripts\activate

pip install -r requirements.txt
pip install pytest

cp .env.example .env                 # Windows : copy .env.example .env
# renseigner les clés — voir le README, section « Variables d'environnement »
```

La première installation télécharge `sentence-transformers` (PyTorch, ~2 Go).

Vérifier que tout fonctionne :

```bash
pytest -q
```

---

## Organisation du dépôt

Le détail de chaque module est dans le [README](README.md) (sections
« Structure du projet » et « Lancer chaque composant ») et dans
[`docs/`](docs/). En résumé :

| Dossier | Rôle |
|---|---|
| `scraper/` | Collecte des articles depuis les sources RSS / web / PDF |
| `pipeline/` | Filtrage de pertinence, déduplication, résumé LLM, sélection éditoriale |
| `newsletter/` | Rédaction de la newsletter via Gemini |
| `validation/` | Interface Streamlit de validation humaine |
| `publisher/` | Publication multicanal (Telegram actif, email en évolution) |
| `dashboard/` | Dashboard public Streamlit |
| `archive/` | Index Whoosh + recherche full-text des éditions passées |
| `database.py` | Accès SQLite — point d'entrée unique de la persistance |
| `tests/` | Suite pytest |

---

## Workflow Git

Le dépôt suit un **git-flow** simplifié :

```
main       ← version stable, déployée. Jamais de commit direct.
develop    ← intégration continue. Jamais de commit direct.
feature/*  ← une branche par tâche, partant de develop
```

1. Partir de `develop` à jour :
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feat/sX-description       # ou fix/... ou docs/... ou chore/...
   ```
2. Committer au fil de l'eau (voir la convention ci-dessous).
3. Ouvrir une **pull request vers `develop`** (jamais vers `main`).
4. Après relecture et validation, la PR est fusionnée dans `develop`.
5. `develop` est fusionné dans `main` par lot, lors d'une mise en production.

Nommage des branches : `feat/sX-sujet-court`, `fix/sujet`, `docs/sujet`, `chore/sujet`.

---

## Convention de commits

Format : `type(scope): description courte à l'impératif`

```
feat(s11): dashboard V2 — filtres, nuage de mots, comparaison pays
fix(tests): AppTest.get("imgs") -> "image", clé renommée par Streamlit
docs(s15): guide de contribution
chore(s14): simulation de 4 cycles hebdomadaires
```

- **type** : `feat`, `fix`, `docs`, `chore`, `refactor`, `test`
- **scope** : le numéro de sprint (`s11`, `s14`…) ou le module (`tests`, `publisher`…)
- Le corps du message explique le *pourquoi* si ce n'est pas évident.
- Référencer l'issue : `Refs #49` dans le corps, `Closes #49` sur le dernier commit
  ou dans la description de la PR.

---

## Convention de code

- **Style** : PEP 8, indentation 4 espaces, lignes ≤ 100 caractères.
- **Nommage** : identifiants et messages en français (le projet est francophone),
  cohérents avec le code existant.
- **Docstrings** : chaque module et chaque fonction publique porte une docstring
  qui explique son rôle et, si utile, ses choix de conception.
- **Secrets** : toujours via `os.getenv(...)`, jamais de valeur en dur, jamais de
  secret commité. `.env` est ignoré par Git.
- **Base de données** : passer par `database.py`, ne pas ouvrir de connexion
  `sqlite3` ailleurs.
- **Erreurs réseau** : une source, un résumé ou une publication en échec ne doit
  jamais interrompre le reste du pipeline ; toute erreur est loguée, jamais
  silencieuse (voir le README, section « Stabilité et limites connues »).

---

## Tests

```bash
pytest -q                                    # toute la suite
pytest tests/test_pipeline_stability.py -v   # tests de résilience réseau
```

- Les tests n'appellent **aucun service externe** : Gemini et Telegram sont
  simulés, la base est une SQLite temporaire (`tmp_path`).
- Toute nouvelle fonctionnalité ou correction de bug est accompagnée d'un test.
- La suite complète doit passer avant d'ouvrir une PR.

---

## Procédure de pull request

1. Vérifier que `pytest -q` passe et que la branche est à jour avec `develop`.
2. Ouvrir la PR **vers `develop`**, en *draft* tant que le travail est en cours.
3. Décrire : ce que fait la PR, comment la tester, l'issue liée (`Closes #N`).
4. Passer la PR en *ready for review* et demander une relecture.
5. Répondre aux commentaires par de nouveaux commits (ne pas réécrire l'historique
   d'une PR en cours de revue).
6. La fusion est faite par le relecteur une fois la PR approuvée.

---

## Signaler un bug ou proposer une évolution

Ouvrir une *issue* GitHub en décrivant :

- **Bug** : comportement attendu, comportement observé, étapes pour reproduire,
  logs éventuels.
- **Évolution** : le besoin, le contexte, une proposition de solution si possible.

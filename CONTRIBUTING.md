# Contribuer à AfroTech Pulse

Merci de l'intérêt porté au projet. Ce guide décrit comment installer l'environnement, quelles
conventions respecter et comment soumettre une contribution.

---

## Sommaire

- [Prérequis](#prérequis)
- [Lancer le projet en local](#lancer-le-projet-en-local)
- [Convention de nommage des branches](#convention-de-nommage-des-branches)
- [Convention des commits](#convention-des-commits)
- [Procédure de pull request](#procédure-de-pull-request)
- [Lancer les tests](#lancer-les-tests)
- [Style de code](#style-de-code)
- [Signaler un bug ou proposer une fonctionnalité](#signaler-un-bug-ou-proposer-une-fonctionnalité)

---

## Prérequis

- **Python 3.11 ou supérieur** — la CI GitHub Actions tourne en 3.11, c'est la version de référence
- **Git**
- Un compte **Google AI Studio** pour obtenir une `GEMINI_API_KEY` (gratuite, sans carte bancaire)
  si tu travailles sur les étapes de résumé ou de rédaction

Aucune clé n'est nécessaire pour contribuer sur la collecte, le filtrage, la déduplication, la base
de données ou les tests : la suite de tests ne fait aucun appel réseau.

---

## Lancer le projet en local

```bash
# 1. Forker puis cloner le dépôt
git clone <url-de-ton-fork>
cd AfroTech-Pulse

# 2. Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Remplir les clés nécessaires — voir la section Variables d'environnement du README

# 5. Créer la base de données locale
python database.py

# 6. Vérifier l'installation
python -m pytest tests/ -v
```

Le détail de chaque composant (collecte, résumés, rédaction, validation, publication, archive) est
documenté dans la section [Lancer chaque composant](README.md#lancer-chaque-composant) du README.

Avant de toucher au code, deux lectures utiles : [docs/architecture.md](docs/architecture.md)
pour comprendre comment les modules s'articulent et ce qu'il ne faut pas casser (notamment
que `database.py` ne dépend d'aucun autre module), et [docs/api.md](docs/api.md) pour la
signature exacte des fonctions publiques.

### Règles de sécurité à respecter

- Ne commite **jamais** le fichier `.env` ni aucune clé API. Il est ignoré par Git — laisse-le ainsi.
- N'ajoute jamais de clé, token ou mot de passe en dur dans le code. Toute valeur secrète se lit via
  `os.getenv()`, avec un message d'erreur explicite si elle manque (voir `pipeline/summarize.py`).
- N'ajoute jamais de donnée personnelle réelle (adresse email, nom d'abonné) dans un test, une
  fixture ou la base versionnée. Utilise des valeurs factices du type `test@exemple.com`.
- La commande `python -m publisher.publish` envoie un message **réel** sur le canal Telegram. Ne la
  lance pas pour tester : la suite de tests simule intégralement les clients réseau.

---

## Convention de nommage des branches

Toutes les branches partent de `develop`.

| Type | Format | Exemple |
|---|---|---|
| Fonctionnalité rattachée à un sprint | `feat/sNN-description-courte` | `feat/s13-archive-moteur-recherche` |
| Fonctionnalité hors sprint | `feat/description-courte` | `feat/rss-sources-50` |
| Correction de bug | `fix/description-courte` | `fix/cron-orchestrateur` |
| Documentation seule | `docs/description-courte` | `docs/guide-contribution` |

En minuscules, mots séparés par des tirets, sans accent ni caractère spécial. `NN` est le numéro du
sprint correspondant.

```bash
git checkout develop
git pull origin develop
git checkout -b feat/s16-nouvelle-fonctionnalite
```

---

## Convention des commits

Format : `type(portée) : description à l'impératif`

La portée est facultative mais recommandée quand un sprint est rattaché.

| Type | Quand l'utiliser |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `docs` | Documentation seule, aucun code modifié |
| `test` | Ajout ou modification de tests uniquement |
| `chore` | Maintenance : dépendances, configuration, CI, nettoyage |
| `refactor` | Réécriture sans changement de comportement |

**Exemples valides :**

```
feat(s13) : ajoute le moteur de recherche full-text Whoosh
fix : corrige le découpage des messages Telegram au-delà de 4096 caractères
docs : documente les variables d'environnement dans le README
test : couvre la republication d'un canal en échec
chore : ajoute pytest aux dépendances
```

Écris la description en français, à l'impératif présent, sans point final. Un commit doit faire une
seule chose : si tu dois écrire « et » dans la description, découpe-le en deux commits.

---

## Procédure de pull request

1. **Cible** : toutes les PR sont ouvertes vers `develop`, jamais vers `main`. `main` ne reçoit que
   les merges de `develop` au moment des mises en production.
2. **Tests obligatoires** : la suite complète doit passer au vert avant l'ouverture de la PR. Une PR
   avec des tests en échec ne sera pas relue.
3. **Tests pour tout nouveau code** : toute fonctionnalité ou correction s'accompagne des tests
   correspondants dans `tests/`. Une correction de bug ajoute au minimum un test qui échouerait sans
   le correctif.
4. **Review requise** : au moins une approbation d'un autre membre de l'équipe est nécessaire pour
   merger. Ne merge jamais ta propre PR sans review.
5. **Description de la PR** : explique ce que fait la contribution et pourquoi. Si elle répond à une
   issue, référence-la (`Closes #47`). Signale explicitement tout changement de comportement, toute
   migration de base de données et toute nouvelle dépendance.
6. **Portée** : une PR traite un seul sujet. Les changements de formatage sans rapport, la
   documentation d'une autre fonctionnalité ou les refactorings opportunistes vont dans une PR
   séparée — ils rendent la relecture bien plus difficile.

Avant d'ouvrir la PR :

```bash
git checkout develop
git pull origin develop
git checkout ma-branche
git rebase develop            # résoudre les conflits ici, pas dans la PR
python -m pytest tests/ -v    # tout doit être au vert
git push origin ma-branche
```

---

## Lancer les tests

```bash
python -m pytest tests/ -v                      # toute la suite, détaillée
python -m pytest tests/ -q                      # sortie compacte
python -m pytest tests/test_publish.py -v       # un seul fichier
python -m pytest tests/ -k "telegram" -v        # les tests dont le nom contient "telegram"
python -m pytest tests/ -x                      # s'arrêter au premier échec
```

### Comment les tests sont écrits

Le projet utilise `pytest` avec les fixtures `monkeypatch` et `tmp_path`. Trois règles à respecter
en écrivant un nouveau test :

- **Jamais d'appel réseau réel.** Les clients Gemini, Telegram et Resend sont remplacés par des
  doublures via `monkeypatch`. Un test qui appelle une vraie API est un test qui échouera en CI.
- **Jamais d'écriture dans la vraie base.** Redirige `database.DB_PATH` vers `tmp_path` :

  ```python
  def test_ma_fonctionnalite(monkeypatch, tmp_path):
      monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
      database.creer_base()
      # ...
  ```

- **Un message d'assertion explicite.** Il doit dire ce qui est attendu et pourquoi, pas répéter le
  code :

  ```python
  assert newsletter[3] == "validé", "un échec ne doit jamais marquer statut = publié"
  ```

Les statuts de newsletter suivent une machine à états stricte : une transition directe de
`brouillon` à `publié` lève une `ValueError`. Un test qui prépare une newsletter publiée doit
enchaîner tout le cycle `brouillon → en_revue → validé → publié`.

---

## Style de code

Le code suit les conventions déjà en place dans le dépôt :

- **Français** pour les noms de fonctions et variables métier (`sauvegarder_newsletter`,
  `score_editorial`, `canaux_restants`), les messages affichés et les commentaires.
- **Préfixe `_`** pour les fonctions internes à un module (`_publier_canal`, `_titre_edition`).
- **Commentaires qui expliquent le pourquoi**, pas le quoi. Les commentaires les plus utiles du
  projet documentent une décision et sa raison — voir `database.py:15` sur la désactivation du canal
  email, ou `publisher/email_client.py:17` sur l'absence de mise en cache du client.
- **Constantes en majuscules** en tête de module (`SEUIL_PERTINENCE`, `MAX_TENTATIVES`).
- Lignes limitées à ~100 caractères, docstrings pour les fonctions publiques non triviales.

Aucun formateur automatique n'est imposé à ce jour. Aligne-toi sur le fichier que tu modifies.

---

## Signaler un bug ou proposer une fonctionnalité

Ouvre une issue sur GitHub en précisant :

- **Pour un bug** : ce qui était attendu, ce qui s'est produit, la commande lancée, le message
  d'erreur complet, ta version de Python et ton système d'exploitation.
- **Pour une fonctionnalité** : le besoin auquel elle répond et l'étape du pipeline concernée.

Merci de ne jamais inclure de clé API, de token ou d'adresse email réelle dans une issue — les
issues sont publiques.

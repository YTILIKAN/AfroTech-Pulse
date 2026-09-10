# Audit de sécurité — avant publication open source

**Périmètre** : les fichiers suivis par Git et l'historique complet.
**Contexte** : issue #49 — préparer le dépôt à une visibilité publique.
**Date** : septembre 2026.

Ce document **constate**. Les corrections des points 🔴 demandent une décision
d'équipe (l'une implique une réécriture d'historique) et sont à traiter au
moment de la migration d'hébergement, avant tout passage du dépôt en public.

---

## Résumé

| # | Constat | Gravité | État |
|---|---|---|---|
| 1 | `.env` ignoré par Git, jamais commité | — | ✅ Conforme |
| 2 | Aucune clé API en dur dans le code ni dans l'historique | — | ✅ Conforme |
| 3 | Tous les secrets lus via `os.getenv()`, échec explicite si absent | — | ✅ Conforme |
| 4 | `afrotech.db`, suivi par Git, contient 3 adresses email réelles | 🔴 Critique | ⚠️ À traiter |
| 5 | Les crons GitHub Actions recommitent `afrotech.db` à chaque exécution | 🔴 Critique | ⚠️ À traiter |
| 6 | Pas de scan de secrets automatisé (aucune CI de sécurité) | 🟡 Mineur | À mettre en place |
| 7 | `.pytest_cache/` et `.claude/` n'étaient pas ignorés | 🟡 Mineur | ✅ Corrigé (ce commit) |

**Conclusion : le dépôt ne doit pas être rendu public tant que les points 4 et 5
ne sont pas traités.** Ils publieraient des données personnelles de façon
irréversible.

---

## ✅ Ce qui est conforme

### 1. Gestion de `.env`

`.env` est en ligne 2 du `.gitignore` et n'a jamais été suivi. Seul `.env.example`
(valeurs vides + commentaires) est commité.

```bash
git ls-files | grep -E '^\.env$'      # → aucune sortie
git check-ignore -v .env              # → .gitignore:2:.env
```

### 2. Aucune clé en dur

Recherche des motifs de clés (Gemini `AIzaSy…`, token bot Telegram `NNNNNNNNN:AA…`,
Resend `re_…`, OpenAI `sk-…`, clés privées PEM) sur **HEAD** et sur **tout
l'historique** : aucun résultat.

```bash
git rev-list --all | while read c; do
  git grep -nIE "AIzaSy[A-Za-z0-9_-]{20,}|[0-9]{9,10}:AA[A-Za-z0-9_-]{33}|re_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----" "$c" 2>/dev/null
done
# → aucune sortie
```

### 3. Lecture des secrets

Toutes les variables sensibles sont lues via `os.getenv(...)` :
`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`,
`TELEGRAM_ADMIN_CHAT_ID`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`. Aucune valeur de
repli en dur. Une variable manquante lève `RuntimeError` avec un message clair.

En production, ces valeurs vivent dans les *Secrets* du dépôt GitHub, jamais dans
un fichier.

---

## ⚠️ À traiter avant le passage en public

### 4. Données personnelles dans `afrotech.db` 🔴

Le fichier `afrotech.db` est **suivi par Git** (choix assumé, cf. `.gitignore`
ligne 18 : persistance de l'état entre exécutions des crons). Sa table
`abonnes_email` contient **3 adresses email réelles** de membres de l'équipe.

Ces adresses sont présentes :
- dans la version actuelle du fichier ;
- dans **l'historique** — `afrotech.db` a été modifié par ~15 commits.

Rendre le dépôt public exposerait ces adresses de façon **irréversible** (forks,
caches de moteurs de recherche, archivage tiers).

**Options (décision d'équipe) :**

| Option | Effet |
|---|---|
| A. Vider `abonnes_email` et repartir d'une base propre | supprime les données du présent, **pas de l'historique** |
| B. Sortir `afrotech.db` du suivi Git + persistance ailleurs (volume, base managée, branche `data/` privée) | supprime le problème pour l'avenir, **pas l'historique** |
| C. Réécrire l'historique : `git filter-repo --path afrotech.db --invert-paths` | supprime toutes les versions du fichier de l'historique ; **force-push coordonné**, tout le monde re-clone |

En pratique : **(A ou B) + C**. À faire au moment de la migration d'hébergement.

### 5. Recommit automatique de `afrotech.db` par les crons 🔴

`daily_scrape.yml`, `weekly_editor.yml` et `monday_publish.yml` committent
`afrotech.db` (`file_pattern: "afrotech.db"`). Tant que la persistance passe par
Git, **toute nouvelle donnée d'abonné saisie sera automatiquement publiée** au
prochain run. Le point 4 ne peut pas être « corrigé une fois » sans changer ce
mécanisme (option B).

---

## 🟡 À améliorer

### 6. Scan de secrets automatisé

Aucun workflow ne vérifie l'absence de secrets. Ajouter un job CI **gitleaks**
(ou `trufflehog`) sur les pull requests :

```bash
docker run --rm -v "${PWD}:/repo" zricethezav/gitleaks:latest detect --source /repo -v
```

### 7. Dossiers non ignorés

`.pytest_cache/` et `.claude/` n'étaient pas dans `.gitignore` — corrigé dans le
même commit que ce document.

---

## Tests de l'issue #49 (à exécuter avant la fusion)

- [ ] `pytest -q` passe sur un environnement propre.
- [ ] `gitleaks detect` ne remonte rien.
- [ ] **Test « from scratch »** : sur une machine vierge, `git clone` + suivre
      uniquement le README → le projet démarre. Consigner le résultat dans la PR.

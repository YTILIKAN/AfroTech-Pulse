# Audit de sécurité — avant publication open source

**Date de l'audit** : 6 septembre 2026
**Périmètre** : les 45 fichiers suivis par Git et l'intégralité de l'historique (89 commits)
**Contexte** : issue #49 — documentation complète et publication open source

Ce document constate. Il ne modifie ni les données, ni l'historique : les corrections proposées
demandent des décisions d'équipe et, pour l'une d'entre elles, une opération destructive.

---

## Résumé

| # | Constat | Gravité | État |
|---|---|---|---|
| 1 | `.env` correctement ignoré et jamais commité | — | ✅ Conforme |
| 2 | Aucune clé API en dur, ni dans les fichiers ni dans l'historique | — | ✅ Conforme |
| 3 | Tous les secrets lus via `os.getenv()`, sans repli en dur | — | ✅ Conforme |
| 4 | 3 adresses email réelles dans `afrotech.db`, fichier suivi par Git | 🔴 Critique | ⚠️ À traiter |
| 5 | Les crons GitHub Actions recommitent ces données à chaque exécution | 🔴 Critique | ⚠️ À traiter |
| 6 | `PRIVACY.md` contredit le comportement réel du code | 🟠 Important | ⚠️ À traiter |
| 7 | Aucun fichier `LICENSE` | 🟠 Important | ⚠️ À traiter |
| 8 | `TWITTER_BEARER_TOKEN` documenté mais lu par aucun code | 🟡 Mineur | À nettoyer |
| 9 | Dossiers non ignorés exposés au commit accidentel | 🟡 Mineur | À nettoyer |

**Conclusion : le dépôt ne doit pas être rendu public en l'état.** Les constats 4 et 5 publieraient
des données personnelles de façon irréversible.

---

## ✅ Ce qui est conforme

### 1. Gestion du fichier `.env`

`.env` figure en ligne 2 du `.gitignore` et n'a jamais été suivi. Vérifié :

```bash
git check-ignore -v .env          # → .gitignore:2:.env
git ls-files | grep -i env        # → .env.example uniquement
```

Seul `.env.example` est versionné, avec les six variables à valeurs vides — c'est exactement l'usage
attendu.

### 2. Aucun secret en dur

Recherche menée sur les fichiers suivis **et** sur les 89 commits de l'historique
(`git grep` sur `git rev-list --all`), portant sur les préfixes de clés Google (`AIza`), OpenAI
(`sk-`), Resend (`re_`), Telegram (`<id>:AA<token>`), GitHub (`ghp_`, `github_pat_`), Slack (`xox*`),
AWS (`AKIA`), ainsi que les blocs de clés privées PEM et les affectations littérales du type
`password=`, `token=`, `secret=`.

**Résultat : aucune occurrence.**

> Note méthodologique : un premier passage avait produit 23 résultats, tous faux positifs. Le motif
> Resend `re_[A-Za-z0-9_]{16,}` matchait des identifiants Python comme
> `derniere_newsletter_brouillon` (« de**rnière_newsletter**_brouillon »). Le motif a été ancré sur
> une frontière de mot avant re-scan. Toute reproduction de cet audit doit tenir compte de ce piège.

### 3. Lecture des secrets

Les six variables sensibles sont lues exclusivement via `os.getenv()`, sans valeur de repli en dur,
et lèvent une `RuntimeError` explicite lorsqu'elles manquent :

| Fichier | Variable |
|---|---|
| `pipeline/summarize.py:21` | `GEMINI_API_KEY` |
| `newsletter/writer.py:22` | `GEMINI_API_KEY` |
| `publisher/telegram_client.py:51` | `TELEGRAM_BOT_TOKEN` |
| `publisher/telegram_client.py:134` | `TELEGRAM_CHANNEL_ID` |
| `publisher/email_client.py:20` | `RESEND_API_KEY` |
| `publisher/email_client.py:33` | `RESEND_FROM_EMAIL` |

---

## 🔴 Constat 4 — Données personnelles dans la base versionnée

`afrotech.db` est volontairement suivi par Git (`.gitignore` : *« afrotech.db est volontairement
suivi par Git (persistance cron) »*). Ce choix est justifié techniquement — il permet aux workflows
GitHub Actions de conserver l'état entre deux exécutions — mais il publie aussi le contenu de la
base.

Or cette base contient des données personnelles réelles :

- **Table `abonnes_email`** : 3 adresses email personnelles (comptes Gmail nominatifs de membres de
  l'équipe), présentes dans le commit `HEAD`.
- **Table `newsletters_historique`** : 5 variantes de noms réels de validateurs, saisis dans le champ
  auteur de l'interface de validation.

Ces données sont présentes dans **13 commits** touchant `afrotech.db`. Passer le dépôt en public les
rend accessibles de façon permanente : supprimer le fichier aujourd'hui ne l'efface pas du passé, et
les forks ou clones déjà réalisés en conservent une copie.

**Impact** : publication non consentie de données personnelles, contraire au RGPD et à la politique
de confidentialité du projet lui-même (constat 6).

### Correction proposée

1. **Immédiat** — vider `abonnes_email` de la base versionnée. La table n'est utilisée que par le
   canal email, désactivé en production (`database.py:18`) : la purger ne casse rien.
2. **Structurel** — sortir la liste d'abonnés du fichier versionné. Une base séparée non suivie, ou
   un stockage chiffré hors dépôt, évite que le problème ne réapparaisse.
3. **Historique** — pour effacer les occurrences passées, `git filter-repo` est nécessaire.
   ⚠️ Opération destructive : elle réécrit tous les SHA, impose un push forcé et invalide les clones
   de toute l'équipe. À planifier explicitement, jamais dans une PR de documentation.
4. **Anonymiser** les auteurs de `newsletters_historique`, ou décider que les prénoms des
   contributeurs sont publiables — c'est une décision d'équipe, pas un problème technique.

---

## 🔴 Constat 5 — Les crons rejouent la fuite

Les deux workflows disposent de `permissions: contents: write` et recommitent `afrotech.db` après
chaque exécution via `stefanzweifel/git-auto-commit-action@v5` :

- `.github/workflows/daily_scrape.yml` — tous les jours à 6h UTC
- `.github/workflows/weekly_editor.yml` — tous les dimanches à 20h UTC

Conséquence : même après une purge de la base et une réécriture d'historique, **le premier cron
suivant recommitera la base courante**, avec les abonnés qu'elle contient à ce moment-là. La
correction du constat 4 est donc sans effet durable tant que ce point n'est pas traité.

### Correction proposée

Exclure les tables à données personnelles de ce qui est versionné — par exemple en exportant vers un
fichier dédié uniquement les tables publiables (`articles_raw`, `newsletters`), ou en purgeant
`abonnes_email` dans une étape du workflow avant le commit automatique.

---

## 🟠 Constat 6 — `PRIVACY.md` contredit le code

Le document affirme :

> « **Aucune donnée personnelle d'utilisateurs finaux** (abonnés WhatsApp Channel, followers
> LinkedIn) n'est collectée, stockée ou traitée par l'application. »

C'est faux sur deux points :

1. La table `abonnes_email` **stocke** des adresses email, et `publisher/email_client.py` les
   **traite** pour l'envoi (en copie cachée). La fonction `database.ajouter_abonne_email()` est
   précisément conçue pour cette collecte.
2. Les canaux décrits (WhatsApp Business, LinkedIn) ne sont pas ceux du code. La publication passe
   par **Telegram** (actif) et **Resend** (email, désactivé). WhatsApp n'apparaît nulle part dans le
   code, et le README documente déjà l'abandon de ce scope initial.

Une politique de confidentialité inexacte est plus risquée que pas de politique du tout : elle
engage le projet sur des affirmations vérifiablement fausses.

### Correction proposée

Réécrire `PRIVACY.md` sur la base du comportement réel : canaux Telegram et Resend, stockage
d'adresses email pour la diffusion, base de données versionnée, durée de conservation, et procédure
de désabonnement (`database.desabonner_email()` existe déjà).

---

## 🟠 Constat 7 — Aucune licence

Le dépôt ne contient aucun fichier `LICENSE`, `COPYING` ou équivalent. En droit d'auteur, l'absence
de licence explicite signifie **tous droits réservés** : publier le code sur GitHub le rend visible,
mais ne donne à personne le droit de le réutiliser, de le modifier ou de le redistribuer. Une
publication « open source » sans licence n'est pas open source.

### Correction proposée

Choisir une licence avant l'ouverture du dépôt et ajouter le fichier `LICENSE` à la racine. MIT et
Apache 2.0 sont les choix permissifs usuels ; AGPL-3.0 si l'équipe souhaite empêcher une
réappropriation fermée du service. Le README signale actuellement ce point en section Licence.

---

## 🟡 Constat 8 — Variable d'environnement inutilisée

`TWITTER_BEARER_TOKEN` figure dans `.env.example` mais aucun fichier Python ne la lit. Elle demande
donc à chaque nouvel arrivant d'obtenir une clé Twitter/X qui ne sert à rien.

Sans être une faille, une variable fantôme dans un modèle de configuration entretient la confusion
sur ce qui est réellement nécessaire. À retirer, ou à conserver avec la mention explicite qu'elle est
réservée à une évolution — c'est ce que fait désormais le tableau des variables du README.

---

## 🟡 Constat 9 — Dossiers exposés au commit accidentel

Deux dossiers présents dans l'arborescence de travail ne sont pas couverts par `.gitignore` :

- `archive/index_whoosh/` — index binaire du moteur de recherche, entièrement régénérable depuis la
  base par `indexer_editions()`. Le committer polluerait chaque diff de fichiers binaires. *(Ajouté
  au `.gitignore` dans le cadre de cet audit.)*
- `.claude/` — configuration locale d'outillage. À ignorer ou à versionner délibérément, selon ce que
  l'équipe décide d'en faire.

---

## Reproduire cet audit

```bash
# Le fichier .env est-il bien ignoré et non suivi ?
git check-ignore -v .env
git ls-files | grep -i env

# Recherche de secrets dans les fichiers suivis, puis dans tout l'historique
PAT='AIza[0-9A-Za-z_-]{30,}|(^|[^A-Za-z0-9_])sk-[A-Za-z0-9]{20,}|(^|[^A-Za-z0-9_])re_[A-Za-z0-9]{20,}|[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY'
git grep -I -n -E "$PAT" -- .
git grep -I -n -E "$PAT" $(git rev-list --all)

# Données personnelles dans la base versionnée
git show HEAD:afrotech.db > /tmp/head.db
python -c "import sqlite3; print(sqlite3.connect('/tmp/head.db').execute('SELECT email FROM abonnes_email').fetchall())"
```

---

## Avant de passer le dépôt en public

- [ ] Constat 4 — purger les données personnelles de la base versionnée
- [ ] Constat 5 — empêcher les crons de les recommiter
- [ ] Constat 4 — décider du sort de l'historique des 13 commits concernés
- [ ] Constat 6 — réécrire `PRIVACY.md` conformément au code
- [ ] Constat 7 — choisir une licence et ajouter le fichier `LICENSE`
- [ ] Constat 8 — trancher sur `TWITTER_BEARER_TOKEN`
- [ ] Constat 9 — statuer sur `.claude/`
- [ ] Rejouer cet audit après corrections

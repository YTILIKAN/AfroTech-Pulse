# S9 — Publication multi-canal

Documente ce qui est fait, ce qui est testé, et ce qui reste bloqué faute d'accès réels, pour
`publisher/publish.py`.

## Ce qui est implémenté

- `publier_whatsapp(contenu)` / `publier_linkedin(contenu)` : un appel HTTP par canal, avec le
  même pattern de retry/backoff que `pipeline/summarize.py` (3 tentatives, backoff exponentiel).
  Une erreur 4xx (hors 429) abandonne immédiatement, une erreur 429 ou 5xx est retentée, un
  timeout est retenté.
- `publish_newsletter(newsletter_id)` : publie sur les deux canaux, marque `statut = 'publié'`
  uniquement si les deux ont réussi. En cas d'échec partiel, le statut reste `'validé'` et les
  colonnes `whatsapp_publie` / `linkedin_publie` de `newsletters` retiennent précisément quel
  canal a réussi. Un nouvel appel ne republie jamais un canal déjà marqué réussi : seul(s) le(s)
  canal(aux) en échec est/sont retenté(s).
- Checklist de publication manuelle assistée (`publisher/publish.py` en CLI) : affiche l'id, le
  statut, un aperçu du contenu et l'état déjà publié ou non de chaque canal, puis demande une
  confirmation explicite (`oui`/`non`) avant d'appeler `publish_newsletter()`. `--oui` permet de
  sauter l'invite pour un usage scripté, à utiliser avec prudence.

## Limitation connue : pas d'environnement sandbox disponible

L'issue demande un test d'intégration en environnement sandbox/staging des deux API avant tout
envoi réel. Aucun compte de test WhatsApp Business API ni LinkedIn API n'est disponible dans ce
projet à ce jour (`WHATSAPP_TOKEN` et `LINKEDIN_TOKEN` sont vides dans `.env`). Cette étape n'a
donc pas pu être faite. Les tests couvrent la logique (retry, échecs partiels, non-régression)
avec des appels HTTP mockés, mais pas un vrai aller-retour contre les API réelles. À faire dès
que des comptes de test sont disponibles, avant toute publication réelle.

## Endpoints utilisés

`WHATSAPP_API_URL` et `LINKEDIN_API_URL` ont des valeurs par défaut indicatives
(`graph.facebook.com/v20.0/me/messages` et `api.linkedin.com/v2/ugcPosts`), surchargeables par
variable d'environnement. Ces valeurs n'ont pas été vérifiées contre un compte réel — à confirmer
contre la documentation Meta (WhatsApp Business Cloud API / WhatsApp Channels) et LinkedIn
(Marketing API / UGC Posts) au moment de configurer de vrais comptes, le format exact du payload
attendu (notamment l'identifiant de destinataire WhatsApp ou d'organisation LinkedIn) devra sans
doute être ajusté.

## État de la première édition réelle

Voir le suivi dans la PR : au moment d'écrire ce document, la seule newsletter au statut
`validé` en base contenait du contenu factice issu d'un test manuel de l'interface S8, pas une
vraie édition générée à partir d'articles réels. La préparation d'une vraie édition (sélection
S6 sur données réelles, génération S7 réelle, validation humaine S8) est traitée séparément.
La publication réelle elle-même n'aura lieu qu'après confirmation explicite, une fois de vrais
tokens WhatsApp/LinkedIn disponibles.

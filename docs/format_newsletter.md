# Format de la newsletter AfroTech Pulse

Ce document décrit le format généré par `newsletter/writer.py::generer_newsletter()`, à partir
d'une sélection d'articles déjà scorés et résumés (issue de l'agent éditeur S6).

## Entrée attendue

`generer_newsletter(articles)` prend une liste de dicts, un par article sélectionné. Chaque
dict doit fournir au minimum :

- `titre` (ou `title`)
- `url`
- `resume` (ou `contenu` / `content` en repli si pas encore résumé)

L'interface ne dépend pas de la façon dont S6 produit cette sélection : tant que la sélection
prend cette forme, elle peut être branchée directement.

## Structure de sortie

Markdown brut, avec exactement 3 sections dans cet ordre :

```
## Édito
<paragraphe d'intro, 3 à 5 phrases>

## Cette semaine
### 1. <titre article 1>
<résumé repris fidèlement, 2 à 3 phrases>
Lien : <url article 1>

### 2. <titre article 2>
...

## Conclusion
<paragraphe de clôture, 2 à 3 phrases>
```

- Un bloc `### <numéro>. <titre>` par article fourni, dans le même ordre, ni plus ni moins.
- Pas de tableaux, pas d'images, pas de HTML — le même Markdown doit rester lisible tel quel
  sur WhatsApp, LinkedIn et le site web. L'adaptation fine par canal (mise en forme spécifique,
  troncature, liens raccourcis) est du ressort de la publication (S9), pas de la génération.

## Ton et longueur

- Français, ton journalistique et informatif, jamais promotionnel ni sensationnaliste, sans
  emojis — même registre que `pipeline/summarize.py`.
- Édito : 3 à 5 phrases, pas de titre d'article cité, pas de liste.
- Par article : reprise fidèle du résumé fourni, 2 à 3 phrases, sans fait ajouté.
- Conclusion : 2 à 3 phrases, pas de nouvelle information factuelle.

## Garde-fous

- Interdiction stricte d'inventer un fait, chiffre, nom d'entreprise, de personne ou
  d'organisation absent du titre/résumé/contenu fourni pour l'article concerné.
- `structure_respectee(newsletter, nb_articles_attendu)` vérifie mécaniquement la présence des
  3 sections et que le nombre de blocs `###` correspond au nombre d'articles fournis. Elle ne
  vérifie pas l'absence de faits inventés — ce contrôle reste manuel (voir
  `docs/s7_validation_newsletter.md`).
- En cas d'échec structurel détecté, `generer_newsletter()` retourne quand même le texte généré
  (avec un avertissement en log) plutôt que de le rejeter silencieusement : la validation
  humaine (S8) reste la dernière étape avant publication.

## Persistance

Chaque génération est enregistrée via `database.sauvegarder_newsletter(contenu, nb_articles)`
dans la table `newsletters`, avec `statut = 'brouillon'` par défaut. Le passage à un autre
statut (validé, publié, rejeté) est du ressort de l'interface de validation humaine (S8).

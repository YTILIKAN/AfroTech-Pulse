# Script manuel — appelle la vraie API Mistral, à lancer à la main (`python verifier_summarize_manuellement.py`).
# Pas un test pytest : pas d'assertions automatiques, juste de quoi relire les résumés soi-même
# et juger la fidélité factuelle + la pertinence de l'angle africain trouvé.

from pipeline.summarize import summarize_article

CAS_DE_TEST = [
    {
        "label": "Article clairement africain",
        "titre": "Flutterwave leve 200 millions de dollars pour son expansion en Afrique de l Est",
        "contenu": (
            "La fintech nigeriane Flutterwave a annonce une levee de fonds de 200 millions de dollars "
            "afin d etendre ses services de paiement au Kenya, en Tanzanie et en Ouganda. L entreprise, "
            "deja presente dans 34 pays africains, affirme vouloir doubler le nombre de commercants "
            "utilisant sa plateforme d ici 2027."
        ),
    },
    {
        "label": "Article sans lien africain explicite (lancement produit US)",
        "titre": "OpenAI lance un nouveau modele de generation video a New York",
        "contenu": (
            "Lors d un evenement a New York, OpenAI a presente son dernier modele de generation video, "
            "capable de produire des clips de 60 secondes a partir d un simple texte. Le modele sera "
            "d abord disponible pour les abonnes payants americains, avant un deploiement international."
        ),
    },
    {
        "label": "Article institutionnel/politique (angle africain indirect)",
        "titre": "L Union europeenne annonce un nouveau fonds pour l intelligence artificielle",
        "contenu": (
            "La Commission europeenne a devoile un fonds de 2 milliards d euros destine a soutenir "
            "la recherche en intelligence artificielle sur le sol europeen. Ce fonds financera des "
            "startups et des laboratoires de recherche publics sur les cinq prochaines annees."
        ),
    },
    {
        "label": "Article ambigu, terme africain cite en passant",
        "titre": "Une conference mondiale sur le climat reunit 190 pays",
        "contenu": (
            "Des delegations de 190 pays se sont reunies cette semaine pour discuter des engagements "
            "climatiques. Des representants du Nigeria et de l Egypte ont plaide pour un financement "
            "accru des technologies vertes dans les pays en developpement."
        ),
    },
]

for cas in CAS_DE_TEST:
    print("=" * 70)
    print(cas["label"])
    print("=" * 70)
    resume = summarize_article(cas["titre"], cas["contenu"])
    print(resume if resume else "(aucun résumé — voir logs d'erreur ci-dessus)")
    print()

from scraper.main import load_sources, scrape_rss
from pipeline.filter import score_article
from pipeline.dedup import deduplicate
import database

SEUIL_PERTINENCE = database.SEUIL_PERTINENCE


def run():
    """Exécute la collecte quotidienne : scraping, déduplication, scoring, sauvegarde.

    Point d'entrée de `daily_scrape.yml`. Pour chaque source RSS active : récupère les
    articles, déduplique le lot de cette source, score la pertinence africaine, puis insère
    ceux qui ne sont pas déjà en base. Affiche un bilan chiffré à la fin.

    Ne consomme aucun crédit LLM : le résumé est une étape séparée
    (`pipeline.run_summarize`).
    """
    database.creer_base()

    sources = load_sources()
    print(f"AfroTech Pulse — Orchestrateur")
    print(f"{len(sources)} sources RSS actives\n")

    total_collectes = 0
    total_pertinents = 0
    total_hors_sujet = 0
    total_doublons_supprimes = 0

    for source in sources:
        print(f"[{source['category']}] {source['name']}...")
        articles = scrape_rss(source)

        # Dédup au sein du batch du jour uniquement (pas de comparaison
        # contre les articles déjà en base — limitation connue).
        articles_dedupliques = deduplicate(articles)
        total_doublons_supprimes += len(articles) - len(articles_dedupliques)

        nouveaux = 0
        for a in articles_dedupliques:
            score = score_article(a["title"], a["content"], a["source_id"])
            if score > SEUIL_PERTINENCE:
                total_pertinents += 1
            else:
                total_hors_sujet += 1

            if not database.article_existe(a["url"]):
                database.sauvegarder_article(
                    titre=a["title"],
                    url=a["url"],
                    source_id=a["source_id"],
                    date_pub=a["published"],
                    contenu=a["content"],
                    score_pertinence=score,
                )
                nouveaux += 1
        deja_en_base = len(articles_dedupliques) - nouveaux
        print(f"   {len(articles)} collectés — {nouveaux} nouveaux, {deja_en_base} déjà en base")
        total_collectes += len(articles)

    print(f"\n{'-' * 50}")
    print(f"Résumé : {total_collectes} articles collectés")
    print(f"         {total_doublons_supprimes} doublons supprimés (dédup intra-batch)")
    print(f"         {total_pertinents} pertinents (score > {SEUIL_PERTINENCE})")
    print(f"         {total_hors_sujet} hors-sujet")
    print(f"Base    : {database.DB_PATH}")


if __name__ == "__main__":
    run()

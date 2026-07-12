from scraper.main import load_sources, scrape_rss
from pipeline.filter import score_article
import database

SEUIL_PERTINENCE = 40


def run():
    database.creer_base()

    sources = load_sources()
    print(f"AfroTech Pulse — Orchestrateur")
    print(f"{len(sources)} sources RSS actives\n")

    total_collectes = 0
    total_pertinents = 0
    total_hors_sujet = 0

    for source in sources:
        print(f"[{source['category']}] {source['name']}...")
        articles = scrape_rss(source)

        nouveaux = 0
        for a in articles:
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
        doublons = len(articles) - nouveaux
        print(f"   {len(articles)} collectés — {nouveaux} nouveaux, {doublons} déjà en base")
        total_collectes += len(articles)

    print(f"\n{'-' * 50}")
    print(f"Résumé : {total_collectes} articles collectés")
    print(f"         {total_pertinents} pertinents (score > {SEUIL_PERTINENCE})")
    print(f"         {total_hors_sujet} hors-sujet")
    print(f"Base    : {database.DB_PATH}")


if __name__ == "__main__":
    run()

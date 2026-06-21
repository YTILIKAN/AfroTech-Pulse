from scraper.main import load_sources, scrape_rss
import database


def run():
    database.creer_base()

    sources = load_sources()
    print(f"AfroTech Pulse — Orchestrateur")
    print(f"{len(sources)} sources RSS actives\n")

    total_nouveaux = 0
    total_doublons = 0

    for source in sources:
        print(f"[{source['category']}] {source['name']}...")
        articles = scrape_rss(source)

        nouveaux = 0
        for a in articles:
            if not database.article_existe(a["url"]):
                database.sauvegarder_article(
                    titre=a["title"],
                    url=a["url"],
                    source_id=a["source_id"],
                    date_pub=a["published"],
                    contenu=a["content"],
                )
                nouveaux += 1
        doublons = len(articles) - nouveaux
        print(f"   {len(articles)} collectés — {nouveaux} nouveaux, {doublons} déjà en base")
        total_nouveaux += nouveaux
        total_doublons += doublons

    print(f"\n{'-' * 50}")
    print(f"Résumé : {total_nouveaux} nouveaux articles sauvegardés")
    print(f"         {total_doublons} doublons ignorés")
    print(f"Base    : {database.DB_PATH}")


if __name__ == "__main__":
    run()

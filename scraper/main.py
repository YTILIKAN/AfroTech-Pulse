import json
import time
import feedparser
import requests
from datetime import datetime
from pathlib import Path


SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"
REQUEST_TIMEOUT = 10

# lit toutes les sources et garde uniquement celle de type choisir
def load_sources():
    """Retourne les sources RSS actives de data/sources.json.

    Seules les entrées `type == "rss"`, `active` et pourvues d'une url sont retenues — les
    sources de type web, api et pdf sont cataloguées pour une évolution future mais ne sont
    pas encore collectées.
    """
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    rss_sources = [
        s for s in data["sources"]
        if s["type"] == "rss" and s["active"] and s["url"]
    ]
    return rss_sources

# Coeur du scraper qui viste l'url,gere les erreurs et extraires chaque article
def scrape_rss(source):
    """Récupère et parse le flux d'une source, et retourne ses articles.

    Chaque article est un dict `{source_id, source_name, category, title, url, published,
    content}`. `published` est normalisé en ISO 8601 quand feedparser a su lire la date.

    Ne lève jamais : timeout, erreur réseau, erreur HTTP ou flux illisible sont journalisés
    et retournent une liste vide, pour qu'une source en panne n'interrompe pas la collecte
    des autres.
    """
    name = source["name"]
    url = source["url"]

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        })
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {name} — site trop lent, on passe.")
        return []
    except requests.exceptions.ConnectionError:
        print(f"  [ERREUR RÉSEAU] {name} — site inaccessible, on passe.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  [ERREUR HTTP {e.response.status_code}] {name} — on passe.")
        return []
    except Exception as e:
        print(f"  [ERREUR INCONNUE] {name} — {e}")
        return []

    if not feed.entries:
        print(f"  [VIDE] {name} — flux RSS vide ou non reconnu.")
        return []

    articles = []
    for entry in feed.entries:
        title = entry.get("title", "Sans titre").strip()
        link = entry.get("link", "")
        content = entry.get("summary", entry.get("description", "")).strip()

        published = entry.get("published", entry.get("updated", ""))
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                published = published

        articles.append({
            "source_id": source["id"],
            "source_name": name,
            "category": source["category"],
            "title": title,
            "url": link,
            "published": published,
            "content": content,
        })

    return articles

# Boucle principale sur toutes les sources Rss
def main():
    """Collecte toutes les sources RSS actives et retourne les articles trouvés.

    Point d'entrée autonome, utile pour tester la collecte seule. Le pipeline de production
    passe par `orchestrator.run()`, qui enchaîne collecte, déduplication, scoring et
    sauvegarde.
    """
    sources = load_sources()
    print(f"AfroTech Pulse — Scraping de {len(sources)} sources RSS\n")

    all_articles = []

    for source in sources:
        print(f"Scraping {source['name']}...")
        articles = scrape_rss(source)
        print(f"  → {len(articles)} articles trouvés")
        all_articles.extend(articles)
        time.sleep(1)

    print(f"\nTotal : {len(all_articles)} articles collectés depuis {len(sources)} sources.")
    return all_articles


if __name__ == "__main__":
    main()

# pipeline/run_summarize.py — résume en batch les articles pertinents pas encore résumés

import argparse

import database
from pipeline.summarize import summarize_article

SEUIL_PERTINENCE = database.SEUIL_PERTINENCE


def run(limit=None):
    database.creer_base()

    articles = database.articles_a_resumer(seuil=SEUIL_PERTINENCE, limit=limit)
    print(f"AfroTech Pulse — Résumé batch")
    print(f"{len(articles)} article(s) à résumer (score > {SEUIL_PERTINENCE}, pas encore résumé)\n")

    resumes = 0
    echecs = 0

    for url, titre, contenu in articles:
        print(f"[{titre}]")
        resume = summarize_article(titre, contenu)
        if resume is not None:
            database.sauvegarder_resume(url, resume)
            resumes += 1
        else:
            echecs += 1

    print(f"\n{'-' * 50}")
    print(f"Résumé : {resumes} article(s) résumé(s), {echecs} échec(s)")
    print(f"Base   : {database.DB_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Résume en batch les articles pertinents pas encore résumés.")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum d'articles à résumer.")
    args = parser.parse_args()
    run(limit=args.limit)


if __name__ == "__main__":
    main()

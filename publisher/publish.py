# publisher/publish.py — Publication WhatsApp Business API + LinkedIn API + site web

import argparse
import os
import time

import httpx
from dotenv import load_dotenv

import database

load_dotenv()

MAX_TENTATIVES = 3

# Endpoints indicatifs, à confirmer/ajuster contre la documentation Meta/LinkedIn
# une fois de vrais comptes de test disponibles (voir docs/publication_s9.md).
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0/me/messages")
LINKEDIN_API_URL = os.getenv("LINKEDIN_API_URL", "https://api.linkedin.com/v2/ugcPosts")

_http_client = None


def _get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=10.0)
    return _http_client


def _post_avec_retry(url, headers, payload, nom_canal):
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = _get_http_client().post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            print(f"  [{nom_canal}] [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")
        else:
            if response.status_code < 300:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [{nom_canal}] [ERREUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(f"  [{nom_canal}] [ERREUR {response.status_code}] publication impossible, on abandonne.")
                return False

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  [{nom_canal}] Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [{nom_canal}] [ÉCHEC] publication abandonnée après {MAX_TENTATIVES} tentatives.")
    return False


def publier_whatsapp(contenu: str) -> bool:
    cle = os.getenv("WHATSAPP_TOKEN")
    if not cle:
        raise RuntimeError(
            "WHATSAPP_TOKEN manquante — copie .env.example en .env et renseigne ta clé."
        )
    headers = {"Authorization": f"Bearer {cle}"}
    payload = {"messaging_product": "whatsapp", "type": "text", "text": {"body": contenu}}
    return _post_avec_retry(WHATSAPP_API_URL, headers, payload, "WhatsApp")


def publier_linkedin(contenu: str) -> bool:
    cle = os.getenv("LINKEDIN_TOKEN")
    if not cle:
        raise RuntimeError(
            "LINKEDIN_TOKEN manquante — copie .env.example en .env et renseigne ta clé."
        )
    headers = {"Authorization": f"Bearer {cle}", "X-Restli-Protocol-Version": "2.0.0"}
    payload = {"commentary": contenu}
    return _post_avec_retry(LINKEDIN_API_URL, headers, payload, "LinkedIn")


def publish_newsletter(newsletter_id: int) -> dict:
    """Publie une newsletter validée sur WhatsApp et LinkedIn.

    Un canal déjà marqué comme publié (whatsapp_publie/linkedin_publie) n'est jamais
    republié : un appel répété après un échec partiel ne retente que le(s) canal(aux)
    resté(s) en échec. Le statut n'est marqué 'publié' que lorsque les deux canaux ont
    réussi, jamais en cas d'échec, même partiel.
    """
    newsletter = database.obtenir_newsletter(newsletter_id)
    if newsletter is None:
        raise ValueError(f"Newsletter introuvable : id={newsletter_id}")

    _, contenu, _, statut, _, whatsapp_deja_publie, linkedin_deja_publie = newsletter

    if statut != "validé":
        raise ValueError(
            f"Seule une newsletter au statut 'validé' peut être publiée (statut actuel : {statut!r})"
        )

    whatsapp_ok = bool(whatsapp_deja_publie) or publier_whatsapp(contenu)
    if whatsapp_ok and not whatsapp_deja_publie:
        database.marquer_canal_publie(newsletter_id, "whatsapp")

    linkedin_ok = bool(linkedin_deja_publie) or publier_linkedin(contenu)
    if linkedin_ok and not linkedin_deja_publie:
        database.marquer_canal_publie(newsletter_id, "linkedin")

    if whatsapp_ok and linkedin_ok:
        database.changer_statut_newsletter(newsletter_id, "publié", "publisher")
        print(f"Newsletter #{newsletter_id} publiée avec succès sur WhatsApp et LinkedIn.")
    else:
        canaux_en_echec = [
            nom for nom, ok in [("WhatsApp", whatsapp_ok), ("LinkedIn", linkedin_ok)] if not ok
        ]
        print(
            f"[ALERTE] Échec partiel pour la newsletter #{newsletter_id} : "
            f"{', '.join(canaux_en_echec)} en échec. Statut inchangé ('validé'). "
            f"Un nouvel appel à publish_newsletter({newsletter_id}) ne retentera que "
            f"{'ce canal' if len(canaux_en_echec) == 1 else 'ces canaux'}."
        )

    return {"whatsapp": whatsapp_ok, "linkedin": linkedin_ok}


def _apercu(contenu: str, longueur=400) -> str:
    if len(contenu) <= longueur:
        return contenu
    return contenu[:longueur] + "…"


def _afficher_checklist_pre_publication(newsletter):
    newsletter_id, contenu, nb_articles, statut, date_generation, whatsapp_publie, linkedin_publie = newsletter
    print("=" * 60)
    print("Checklist de publication — AfroTech Pulse")
    print("=" * 60)
    print(f"Newsletter   : #{newsletter_id}")
    print(f"Statut       : {statut}")
    print(f"Articles     : {nb_articles}")
    print(f"Générée le   : {date_generation}")
    print(f"WhatsApp     : {'déjà publié' if whatsapp_publie else 'pas encore publié'}")
    print(f"LinkedIn     : {'déjà publié' if linkedin_publie else 'pas encore publié'}")
    print("-" * 60)
    print(_apercu(contenu))
    print("-" * 60)
    print("Vérifie que c'est bien cette édition, et sur ces 2 canaux, que tu veux publier MAINTENANT.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Publie une newsletter validée sur WhatsApp et LinkedIn (checklist manuelle assistée)."
    )
    parser.add_argument("newsletter_id", type=int, help="id de la newsletter à publier")
    parser.add_argument(
        "--oui", action="store_true",
        help="Confirme la publication sans invite interactive (usage automatisé uniquement).",
    )
    args = parser.parse_args()

    database.creer_base()
    newsletter = database.obtenir_newsletter(args.newsletter_id)
    if newsletter is None:
        print(f"Newsletter introuvable : id={args.newsletter_id}")
        return

    _afficher_checklist_pre_publication(newsletter)

    if not args.oui:
        reponse = input("Confirmer la publication ? (oui/non) : ").strip().lower()
        if reponse != "oui":
            print("Publication annulée.")
            return

    resultat = publish_newsletter(args.newsletter_id)
    print()
    print(f"Résultat : WhatsApp={'OK' if resultat['whatsapp'] else 'KO'}, "
          f"LinkedIn={'OK' if resultat['linkedin'] else 'KO'}")
    print("Vérifie manuellement sur les 2 canaux que la publication est bien visible avant de clore l'édition.")


if __name__ == "__main__":
    main()

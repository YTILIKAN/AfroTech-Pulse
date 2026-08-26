# publisher/publish.py — Orchestration de la publication multicanal (Telegram + Email)

import database
from publisher.telegram_client import envoyer_telegram

# "email" sera ajouté une fois le client Resend écrit
ENVOI_PAR_CANAL = {
    "telegram": envoyer_telegram,
}


def _tentatives_precedentes(newsletter_id, canal):
    for c, _statut, tentatives, _erreur, _horodatage in database.statuts_publication(newsletter_id):
        if c == canal:
            return tentatives
    return 0


def _publier_canal(newsletter_id, canal, contenu):
    envoyer = ENVOI_PAR_CANAL[canal]
    erreur = None
    try:
        succes = envoyer(contenu)
    except RuntimeError as e:
        print(f"  [CONFIG MANQUANTE - {canal}] {e}")
        succes = False
        erreur = str(e)

    tentatives = _tentatives_precedentes(newsletter_id, canal) + 1
    statut = "publié" if succes else "echec"
    if not succes and erreur is None:
        erreur = f"Échec de l'envoi sur {canal} après {tentatives} tentative(s) au total."

    database.enregistrer_publication_canal(newsletter_id, canal, statut, tentatives, erreur)
    return succes


def _finaliser_si_complet(newsletter_id, auteur):
    if database.tous_canaux_publies(newsletter_id):
        database.changer_statut_newsletter(newsletter_id, "publié", auteur)
        print(f"[OK] Newsletter #{newsletter_id} marquée 'publié' — tous les canaux ont réussi.")
    else:
        canaux_restants = [
            canal for canal, statut, *_ in database.statuts_publication(newsletter_id)
            if statut != "publié"
        ]
        print(
            f"[ALERTE] Newsletter #{newsletter_id} publiée partiellement. "
            f"Canaux à republier : {canaux_restants}"
        )


def publish_newsletter(auteur="orchestrateur"):
    newsletter = database.derniere_newsletter_validee()
    if newsletter is None:
        print("[INFO] Aucune newsletter validée en attente de publication.")
        return {}

    newsletter_id, contenu, _nb_articles, _statut, _date_generation = newsletter

    resultats = {}
    for canal in database.CANAUX_PUBLICATION:
        resultats[canal] = _publier_canal(newsletter_id, canal, contenu)

    _finaliser_si_complet(newsletter_id, auteur)
    return resultats


def republier_canal(newsletter_id, canal, auteur="orchestrateur"):
    if canal not in ENVOI_PAR_CANAL:
        raise ValueError(f"Canal inconnu : {canal!r}")

    newsletter = database.newsletter_par_id(newsletter_id)
    if newsletter is None:
        raise ValueError(f"Newsletter introuvable : id={newsletter_id}")

    contenu = newsletter[1]
    succes = _publier_canal(newsletter_id, canal, contenu)
    _finaliser_si_complet(newsletter_id, auteur)
    return succes


if __name__ == "__main__":
    database.creer_base()
    publish_newsletter()

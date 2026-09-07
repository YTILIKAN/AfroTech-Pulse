# publisher/publish.py — Orchestration de la publication multicanal (Telegram + Email)

import database
from publisher.email_client import envoyer_email
from publisher.telegram_client import envoyer_telegram

ENVOI_PAR_CANAL = {
    "telegram": envoyer_telegram,
    "email": envoyer_email,
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
    except Exception as e:
        # Filet de sécurité large et volontaire : une erreur réseau (DNS, connexion coupée)
        # ou tout autre imprévu venant d'un client ne doit jamais faire planter
        # publish_newsletter() avant d'avoir tenté les autres canaux, ni faire planter
        # review_ui.py qui appelle ça directement depuis un bouton sans try/except.
        print(f"  [ERREUR INATTENDUE - {canal}] {e}")
        succes = False
        erreur = str(e)

    tentatives = _tentatives_precedentes(newsletter_id, canal) + 1
    statut = "publié" if succes else "echec"
    if not succes and erreur is None:
        erreur = f"Échec de l'envoi sur {canal} après {tentatives} tentative(s) au total."

    database.enregistrer_publication_canal(newsletter_id, canal, statut, tentatives, erreur)
    return succes


def _reindexer_archive(newsletter_id):
    # Import local : évite un cycle publish → search → database et garde publish.py importable
    # même sans Whoosh installé.
    from archive.search import indexer_editions

    try:
        indexer_editions()
        print(f"[OK] Archive réindexée — newsletter #{newsletter_id} est cherchable.")
    except Exception as e:
        # Même logique que _publier_canal() : l'envoi vers les abonnés a réussi, une archive
        # qui n'indexe pas ne doit pas remonter une exception dans le bouton "Publier"
        # de review_ui.py ni faire échouer l'orchestrateur.
        print(f"[ALERTE] Newsletter #{newsletter_id} publiée mais non indexée dans l'archive : {e}")


def _finaliser_si_complet(newsletter_id, auteur):
    if database.tous_canaux_publies(newsletter_id, canaux=database.CANAUX_PUBLICATION):
        database.changer_statut_newsletter(newsletter_id, "publié", auteur)
        print(f"[OK] Newsletter #{newsletter_id} marquée 'publié' — tous les canaux ont réussi.")
        _reindexer_archive(newsletter_id)
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
    if canal not in database.CANAUX_PUBLICATION:
        raise ValueError(f"Canal inconnu ou désactivé : {canal!r}")

    newsletter = database.newsletter_par_id(newsletter_id)
    if newsletter is None:
        raise ValueError(f"Newsletter introuvable : id={newsletter_id}")
    if newsletter[3] != "validé":
        raise ValueError(
            f"Impossible de republier : la newsletter #{newsletter_id} a le statut "
            f"{newsletter[3]!r}, seul le statut 'validé' est autorisé."
        )

    contenu = newsletter[1]
    succes = _publier_canal(newsletter_id, canal, contenu)
    _finaliser_si_complet(newsletter_id, auteur)
    return succes


if __name__ == "__main__":
    database.creer_base()
    publish_newsletter()

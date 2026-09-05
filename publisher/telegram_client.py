# publisher/telegram_client.py — Client Telegram Bot API, publication sur le canal Y'TILIKAN

import os
import re
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

MAX_TENTATIVES = 3
LIMITE_CARACTERES_TELEGRAM = 4096

_MOTIF_LIEN = re.compile(r"^Lien\s*:\s*(\S+)\s*$")


def _echapper_html(texte):
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _mettre_en_forme_telegram(contenu):
    """Convertit le Markdown de la newsletter (## Titre, ### N. Titre, Lien : url) en
    HTML supporté par Telegram (parse_mode="HTML") : titres en gras, liens cliquables.

    HTML est utilisé plutôt que le mode Markdown natif de Telegram, qui échoue dès qu'un
    underscore/astérisque n'est pas correctement "fermé" — bien plus fréquent dans du texte
    normal (URLs, noms propres) que les 3 caractères (&, <, >) à échapper en HTML.
    """
    lignes = []
    for ligne in contenu.split("\n"):
        if ligne.startswith("### "):
            lignes.append(f"<b>{_echapper_html(ligne[4:])}</b>")
        elif ligne.startswith("## "):
            # .upper() AVANT l'échappement : sinon "&" -> "&amp;" -> "&AMP;" (majuscule)
            # n'est plus une entité HTML valide et Telegram rejette le message.
            lignes.append(f"<b>{_echapper_html(ligne[3:].upper())}</b>")
        else:
            correspondance = _MOTIF_LIEN.match(ligne.strip())
            if correspondance:
                url = _echapper_html(correspondance.group(1))
                lignes.append(f'🔗 <a href="{url}">Lire l\'article complet</a>')
            else:
                lignes.append(_echapper_html(ligne))
    return "\n".join(lignes)


def get_client():
    # Pas de mise en cache : évite qu'un token périmé reste utilisé après un changement
    # de .env sans redémarrage du process (même raisonnement que email_client.get_client()).
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN manquant — copie .env.example en .env et renseigne ton token."
        )
    return httpx.Client(
        base_url=f"https://api.telegram.org/bot{token}",
        timeout=10.0,
    )


def _coupure_valide(texte, position):
    prefixe = texte[:position]
    # (1) Pas au milieu d'une balise elle-même (ex. entre "<" et "a href=...>") : le nombre
    #     de "<" et de ">" doit être égal, sinon une balise est littéralement tronquée.
    if prefixe.count("<") != prefixe.count(">"):
        return False
    # (2) Pas d'ancre/gras ouvert sans sa fermeture (une fois (1) garanti, "<a"/"</a>" et
    #     "<b>"/"</b>" ne peuvent plus être des fragments de balise, juste des paires réelles).
    return prefixe.count("<a") == prefixe.count("</a>") and prefixe.count("<b>") == prefixe.count("</b>")


def _trouver_coupure_sure(texte, limite):
    # On cherche le point de coupure le plus "propre" possible, en vérifiant à chaque fois
    # que les balises HTML (<a href="...">...</a>, <b>...</b>) restent équilibrées et jamais
    # tronquées avant ce point — Telegram rejette un message HTML mal formé.
    for candidat in (texte.rfind("\n\n", 0, limite), texte.rfind("\n", 0, limite)):
        if candidat != -1 and _coupure_valide(texte, candidat):
            return candidat

    # Dernier recours : reculer caractère par caractère depuis la limite jusqu'à un point
    # valide. Cas extrême (une seule "ligne" dépassant la limite à elle seule) qui ne
    # devrait pas arriver avec le contenu réel d'une newsletter (toujours multi-lignes).
    position = limite
    while position > 0 and not _coupure_valide(texte, position):
        position -= 1
    return position if position > 0 else limite


def _decouper_message(contenu, limite=LIMITE_CARACTERES_TELEGRAM):
    if len(contenu) <= limite:
        return [contenu]

    morceaux = []
    reste = contenu
    while len(reste) > limite:
        coupure = _trouver_coupure_sure(reste, limite)
        morceaux.append(reste[:coupure].strip())
        reste = reste[coupure:].strip()
    if reste:
        morceaux.append(reste)
    return morceaux


def _envoyer_message(channel_id, texte_html):
    payload = {"chat_id": channel_id, "text": texte_html, "parse_mode": "HTML"}

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = get_client().post("/sendMessage", json=payload)
            if response.status_code == 200:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                print(f"  [RATE LIMIT/SERVEUR {response.status_code}] tentative {tentative}/{MAX_TENTATIVES}...")
            else:
                print(
                    f"  [ERREUR API {response.status_code}] envoi Telegram impossible, "
                    f"on abandonne. {response.text}"
                )
                return False
        except httpx.TimeoutException:
            print(f"  [TIMEOUT] tentative {tentative}/{MAX_TENTATIVES}...")

        if tentative < MAX_TENTATIVES:
            delai = 2 ** tentative
            print(f"  Nouvelle tentative dans {delai}s...")
            time.sleep(delai)

    print(f"  [ÉCHEC] envoi Telegram abandonné après {MAX_TENTATIVES} tentatives.")
    return False


def envoyer_telegram(contenu: str) -> bool:
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    if not channel_id:
        raise RuntimeError(
            "TELEGRAM_CHANNEL_ID manquant — copie .env.example en .env et renseigne "
            "l'identifiant du canal Telegram (ex. @ytilikan)."
        )

    contenu_html = _mettre_en_forme_telegram(contenu)
    for morceau in _decouper_message(contenu_html):
        if not _envoyer_message(channel_id, morceau):
            return False
    return True

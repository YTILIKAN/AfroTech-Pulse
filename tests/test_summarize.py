from types import SimpleNamespace

import pipeline.summarize as summarize_module
from pipeline.summarize import summarize_article

CONTENU_VALIDE = "Contenu suffisamment long pour passer le garde-fou de longueur minimale du script."


def fake_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_appel_reussi_retourne_le_resume_nettoye(monkeypatch):
    monkeypatch.setattr(
        summarize_module.client.chat, "complete",
        lambda **kw: fake_response("  Ligne 1.\nLigne 2.\nLigne 3.  "),
    )
    resultat = summarize_article("titre", CONTENU_VALIDE)
    assert resultat == "Ligne 1.\nLigne 2.\nLigne 3."


def test_contenu_vide_retourne_none(monkeypatch):
    assert summarize_article("titre", "") is None


def test_contenu_trop_court_retourne_none(monkeypatch):
    assert summarize_article("titre", "trop court") is None

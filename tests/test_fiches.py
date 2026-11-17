from pathlib import Path

import pytest

from app.fiches import Bibliotheque, FicheError, analyser, slug

FICHES = Path(__file__).resolve().parent.parent / "fiches"

MINIMALE = """---
nom: Test
brochage:
  rangees:
    - cote: haut
      broches:
        - { nom: ON, type: gpio }
        - { nom: NO, type: inconnu }
---
Corps **gras**.
"""


def test_fiches_exemples_valides():
    fiches, erreurs = Bibliotheque(FICHES).lister()
    assert erreurs == []
    assert len(fiches) >= 5
    for f in fiches:
        assert f.avertissements == [], (f.id, f.avertissements)


def test_modele_vierge_valide():
    fiche = analyser("modele", (FICHES / "_modele.md").read_text(encoding="utf-8"))
    assert fiche.avertissements == []


def test_noms_yaml_non_booleens_et_type_inconnu():
    f = analyser("test", MINIMALE)
    broches = f.meta["brochage"]["rangees"][0]["broches"]
    assert [b["nom"] for b in broches] == ["ON", "NO"]
    assert broches[1]["type"] == "autre"
    assert any("inconnu" in a for a in f.avertissements)
    assert "<strong>gras</strong>" in f.complete()["html"]


@pytest.mark.parametrize("source", ["pas d'en-tête", "---\nnom: [\n---\n", "---\ndescription: x\n---\n"])
def test_fiches_invalides(source):
    with pytest.raises(FicheError):
        analyser("x", source)


def test_ecriture_lecture_suppression(tmp_path):
    b = Bibliotheque(tmp_path)
    b.ecrire("essai", MINIMALE)
    assert b.lire("essai").meta["nom"] == "Test"
    with pytest.raises(FicheError):
        b.ecrire("essai", "invalide")
    assert b.source("essai") == MINIMALE
    b.supprimer("essai")
    assert not b.existe("essai")


def test_identifiants_et_modeles(tmp_path):
    b = Bibliotheque(tmp_path)
    with pytest.raises(FicheError):
        b.chemin("../etc")
    with pytest.raises(FileNotFoundError):
        b.chemin_modele("../../secret.glb")
    assert b.ecrire_modele("Mon Modèle.STL", b"solid") == "modeles/mon-modele.stl"
    assert slug("Module BME280 (I²C)") == "module-bme280-i2c"

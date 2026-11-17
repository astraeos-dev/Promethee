# Modèles 3D des appareils

`<identifiant>.glb` est le modèle complet de l'appareil décrit par `sheets/<identifiant>.md`,
construit par `tools/build_models.py` : ne pas le modifier à la main, mais modifier la fiche puis
relancer l'outil. `index.json` garde l'empreinte de ce qui a servi à construire chaque modèle (les
tests signalent un modèle à reconstruire) et `parts.json` les dimensions des pièces, pour le schéma 2D.

Les composants viennent de la [bibliothèque 3D de KiCad](https://gitlab.com/kicad/libraries/kicad-packages3D)
(révision indiquée dans `tools/parts.yaml`) : les modèles qui les contiennent restent donc sous
licence **CC-BY-SA 4.0**, avec l'exception KiCad : voir [LICENSE.md](LICENSE.md).

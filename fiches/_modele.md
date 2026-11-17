---
# Modèle de fiche Prométhée. Copier ce fichier sous le nom <identifiant>.md
# (minuscules, chiffres et tirets), puis le compléter. Format : docs/format-fiche.md
nom: Nouvel appareil
categorie: Divers
fabricant: ""
reference: ""
description: Une phrase qui dit à quoi sert l'appareil.
tags: []

caracteristiques:
  Tension d'alimentation: 3,3 V
  Courant typique: ""

liens:
  - titre: Fiche technique (datasheet)
    url: https://exemple.org/datasheet.pdf

# Vue 3D générée à partir du boîtier et du brochage.
# type : carte | module | dip | to92. Dimensions en millimètres, vue de dessus :
# la largeur est horizontale, la longueur verticale.
boitier:
  type: carte
  longueur: 40
  largeur: 20
  epaisseur: 1.6
  couleur: "#1d5c3a"

# Pour remplacer la vue générée par un vrai modèle (.glb, .gltf ou .stl),
# déposer le fichier dans fiches/modeles/ et indiquer son nom ici.
# modele3d: modeles/mon-appareil.glb

brochage:
  pas: 2.54
  rangees:
    - nom: J1
      cote: gauche          # gauche | droite | haut | bas
      broches:              # de haut en bas (de gauche à droite pour haut et bas)
        - { n: 1, nom: VCC, type: alim, desc: "Alimentation 3,3 V" }
        - { n: 2, nom: GND, type: masse }
        - { n: 3, nom: SDA, type: i2c, fonctions: [GPIO4] }
        - { n: 4, nom: SCL, type: i2c, fonctions: [GPIO5] }
# Types de broche : alim, masse, gpio, analogique, pwm, i2c, spi, uart,
# controle, reserve, nc, autre.

# Composants visibles sur la carte (facultatif). x et y : centre, depuis le coin haut gauche.
composants:
  - { nom: Puce, x: 12, y: 15, largeur: 6, longueur: 6, hauteur: 1, texte: "IC" }
---

## Présentation

Ce que fait l'appareil, dans quel cas l'utiliser.

## Câblage

| Appareil | Microcontrôleur |
|----------|-----------------|
| VCC      | 3V3             |
| GND      | GND             |

## Utilisation

```cpp
// Exemple de code
```

## Précautions

- Ne pas dépasser 3,6 V sur les broches.

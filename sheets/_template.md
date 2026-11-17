---
# Modèle de fiche Prométhée. Copier ce fichier sous le nom <identifiant>.md
# (minuscules, chiffres et tirets), puis le compléter. Format : docs/sheet-format.md
name: Nouvel appareil
category: Divers
manufacturer: ""
part_number: ""
description: Une phrase qui dit à quoi sert l'appareil.
tags: []

# Clés libres, affichées telles quelles dans l'onglet « Caractéristiques ».
specs:
  Tension d'alimentation: 3,3 V
  Courant typique: ""

links:
  - title: Fiche technique (datasheet)
    url: https://exemple.org/datasheet.pdf

# Vue 3D générée à partir du boîtier et du brochage.
# type : board | module | dip | to92. Dimensions en millimètres, vue de dessus :
# width est horizontale, length verticale.
package:
  type: board
  length: 40
  width: 20
  thickness: 1.6
  color: "#1d5c3a"

# Pour remplacer la vue générée par un vrai modèle (.glb, .gltf ou .stl),
# déposer le fichier dans sheets/models/ et indiquer son nom ici.
# model3d: models/mon-appareil.glb

pinout:
  pitch: 2.54
  rows:
    - name: J1
      side: left            # left | right | top | bottom
      pins:                 # de haut en bas (de gauche à droite pour top et bottom)
        - { n: 1, name: VCC, type: power, description: "Alimentation 3,3 V" }
        - { n: 2, name: GND, type: ground }
        - { n: 3, name: SDA, type: i2c, functions: [GPIO4] }
        - { n: 4, name: SCL, type: i2c, functions: [GPIO5] }
# Types de broche : power, ground, gpio, analog, pwm, i2c, spi, uart,
# control, reserved, nc, other.

# Composants visibles sur la carte (facultatif). x et y : centre, depuis le coin haut gauche.
components:
  - { name: Puce, x: 12, y: 15, width: 6, length: 6, height: 1, label: "IC" }
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

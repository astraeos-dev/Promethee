---
# Modèle de fiche Prométhée, pour préparer une fiche livrée avec l'application.
# Copier sous le nom <identifiant>.md (minuscules, chiffres et tirets). Format : docs/sheet-format.md
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

# Boîtier : circuit imprimé ou corps du composant.
# type : board | module | dip | to92. Dimensions en millimètres, vue de dessus :
# width est horizontale, length verticale.
package:
  type: board
  length: 40
  width: 20
  thickness: 1.6
  color: "#1d5c3a"

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

# Vrais modèles 3D (sheets/models, voir tools/models.yaml). x et y : centre, depuis le coin haut gauche.
parts:
  - { name: Barrette, model: models/pin-header-1x04.glb, x: 1.27, y: 20, side: bottom }
  - { name: Puce, model: models/sot-23-5.glb, x: 12, y: 15, label: "IC" }
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

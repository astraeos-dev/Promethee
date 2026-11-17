# Format d'une fiche

Ce document sert à préparer les fiches livrées avec Prométhée. Pour en obtenir une nouvelle,
il suffit d'[ouvrir une demande](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml) :
la fiche est ajoutée dans une mise à jour.

Chaque appareil a son fichier dans le dossier `sheets/` du dépôt : `sheets/<identifiant>.md`.
L'identifiant est le nom du fichier, en minuscules, chiffres et tirets (`esp32-devkitc-v4`).
Les fichiers qui commencent par `_` (comme `_template.md`) ne sont pas listés.

Une fiche a deux parties :

1. un **en-tête YAML** entre deux lignes `---` : identité, caractéristiques, boîtier, brochage.
   Les **clés sont en anglais**, les valeurs dans la langue de votre choix ;
2. un **texte en Markdown** : présentation, câblage, code d'exemple, précautions.
   Il s'affiche dans l'onglet « Utilisation ».

Partir de `sheets/_template.md`. Pour voir le résultat, lancer Prométhée en développement
(`uvicorn app.main:app --reload`) : un fichier modifié est relu au prochain affichage. Les tests
(`pytest`) vérifient que chaque fiche se lit sans avertissement.

## Identité

| Clé            | Obligatoire | Exemple                                        |
|----------------|-------------|------------------------------------------------|
| `name`         | oui         | `ESP32-DevKitC V4`                             |
| `category`     | non         | `Carte de développement` (défaut : Divers)     |
| `manufacturer` | non         | `Espressif`                                    |
| `part_number`  | non         | `ESP32-DevKitC-32E`                            |
| `description`  | non         | une phrase, affichée sur la carte de la fiche  |
| `tags`         | non         | `[wifi, bluetooth]`                            |
| `specs`        | non         | liste `Libellé: valeur`, affichée en tableau ; les libellés sont libres |
| `links`        | non         | liste de `{ title, url }` (datasheets, guides) |

## Boîtier et vue 3D

La vue 3D part du boîtier (`package`) : circuit imprimé avec ses pastilles et la sérigraphie des
broches pour une carte, ou repères des pattes pour un DIP ou un TO-92. Les **vrais modèles 3D** des
pièces (`parts`, voir plus bas) s'y ajoutent ; sans eux, une représentation simplifiée est dessinée.
Toutes les dimensions sont en millimètres, **vue de dessus** : `width` est horizontale,
`length` verticale.

```yaml
package:
  type: board        # board | module | dip | to92
  length: 54.4
  width: 27.9
  thickness: 1.6     # épaisseur du circuit imprimé, ou hauteur du boîtier
  color: "#16181d"   # toujours entre guillemets
  marking: NE555P    # texte imprimé (facultatif)
```

| Type     | Rendu                                                                 |
|----------|-----------------------------------------------------------------------|
| `board`  | circuit imprimé, noms des broches sérigraphiés                        |
| `module` | comme `board`, pour les petits modules (capteurs, convertisseurs)     |
| `dip`    | circuit intégré DIP : `width` = écart entre les rangées (7,62 pour un DIP-8) |
| `to92`   | transistor ou régulateur TO-92, face plate vers le bas de la vue      |

## Brochage

```yaml
pinout:
  pitch: 2.54            # écart entre broches (défaut : 2,54 ; 1,27 en to92)
  rows:
    - name: J2
      side: left         # left | right | top | bottom
      start: 4.6         # position de la 1re broche le long du côté (défaut : rangée centrée)
      inset: 1.27        # distance au bord (défaut : 1,27 ; 0 pour dip et to92)
      pins:
        - { n: 1, name: 3V3, type: power, description: "Sortie 3,3 V" }
        - { n: 2, name: GPIO36, type: analog, functions: [ADC1_CH0, SENSOR_VP] }
```

Les broches d'une rangée sont données **dans l'ordre physique** : de haut en bas pour
`left` et `right`, de gauche à droite pour `top` et `bottom`. Pour un DIP, la rangée de droite
se lit donc 8, 7, 6, 5.

| Clé           | Rôle                                                  |
|---------------|-------------------------------------------------------|
| `n`           | numéro affiché (défaut : rang dans la rangée)         |
| `name`        | nom court, sérigraphié sur la carte                   |
| `type`        | couleur et filtre (voir ci-dessous)                   |
| `functions`   | fonctions alternatives : `[SDA, ADC2_CH0]`            |
| `description` | précision affichée au survol et dans le tableau       |

| Type       | Affiché comme   |
|------------|-----------------|
| `power`    | Alimentation    |
| `ground`   | Masse           |
| `gpio`     | E/S numérique   |
| `analog`   | Analogique      |
| `pwm`      | PWM             |
| `i2c`      | I²C             |
| `spi`      | SPI             |
| `uart`     | UART            |
| `control`  | Contrôle (reset, enable, boot…) |
| `reserved` | Réservée (à ne pas utiliser) |
| `nc`       | Non connectée   |
| `other`    | Autre           |

## Pièces réelles (vue 3D)

Les modèles viennent de la bibliothèque 3D de KiCad, convertis en `.glb` dans `sheets/models/`.
Pour en ajouter un : déclarer son fichier STEP dans `tools/models.yaml`, puis lancer
`python tools/build_models.py` (dépendances : `requirements-dev.txt`). Un modèle de fabricant
au format STEP peut aussi y être ajouté, si sa licence permet de le redistribuer.

```yaml
parts:
  - { name: Module ESP32, model: models/esp32-wroom-32e.glb, x: 13.95, y: 12.75, color: "#c8ccd2", label: "ESP32-WROOM-32E" }
  - { name: Barrette J2, model: models/pin-header-1x19.glb, x: 1.27, y: 27.46, side: bottom }
  - { name: Microcontrôleur, model: models/tqfp-32.glb, x: 9, y: 26.5, rotation: 45, label: "ATMEGA328P" }
```

| Clé        | Rôle                                                                  |
|------------|-----------------------------------------------------------------------|
| `model`    | fichier de `sheets/models/`                                           |
| `x`, `y`   | position du **centre** de la pièce, en mm depuis le coin haut gauche  |
| `rotation` | rotation en degrés, sens inverse des aiguilles d'une montre vue de dessus |
| `side`     | `top` (défaut) ou `bottom` : pièce montée sous la carte (barrettes mâles…) |
| `z`        | décalage vertical en mm (rarement utile)                              |
| `color`    | couleur de la pièce dans le schéma 2D (`#2a2d34` par défaut)         |
| `label`    | inscription imprimée sur le dessus (puces, blindages)                 |

Pour un `dip` ou un `to92`, une seule pièce : le boîtier, centré sur l'appareil.

Les pièces sans modèle peuvent rester sous forme de boîtes simples :

```yaml
components:
  - { name: Bouton, x: 5, y: 30, width: 6, length: 6, height: 3.5, color: "#c8ccd2" }
```

## Pièges du YAML

- Mettre entre guillemets les couleurs (`"#1d5c3a"`) et les textes qui contiennent `:` ou `#`.
- Les noms `ON`, `OFF`, `YES`, `NO` restent du texte dans Prométhée, mais d'autres outils YAML
  les lisent comme des booléens : les guillemets ne coûtent rien.
- L'indentation se fait avec des espaces, jamais des tabulations.

Une fiche invalide n'empêche pas les autres de s'afficher : elle est signalée en haut de la page
**Fiches**, avec le message d'erreur et un lien pour la corriger.

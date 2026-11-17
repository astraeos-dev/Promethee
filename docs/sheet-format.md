# Format d'une fiche

Ce document sert à préparer les fiches livrées avec Prométhée. Pour en obtenir une nouvelle,
il suffit d'[ouvrir une demande](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml) :
la fiche et le modèle 3D de l'appareil sont réalisés d'après sa fiche technique et des photos,
puis ajoutés dans une mise à jour.

Chaque appareil a son fichier dans le dossier `sheets/` du dépôt : `sheets/<identifiant>.md`.
L'identifiant est le nom du fichier, en minuscules, chiffres et tirets (`esp32-devkitc-v4`).
Les fichiers qui commencent par `_` (comme `_template.md`) ne sont pas listés.

Une fiche a deux parties :

1. un **en-tête YAML** entre deux lignes `---` : identité, caractéristiques, boîtier, brochage,
   pièces. Les **clés sont en anglais**, les valeurs dans la langue de votre choix ;
2. un **texte en Markdown** : présentation, câblage, code d'exemple, précautions.
   Il s'affiche dans l'onglet « Utilisation ».

## Préparer une fiche

1. Copier `sheets/_template.md` sous le nom `sheets/<identifiant>.md` et le compléter.
2. Construire le modèle 3D : `python tools/build_models.py <identifiant>`
   (dépendances : `pip install -r requirements-dev.txt`). Il est écrit dans
   `sheets/models/<identifiant>.glb`.
3. Vérifier le résultat avec Prométhée en développement (`uvicorn app.main:app --reload`),
   puis lancer `pytest` : les tests refusent une fiche avec des avertissements, ou dont le modèle 3D
   n'a pas été reconstruit après une modification.

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

## Boîtier

Toutes les dimensions sont en millimètres, **vue de dessus** : `width` est horizontale,
`length` verticale, et les positions `x`, `y` se comptent depuis le coin haut gauche.

```yaml
package:
  type: board          # board | module | dip | to92
  length: 54.4
  width: 27.9
  thickness: 1.6       # épaisseur du circuit imprimé, ou hauteur du boîtier
  color: "#16181d"     # vernis (ou corps du boîtier), toujours entre guillemets
  marking: NE555P      # inscription d'un DIP ou d'un TO-92
  finish: gold         # pastilles : gold (or, ENIG) ou tin (étain, HASL)
  corner_radius: 0.8   # arrondi des coins du circuit imprimé
  silkscreen:          # textes sérigraphiés en plus des noms de broches
    - { text: EN, x: 7.2, y: 47.1, size: 1.0 }
    - { text: "ESP32-DevKitC V4", x: 14, y: 30, size: 1.2, side: bottom }
  holes:               # perçages en plus des broches (connecteur non monté, fixation)
    - { x: 6.46, y: 40.9, drill: 1.0, pad: 1.7, square: true }
    - { x: 2.5, y: 2.5, drill: 3.2 }   # sans pad : trou non métallisé
```

| Type     | Modèle 3D                                                             |
|----------|-----------------------------------------------------------------------|
| `board`  | circuit imprimé complet : âme en FR4, vernis, sérigraphie, trous métallisés, pastilles, soudures |
| `module` | comme `board`, pour les petits modules (capteurs, convertisseurs)     |
| `dip`    | boîtier DIP : `width` = écart entre les rangées (7,62 pour un DIP-8)  |
| `to92`   | transistor ou régulateur TO-92, face plate vers le bas de la vue, pattes longues |

Sur une carte, chaque broche reçoit un trou métallisé de 1 mm et une pastille de 1,7 mm, carrée
pour la broche n° 1, et une soudure du côté opposé au corps des barrettes.

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
        - { n: 3, name: GPIO36, silkscreen: SVP, type: analog, functions: [ADC1_CH0, SENSOR_VP] }
```

Les broches d'une rangée sont données **dans l'ordre physique** : de haut en bas pour
`left` et `right`, de gauche à droite pour `top` et `bottom`. Pour un DIP, la rangée de droite
se lit donc 8, 7, 6, 5.

| Clé           | Rôle                                                  |
|---------------|-------------------------------------------------------|
| `n`           | numéro affiché (défaut : rang dans la rangée)         |
| `name`        | nom de la broche, dans le tableau et le schéma        |
| `silkscreen`  | texte imprimé à côté de la broche sur la vraie carte, s'il diffère du nom |
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

## Pièces (modèle 3D)

Chaque pièce posée sur l'appareil est soit un **modèle réel** de la bibliothèque 3D de KiCad,
déclaré dans `tools/parts.yaml` et converti dans `tools/parts/`, soit une **forme simple**
pour ce qui n'y existe pas (relais, afficheur, bornier…).

```yaml
parts:
  - { name: Module ESP32, model: esp32-wroom-32e, x: 13.95, y: 12.75, color: "#c8ccd2", label: "ESP32-WROOM-32E" }
  - { name: Barrette J2, model: pin-header-1x19, x: 1.27, y: 27.46, side: bottom }
  - { name: Microcontrôleur, model: tqfp-32, x: 9, y: 26.5, rotation: 45, label: "ATMEGA328P" }
  - { name: Relais, shape: box, x: 20, y: 15, width: 15.5, length: 19, height: 15.5, color: "#1f5fc4", label: "SRD-05VDC" }
```

| Clé        | Rôle                                                                  |
|------------|-----------------------------------------------------------------------|
| `model`    | nom d'une pièce de `tools/parts.yaml`                                 |
| `shape`    | à défaut de modèle : `box` ou `cylinder`, avec `width`, `length`, `height` |
| `x`, `y`   | position du **centre** de la pièce                                    |
| `rotation` | rotation en degrés, sens inverse des aiguilles d'une montre vue de dessus |
| `side`     | `top` (défaut) ou `bottom` : pièce montée sous la carte (barrettes mâles…) |
| `z`        | décalage vertical en mm (rarement utile)                              |
| `color`    | couleur de la forme simple, et de la pièce dans le schéma 2D          |
| `label`    | inscription imprimée sur le dessus (puces, blindages)                 |

Pour un `dip` ou un `to92`, une seule pièce : le boîtier, centré sur l'appareil ; son inscription
vient de `package.marking`.

Pour ajouter un modèle KiCad : ajouter son fichier STEP dans `tools/parts.yaml`, puis relancer
`python tools/build_models.py`. Un modèle STEP de fabricant peut aussi y être ajouté si sa
licence permet de le redistribuer.

## Liste de matériel (demandes)

`sheets/catalog.yaml` liste du matériel courant, sans fiche : la page **Demander une fiche**
l'affiche, et chaque appareil ouvre le formulaire GitHub `fiche.yml` déjà rempli (les paramètres
de l'adresse portent les identifiants des champs du formulaire).

```yaml
devices:
  - id: arduino-uno-r3            # identifiant de la future fiche : sheets/arduino-uno-r3.md
    name: Arduino Uno R3
    category: Carte de développement
    manufacturer: Arduino
    part_number: A000066
    description: Carte ATmega328P en 5 V, la référence pour débuter.
    dimensions: 68,6 × 53,4 mm     # facultatif
    links: [https://docs.arduino.cc/hardware/uno-rev3/]
```

Quand une fiche porte le même identifiant qu'un appareil de la liste, la page affiche
« Fiche disponible » et renvoie vers elle. Les liens de la liste et des fiches sont vérifiés par
`python tools/check_links.py` (workflow **Links**, chaque semaine et à chaque modification).

## Pièges du YAML

- Mettre entre guillemets les couleurs (`"#1d5c3a"`) et les textes qui contiennent `:` ou `#`.
- Les noms `ON`, `OFF`, `YES`, `NO` restent du texte dans Prométhée, mais d'autres outils YAML
  les lisent comme des booléens : les guillemets ne coûtent rien.
- L'indentation se fait avec des espaces, jamais des tabulations.

Une fiche invalide n'empêche pas les autres de s'afficher : elle est signalée en haut de la page
**Fiches**, avec le message d'erreur.

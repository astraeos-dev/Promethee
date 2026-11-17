# Format d'une fiche

Chaque appareil a son fichier dans le dossier `fiches/` : `fiches/<identifiant>.md`.
L'identifiant est le nom du fichier, en minuscules, chiffres et tirets (`esp32-devkitc-v4`).
Les fichiers qui commencent par `_` (comme `_modele.md`) ne sont pas listés.

Une fiche a deux parties :

1. un **en-tête YAML** entre deux lignes `---` : identité, caractéristiques, boîtier, brochage ;
2. un **texte en Markdown** : présentation, câblage, code d'exemple, précautions.
   Il s'affiche dans l'onglet « Utilisation ».

Le plus simple est de copier `fiches/_modele.md`, ou d'utiliser **+ Nouvelle fiche** dans
l'interface, qui montre l'aperçu 3D et les erreurs pendant la saisie. Un fichier modifié à la
main est relu au prochain affichage, sans redémarrer le conteneur.

## Identité

| Clé               | Obligatoire | Exemple                                  |
|-------------------|-------------|------------------------------------------|
| `nom`             | oui         | `ESP32-DevKitC V4`                       |
| `categorie`       | non         | `Carte de développement` (défaut : Divers) |
| `fabricant`       | non         | `Espressif`                              |
| `reference`       | non         | `ESP32-DevKitC-32E`                      |
| `description`     | non         | une phrase, affichée sur la carte de la fiche |
| `tags`            | non         | `[wifi, bluetooth]`                      |
| `caracteristiques`| non         | liste `Clé: valeur`, affichée en tableau |
| `liens`           | non         | liste de `{ titre, url }` (datasheets, guides) |

## Boîtier et vue 3D

La vue 3D est **générée** à partir de `boitier`, `brochage` et `composants`.
Toutes les dimensions sont en millimètres, **vue de dessus** : la `largeur` est horizontale,
la `longueur` verticale.

```yaml
boitier:
  type: carte        # carte | module | dip | to92
  longueur: 54.4
  largeur: 27.9
  epaisseur: 1.6     # épaisseur du circuit imprimé, ou hauteur du boîtier
  couleur: "#16181d" # toujours entre guillemets
  marquage: NE555P   # texte imprimé (facultatif)
```

| Type     | Rendu                                                                 |
|----------|-----------------------------------------------------------------------|
| `carte`  | circuit imprimé, barrettes mâles dessous, noms des broches sérigraphiés |
| `module` | comme `carte`, pour les petits modules (capteurs, convertisseurs)     |
| `dip`    | circuit intégré DIP : `largeur` = écart entre les rangées (7,62 pour un DIP-8) |
| `to92`   | transistor ou régulateur TO-92, face plate vers le bas de la vue      |

Pour afficher un vrai modèle (exporté de KiCad, FreeCAD, Fusion…), déposer un fichier `.glb`,
`.gltf` (en un seul fichier) ou `.stl` dans `fiches/modeles/`, ou utiliser **Joindre un modèle 3D**
dans l'éditeur, puis :

```yaml
modele3d: modeles/esp32-devkitc.glb
```

Le bouton **Modèle fourni** bascule alors entre le modèle et la vue générée (seule la vue générée
permet de survoler les broches).

## Brochage

```yaml
brochage:
  pas: 2.54              # écart entre broches (défaut : 2,54 ; 1,27 en to92)
  rangees:
    - nom: J2
      cote: gauche       # gauche | droite | haut | bas
      debut: 4.6         # position de la 1re broche le long du côté (défaut : rangée centrée)
      retrait: 1.27      # distance au bord (défaut : 1,27 ; 0 pour dip et to92)
      broches:
        - { n: 1, nom: 3V3, type: alim, desc: "Sortie 3,3 V" }
        - { n: 2, nom: GPIO36, type: analogique, fonctions: [ADC1_CH0, SENSOR_VP] }
```

Les broches d'une rangée sont données **dans l'ordre physique** : de haut en bas pour
`gauche` et `droite`, de gauche à droite pour `haut` et `bas`. Pour un DIP, la rangée de droite
se lit donc 8, 7, 6, 5.

| Clé         | Rôle                                                   |
|-------------|--------------------------------------------------------|
| `n`         | numéro affiché (défaut : rang dans la rangée)          |
| `nom`       | nom court, sérigraphié sur la carte                    |
| `type`      | couleur et filtre (voir ci-dessous)                    |
| `fonctions` | fonctions alternatives : `[SDA, ADC2_CH0]`             |
| `desc`      | précision affichée au survol et dans le tableau        |

Types : `alim`, `masse`, `gpio`, `analogique`, `pwm`, `i2c`, `spi`, `uart`, `controle`,
`reserve` (à ne pas utiliser), `nc` (non connectée), `autre`.

## Composants visibles

Pour rendre la carte reconnaissable : puces, connecteurs, boutons. `x` et `y` sont la position
du **centre**, depuis le coin haut gauche.

```yaml
composants:
  - { nom: Module ESP32, x: 13.95, y: 12.2, largeur: 18, longueur: 25.5, hauteur: 3.1, couleur: "#b9bec6", texte: "ESP32-WROOM-32E" }
  - { nom: Condensateur, x: 5, y: 30, largeur: 5, longueur: 5, hauteur: 7, forme: cylindre, couleur: "#1d3f8f" }
```

## Pièges du YAML

- Mettre entre guillemets les couleurs (`"#1d5c3a"`) et les textes qui contiennent `:` ou `#`.
- Les noms `ON`, `OFF`, `YES`, `NO` restent du texte dans Prométhée, mais d'autres outils YAML
  les lisent comme des booléens : les guillemets ne coûtent rien.
- L'indentation se fait avec des espaces, jamais des tabulations.

Une fiche invalide n'empêche pas les autres de s'afficher : elle est signalée en haut de la page
**Fiches**, avec le message d'erreur et un lien pour la corriger.

# Journal des modifications

## 0.4.0

- **Vue 3D corrigée** : elle ne se chargeait pas (fichier Three.js absent de l'image 0.3.0).
- **Vue 3D réaliste** : vrais modèles des composants (module ESP32-WROOM-32E, barrettes,
  connecteurs USB, puces, boîtiers DIP-8 et TO-92) issus de la bibliothèque KiCad.
- **Fiches livrées avec les mises à jour** : l'éditeur disparaît ; nouvelles fiches et corrections
  se demandent sur GitHub (boutons « Demander une fiche » et « Signaler une erreur »).
  Le dossier `sheets` de `/addon_configs` n'est plus utilisé.
- Schéma 2D : les pièces réelles y sont dessinées à l'échelle.

## 0.3.0

- Code, API et base de données en anglais ; l'interface reste en français.
- **Format des fiches** : clés YAML en anglais (`name`, `category`, `package`, `pinout`, `rows`,
  `pins`…). Dossier `fiches/` renommé `sheets/`.
- **Capteurs renommés** : `sensor.promethee_items`, `_parts`, `_low_stock`, `_sheets`
  (attribut `items`). Mettre à jour les automatisations.
- Import CSV : en-têtes anglais, ou français comme avant.

## 0.2.0

- Module complémentaire Home Assistant : interface dans la barre latérale (Ingress).
- Capteurs `sensor.promethee_*` publiés dans Home Assistant.
- Point d'accès `/api/alerts` : articles sous leur seuil.

## 0.1.0

- Stock, fiches techniques, vue 3D, brochage, éditeur, import et export CSV.

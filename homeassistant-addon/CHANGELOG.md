# Journal des modifications

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

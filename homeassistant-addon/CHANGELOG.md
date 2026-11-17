# Journal des modifications

## 0.5.1

- **Nouvel article** : le champ « Nom » propose une liste de matériel courant (90 références
  classées par catégorie, avec recherche). Choisir un nom remplit la catégorie, la valeur, le
  boîtier, la référence et la fiche liée ; le champ « Valeur » propose ensuite les valeurs
  courantes (résistances, condensateurs, LED…). Un champ rempli à la main n'est jamais remplacé.
- **Demander une fiche** ouvre directement le formulaire de demande sur GitHub ; la page de liste
  de la 0.5.0 disparaît.
- « Ajouter au stock », depuis une fiche, remplit aussi le boîtier et la référence.
- Formulaire d'article : la touche Entrée enregistre, au lieu de fermer le formulaire.
- Liens corrigés vers les fiches techniques de l'ESP32-S3-DevKitC-1, du HC-SR501, du MPU-6050,
  du SG90, de l'ULN2803A et du 2N7000.

## 0.5.0

- **Demander une fiche** : liste de matériel courant (une soixantaine d'appareils : cartes,
  capteurs, afficheurs, modules, alimentation, moteurs, circuits intégrés, transistors, diodes).
  Chaque appareil ouvre le formulaire GitHub déjà rempli ; « Autre appareil » ouvre le formulaire vide.
- Formulaire de demande : la catégorie devient un champ texte, pré-rempli depuis la liste.
- Vérification hebdomadaire des liens vers les fiches techniques (workflow Links).

## 0.4.0

- **Vue 3D corrigée** : elle ne se chargeait pas (fichier Three.js absent de l'image 0.3.0).
- **Modèle 3D complet de chaque appareil** : circuit imprimé (vernis, sérigraphie de la vraie
  carte, trous métallisés, pastilles, soudures) et composants réels issus de la bibliothèque KiCad
  (module ESP32-WROOM-32E, barrettes, connecteurs USB, puces, boîtiers DIP-8 et TO-92) ;
  téléchargeable depuis la fiche (`.glb`).
- Vue 3D plus légère : affichage à la demande, fichiers compressés à l'envoi.
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

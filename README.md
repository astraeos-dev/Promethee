<p align="center"><img src="assets/brand/icon.svg" width="128" height="128" alt="Prométhée"></p>

# Prométhée — stock électronique et fiches techniques en 3D

> Un conteneur Docker pour suivre son stock de composants et de cartes, avec pour chaque appareil
> une fiche en Markdown : vue 3D interactive, brochage, caractéristiques et mode d'emploi.

[![Tests](https://github.com/astraeos-dev/Promethee/actions/workflows/tests.yml/badge.svg)](https://github.com/astraeos-dev/Promethee/actions/workflows/tests.yml)
[![Licence MIT](https://img.shields.io/github/license/astraeos-dev/Promethee?label=licence)](LICENSE)
![Docker](https://img.shields.io/badge/Docker-Compose%20v2-2496ed?logo=docker&logoColor=white)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-module-18bcf2?logo=homeassistant&logoColor=white)

<a href="https://buymeacoffee.com/gregorychau"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>

**Installer** : dans Home Assistant, ajouter ce dépôt aux modules complémentaires ;
ou bien `docker compose up -d`, puis ouvrir <http://localhost:8080>. Une idée, un problème ?
[Ouvrir une demande](https://github.com/astraeos-dev/Promethee/issues/new/choose).

**Projet actif** · un des projets d'Astraeos : [site web](https://astraeos-dev.github.io/personnal-site/)

---

<p align="center"><img src="assets/captures/fiche-3d.png" alt="Fiche de l'ESP32-DevKitC : vue 3D avec les noms des broches"></p>

## Présentation

Un atelier d'électronique accumule vite des centaines de références : résistances, capteurs,
cartes de développement. Prométhée répond à deux questions : *combien m'en reste-t-il, et où ?*
et *comment se branche cet appareil ?*

Le stock vit dans une base SQLite, avec l'historique de chaque entrée et sortie. Les fiches
techniques, une par appareil, sont **livrées avec les mises à jour** : un appareil manque, il
suffit d'en [faire la demande](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml).
Chaque fiche montre l'appareil dans un **modèle 3D complet, construit pour lui** : circuit imprimé
avec ses trous métallisés, ses pastilles, ses soudures et la sérigraphie de la vraie carte, composants
réels issus de la bibliothèque KiCad. S'y ajoutent un schéma de brochage et un tableau des broches,
reliés entre eux : survoler une broche l'éclaire partout.

Tout fonctionne hors ligne : Three.js est inclus dans l'image, aucune ressource n'est chargée
depuis Internet.

## Fonctionnalités

- **Stock** : quantités, emplacement, seuil d'alerte, fournisseur, prix ; boutons + et − ;
  historique des mouvements ; recherche et filtres ; import et export CSV (compatible tableur).
- **Fiches techniques** : livrées avec chaque version ; nouvelles fiches et corrections
  demandées par des formulaires GitHub, accessibles depuis l'interface.
- **Modèle 3D de chaque appareil** : circuit imprimé aux dimensions réelles (vernis, sérigraphie
  telle qu'imprimée sur la carte, trous métallisés, pastilles en or ou en étain, soudures) et
  composants réels (modules, barrettes, connecteurs USB, puces, boîtiers DIP et TO-92) ; étiquettes,
  vues de dessus, de face et de dessous ; modèle téléchargeable au format glTF (`.glb`).
- **Brochage** : schéma 2D et tableau colorés par type (alimentation, I²C, SPI, UART…),
  avec fonctions alternatives et précautions ; filtre par type.
- **Utilisation** : texte libre en Markdown (câblage, code, formules), caractéristiques et liens
  vers les datasheets.
- **Home Assistant** : module complémentaire avec l'interface dans la barre latérale, et capteurs
  (pièces en stock, articles à réapprovisionner) pour les tableaux de bord et les notifications.
- **Lien stock ↔ fiche** : chaque article peut pointer vers sa fiche, qui affiche la quantité en stock.

<p align="center"><img src="assets/captures/brochage.png" alt="Schéma de brochage et tableau des broches"></p>

## Installation

### Dans Home Assistant (module complémentaire)

Prérequis : Home Assistant OS ou Supervised, sur aarch64 (Raspberry Pi 4 et 5) ou amd64.

1. **Paramètres › Modules complémentaires › Boutique › ⋮ › Dépôts**, ajouter
   `https://github.com/astraeos-dev/Promethee`.
2. Installer **Prométhée**, le démarrer et cocher **Afficher dans la barre latérale**.

L'interface s'ouvre dans Home Assistant (Ingress), sans port à ouvrir. Les nouvelles fiches
arrivent avec les mises à jour du module. Capteurs, exemples d'automatisation et de carte :
[homeassistant-addon/DOCS.md](homeassistant-addon/DOCS.md).

### Avec Docker Compose

Prérequis : Docker avec Compose v2.

```bash
git clone https://github.com/astraeos-dev/Promethee.git
cd Promethee
docker compose up -d
```

L'interface répond sur <http://localhost:8080>. Le dossier `db/` reçoit la base SQLite du stock
(`inventory.sqlite3`), à sauvegarder.

Sous Linux, si votre identifiant n'est pas 1000, lancez `UID=$(id -u) GID=$(id -g) docker compose up -d`
pour que les fichiers créés vous appartiennent.

Sans Compose :

```bash
docker build -t promethee .
docker run -d -p 8080:8000 -v promethee-db:/var/lib/promethee/db ghcr.io/astraeos-dev/promethee
```

## Utilisation

```bash
docker compose up -d          # démarrer
docker compose logs -f        # suivre les journaux
docker compose up -d --build  # mettre à jour après un git pull
```

### Demander une fiche

Le bouton **Demander une fiche** ouvre une liste de matériel courant (cartes Arduino, ESP32 et
Raspberry Pi Pico, capteurs, afficheurs, modules, régulateurs, circuits intégrés, transistors,
diodes…). Choisir un appareil ouvre le formulaire de demande sur GitHub, déjà rempli : nom,
fabricant et référence, catégorie, liens vers la fiche technique, dimensions. Il reste à ajouter
des photos si possible. **Autre appareil** ouvre le formulaire vide, ou directement
[ce lien](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml).
Les fiches sont ajoutées au fur et à mesure des demandes, dans les mises à jour.
Une erreur dans une fiche existante se signale avec **Signaler une erreur**, sur la fiche.

La liste est dans [sheets/catalog.yaml](sheets/catalog.yaml) ; ses liens sont vérifiés chaque
semaine par le workflow [Links](.github/workflows/links.yml).

Le format des fiches, pour les préparer, est décrit dans [docs/sheet-format.md](docs/sheet-format.md).

### Fiches fournies

ESP32-DevKitC V4, Arduino Nano, NE555, module BME280 et transistor PN2222A.

### Import CSV

Colonnes reconnues : `id`, `name`, `category`, `value`, `package`, `sheet`, `quantity`, `threshold`,
`location`, `supplier`, `price`, `notes` ; les en-têtes français (`nom`, `quantité`, `seuil`,
`emplacement`…) sont aussi acceptés. Séparateur `;`, `,` ou tabulation. Une ligne dont
l'`id` existe met l'article à jour, les autres créent un article.

### API

L'API REST est documentée sur <http://localhost:8080/api/docs>.

## Configuration

| Variable             | Défaut             | Rôle                                   |
|----------------------|--------------------|----------------------------------------|
| `PROMETHEE_DB_DIR`   | `/var/lib/promethee/db` | dossier de la base SQLite              |
| `PROMETHEE_HA_URL`   | —                  | Home Assistant à informer, ex. `http://192.168.1.10:8123` |
| `PROMETHEE_HA_TOKEN` | —                  | jeton d'accès longue durée (profil Home Assistant › Sécurité) |
| `PROMETHEE_HA`       | activé             | `off` pour ne publier aucun capteur |

Avec `PROMETHEE_HA_URL` et `PROMETHEE_HA_TOKEN`, un conteneur installé hors de Home Assistant
publie les mêmes capteurs `sensor.promethee_*` que le module complémentaire.

## Limites

- Pas de comptes utilisateurs : à réserver au réseau local, ou à placer derrière un
  reverse proxy avec authentification.
- Les modèles 3D sont fidèles au boîtier, aux dimensions, aux broches, aux composants principaux et
  à la sérigraphie ; les pistes de cuivre ne sont pas dessinées et les petits composants passifs
  sont représentatifs, pas exhaustifs.
- Les fiches ne se modifient pas depuis l'interface : elles arrivent avec les mises à jour.

## Développement

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                   # tests
uvicorn app.main:app --reload            # http://localhost:8000
python tools/build_models.py             # construit les modèles 3D des fiches (sheets/models)
```

Structure : `app/` (API FastAPI, stock SQLite, lecture des fiches, capteurs Home Assistant), `app/static/` (interface en
JavaScript sans framework), `sheets/` (fiches et modèles 3D), `tools/` (construction des modèles 3D), `homeassistant-addon/` (module Home Assistant), `tests/`.
Le code (identifiants, commentaires, API, base de données) est en anglais ; l'interface et la
documentation sont en français.

L'image `ghcr.io/astraeos-dev/promethee` (amd64 et arm64) est publiée à chaque poussée sur `main`
par [.github/workflows/image.yml](.github/workflows/image.yml). Pour une nouvelle version, changer
`app/__init__.py` et `homeassistant-addon/config.yaml` ensemble : un test le vérifie.

## Sources et crédits

- [Three.js](https://threejs.org) r170, MIT, inclus dans `app/static/vendor/three/`.
- Composants des modèles 3D : [bibliothèque KiCad](https://gitlab.com/kicad/libraries/kicad-packages3D),
  CC-BY-SA 4.0, convertis avec [cascadio](https://github.com/mikedh/cascadio) ; modèles construits
  avec [trimesh](https://trimesh.org) et [Shapely](https://shapely.readthedocs.io) ; voir
  [sheets/models/README.md](sheets/models/README.md).
- Sérigraphie : police [DejaVu Sans](https://dejavu-fonts.github.io), licence libre, dans `tools/fonts/`.
- [FastAPI](https://fastapi.tiangolo.com), [Uvicorn](https://www.uvicorn.org), [PyYAML](https://pyyaml.org),
  [Python-Markdown](https://python-markdown.github.io) : MIT ou BSD.
- Brochages établis d'après les documentations d'Espressif, Arduino, Texas Instruments, Bosch
  Sensortec et onsemi, citées dans chaque fiche.

## Licence

MIT, voir [LICENSE](LICENSE).

# Prométhée dans Home Assistant

## Installation

1. **Paramètres › Modules complémentaires › Boutique des modules complémentaires**.
2. Menu **⋮ › Dépôts**, ajouter `https://github.com/astraeos-dev/Promethee`, puis fermer.
3. Rechercher **Prométhée**, l'installer, puis **Démarrer**.
4. Activer **Afficher dans la barre latérale** : Prométhée apparaît dans le menu de Home Assistant.

L'interface passe par Home Assistant (Ingress) : pas de port à ouvrir, et seuls les utilisateurs
connectés à Home Assistant y ont accès.

## Où sont les fichiers

| Contenu | Emplacement |
|---------|-------------|
| Fiches (un fichier `.md` par appareil) | `/addon_configs/<id>_promethee/fiches/` |
| Modèles 3D (`.glb`, `.stl`) | `/addon_configs/<id>_promethee/fiches/modeles/` |
| Base du stock | interne au module, incluse dans les sauvegardes de Home Assistant |

Pour écrire des fiches à la main, ouvrir ce dossier avec le module **Studio Code Server**,
**File editor** (désactiver *Enforce Basepath*) ou un partage **Samba** (dossier `addon_configs`).
Partir de `_modele.md`. Une fiche enregistrée apparaît au prochain affichage, sans redémarrage.
Au premier démarrage, cinq fiches d'exemple sont créées.

## Capteurs

Le module publie ces capteurs, mis à jour après chaque modification du stock et toutes les 5 minutes :

| Entité | Valeur |
|--------|--------|
| `sensor.promethee_references` | nombre de références en stock |
| `sensor.promethee_pieces` | nombre total de pièces |
| `sensor.promethee_alertes` | articles à réapprovisionner (quantité ≤ seuil) ; l'attribut `articles` les liste |
| `sensor.promethee_fiches` | nombre de fiches techniques |

Ces entités n'ont pas d'identifiant unique : elles ne se renomment pas depuis l'interface,
mais s'utilisent normalement dans les cartes, les automatisations et l'historique.

### Notification quand un article passe sous son seuil

```yaml
automation:
  - alias: Prométhée — stock bas
    triggers:
      - trigger: state
        entity_id: sensor.promethee_alertes
    conditions:
      - condition: template
        value_template: >
          {{ trigger.from_state is not none and trigger.from_state.state not in ['unknown', 'unavailable']
             and trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}
    actions:
      - action: notify.notify
        data:
          title: Stock électronique
          message: >
            À réapprovisionner :
            {% for a in state_attr('sensor.promethee_alertes', 'articles') %}
            - {{ a.nom }} {{ a.valeur }} : {{ a.quantite }} (seuil {{ a.seuil }}, {{ a.emplacement }})
            {% endfor %}
```

### Carte du tableau de bord

```yaml
type: markdown
title: À réapprovisionner
content: >
  {% set articles = state_attr('sensor.promethee_alertes', 'articles') or [] %}
  {% for a in articles %}
  - **{{ a.nom }}** {{ a.valeur }} — {{ a.quantite }} / {{ a.seuil }} · {{ a.emplacement }}
  {% else %}
  Rien à commander.
  {% endfor %}
```

## Accès direct (facultatif)

Dans l'onglet **Configuration › Réseau**, un port peut être attribué pour ouvrir Prométhée sans
passer par Home Assistant, par exemple `8080` puis `http://homeassistant.local:8080`.
Cet accès n'a **pas d'authentification** : à réserver au réseau local.

## Sauvegarde

Les sauvegardes de Home Assistant incluent le module : base du stock et fiches.
Le stock s'exporte aussi en CSV depuis la page **Stock**.

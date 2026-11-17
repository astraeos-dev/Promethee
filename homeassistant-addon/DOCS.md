# Prométhée dans Home Assistant

## Installation

1. **Paramètres › Modules complémentaires › Boutique des modules complémentaires**.
2. Menu **⋮ › Dépôts**, ajouter `https://github.com/astraeos-dev/Promethee`, puis fermer.
3. Rechercher **Prométhée**, l'installer, puis **Démarrer**.
4. Activer **Afficher dans la barre latérale** : Prométhée apparaît dans le menu de Home Assistant.

L'interface passe par Home Assistant (Ingress) : pas de port à ouvrir, et seuls les utilisateurs
connectés à Home Assistant y ont accès.

## Fiches techniques

Les fiches (brochage, vue 3D, mode d'emploi) sont livrées avec le module et arrivent avec ses
mises à jour. Pour en demander une : bouton **Demander une fiche** dans Prométhée, qui propose
une liste de matériel courant et ouvre le formulaire GitHub déjà rempli, ou
[ce formulaire](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml).
Une erreur dans une fiche se signale avec **Signaler une erreur**, sur la fiche.

Le stock, lui, est enregistré dans le module et inclus dans les sauvegardes de Home Assistant.

## Capteurs

Le module publie ces capteurs, mis à jour après chaque modification du stock et toutes les 5 minutes :

| Entité | Valeur |
|--------|--------|
| `sensor.promethee_items` | nombre de références en stock |
| `sensor.promethee_parts` | nombre total de pièces |
| `sensor.promethee_low_stock` | articles à réapprovisionner (quantité ≤ seuil) ; l'attribut `items` les liste |
| `sensor.promethee_sheets` | nombre de fiches techniques |

Ces entités n'ont pas d'identifiant unique : elles ne se renomment pas depuis l'interface,
mais s'utilisent normalement dans les cartes, les automatisations et l'historique.

### Notification quand un article passe sous son seuil

```yaml
automation:
  - alias: Prométhée — stock bas
    triggers:
      - trigger: state
        entity_id: sensor.promethee_low_stock
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
            {% for a in state_attr('sensor.promethee_low_stock', 'items') %}
            - {{ a.name }} {{ a.value }} : {{ a.quantity }} (seuil {{ a.threshold }}, {{ a.location }})
            {% endfor %}
```

### Carte du tableau de bord

```yaml
type: markdown
title: À réapprovisionner
content: >
  {% set items = state_attr('sensor.promethee_low_stock', 'items') or [] %}
  {% for a in items %}
  - **{{ a.name }}** {{ a.value }} — {{ a.quantity }} / {{ a.threshold }} · {{ a.location }}
  {% else %}
  Rien à commander.
  {% endfor %}
```

## Accès direct (facultatif)

Dans l'onglet **Configuration › Réseau**, un port peut être attribué pour ouvrir Prométhée sans
passer par Home Assistant, par exemple `8080` puis `http://homeassistant.local:8080`.
Cet accès n'a **pas d'authentification** : à réserver au réseau local.

## Sauvegarde

Les sauvegardes de Home Assistant incluent le module et donc la base du stock.
Le stock s'exporte aussi en CSV depuis la page **Stock**.

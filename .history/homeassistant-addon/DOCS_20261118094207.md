# Prométhée in Home Assistant

L'interface passe par Home Assistant (Ingress) : pas de port à ouvrir, et seuls les utilisateurs
connectés à Home Assistant y ont accès.

## Installation

1. **Settings › Add-ons › Add-on Store**.
2. **⋮ menu › Repositories**, add `https://github.com/astraeos-dev/Promethee`, then close.
3. Search for **Prométhée**, install it, and then click **Start**.
4. Enable **Show in sidebar**: Prométhée will appear in the Home Assistant menu.

## Stock

## Technical Data Sheets

Data sheets (pinout, 3D view, user manual) are provided with the module and are included in its
updates. To request one, use the **Request a data sheet** button in Prométhée, which opens
[the request form](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml)
on GitHub. To report an error in a data sheet, use the **Report an error** option found on the sheet itself.

Pour un nouvel article, le champ **Nom** propose une liste de matériel courant : choisir un nom
remplit la catégorie, la valeur, le boîtier, la référence et la fiche liée.

Le stock est enregistré dans le module et inclus dans les sauvegardes de Home Assistant.

### Notification quand un article passe sous son seuil

## Sensors

The module publishes these sensors, which are updated after every stock change and every 5 minutes:

| Entity                         | Value                                                                                     |
| ------------------------------ | ----------------------------------------------------------------------------------------- |
| `sensor.promethee_items`     | number of stock items (SKUs)                                                              |
| `sensor.promethee_parts`     | total number of individual parts                                                          |
| `sensor.promethee_low_stock` | items requiring replenishment (quantity ≤ threshold); the `items` attribute lists them |
| `sensor.promethee_sheets`    | number of technical data sheets                                                           |

These entities do not have a unique identifier; they cannot be renamed via the interface,
but they can be used as normal in cards, automations, and history.

```yaml
automation:
  - alias: Prométhée — low stock
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
          title: Electronic stock
          message: >
            To restock:
            {% for a in state_attr('sensor.promethee_low_stock', 'items') %}
            - {{ a.name }} {{ a.value }} : {{ a.quantity }} (seuil {{ a.threshold }}, {{ a.location }})
            {% endfor %}
```

### Dashboard map

```yaml
type: markdown
title: To restock
content: >
  {% set items = state_attr('sensor.promethee_low_stock', 'items') or [] %}
  {% for a in items %}
  - **{{ a.name }}** {{ a.value }} — {{ a.quantity }} / {{ a.threshold }} · {{ a.location }}
  {% else %}
  Rien à commander.
  {% endfor %}
```


## Direct Access (Optional)

In the **Configuration › Network** tab, you can assign a port to open Prométhée without going through Home Assistant—for example, using port `8080` would allow access via `http://homeassistant.local:8080`.
This access method has **no authentication**; it should be restricted to your local network.

## Backup

Home Assistant backups include this module, and therefore the inventory database.
You can also export your inventory as a CSV file from the **Inventory** page.

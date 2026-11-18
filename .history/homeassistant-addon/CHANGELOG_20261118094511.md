# Changelog

## 0.5.1

- **New item**: the “Name” field now suggests a list of commonly used equipment (90 references,
  categorized and searchable). Selecting a name fills in the category, value, package,
  reference, and linked sheet; the “Value” field then suggests common values
  (resistors, capacitors, LEDs, etc.). A manually entered field is never overwritten.
- **Request a sheet** now opens the GitHub request form directly; the list page from 0.5.0
  has been removed.
- “Add to inventory”, from a sheet, also fills in the package and reference.
- Item form: pressing Enter saves it instead of closing the form.
- Fixed links to the datasheets for the ESP32-S3-DevKitC-1, HC-SR501, MPU-6050,
  SG90, ULN2803A, and 2N7000.

## 0.5.0

- **Request a sheet**: list of commonly used equipment (around sixty devices: boards,
  sensors, displays, modules, power supplies, motors, integrated circuits, transistors, and diodes).
  Selecting a device opens a prefilled GitHub form; “Other device” opens a blank form.
- Request form: the category is now a text field, prefilled from the list.
- Weekly verification of datasheet links (Links workflow).

## 0.4.0

- **Fixed 3D view**: it would not load (Three.js file missing from the 0.3.0 image).
- **Complete 3D model for every device**: printed circuit board (solder mask, silkscreen from the real
  board, plated holes, pads, solder joints) and real components from the KiCad library
  (ESP32-WROOM-32E module, headers, USB connectors, chips, DIP-8 and TO-92 packages);
  downloadable from the sheet (`.glb`).
- Lighter 3D view: on-demand rendering and compressed files during transfer.
- **Sheets included with updates**: the editor has been removed; new sheets and corrections
  are requested through GitHub (buttons “Request a sheet” and “Report an error”).
  The `sheets` folder in `/addon_configs` is no longer used.
- 2D diagram: real components are drawn to scale.

## 0.3.0

- Code, API, and database are in English; the interface remains in French.
- **Sheet format**: YAML keys are in English (`name`, `category`, `package`, `pinout`, `rows`,
  `pins`, etc.). The `fiches/` folder was renamed to `sheets/`.
- **Sensors renamed**: `sensor.promethee_items`, `_parts`, `_low_stock`, `_sheets`
  (`items` attribute). Update automations accordingly.
- CSV import: English headers, or French headers as before.

## 0.2.0

- Home Assistant add-on: interface in the sidebar (Ingress).
- `sensor.promethee_*` sensors published in Home Assistant.
- `/api/alerts` endpoint: items below their threshold.

## 0.1.0

- Inventory, datasheets, 3D view, pinout, editor, and CSV import/export.

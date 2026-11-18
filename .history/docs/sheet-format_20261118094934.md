# Sheet Format

This document describes how to prepare sheets distributed with Prométhée. To request a new one,
open a [request](https://github.com/astraeos-dev/Promethee/issues/new?template=fiche.yml):
the device sheet and 3D model are created from its datasheet and photos, then included in an update.

Each device has a file in the repository’s `sheets/` directory: `sheets/<identifier>.md`.
The identifier is the lowercase filename, using digits and hyphens (`esp32-devkitc-v4`).
Files beginning with `_`, such as `_template.md`, are not listed.

A sheet has two parts:

1. a **YAML header** enclosed by two `---` lines: identity, specifications, package, pinout,
   and components. The **keys are in English**; values may use either language.
2. **Markdown text**: overview, wiring, example code, and precautions.
   It appears in the “Usage” tab.

## Preparing a Sheet

1. Copy `sheets/_template.md` to `sheets/<identifier>.md` and complete it.
2. Build the 3D model: `python tools/build_models.py <identifier>`
   (dependencies: `pip install -r requirements-dev.txt`). It is written to
   `sheets/models/<identifier>.glb`.
3. Verify the result in the Prométhée development server (`uvicorn app.main:app --reload`),
   then run `pytest`. The tests reject sheets with warnings or whose 3D model has not been
   rebuilt after a change.

## Identity

| Key            | Required | Example                                        |
|----------------|----------|------------------------------------------------|
| `name`         | yes      | `ESP32-DevKitC V4`                             |
| `category`     | no       | `Development board` (default: Miscellaneous)   |
| `manufacturer` | no       | `Espressif`                                    |
| `part_number`  | no       | `ESP32-DevKitC-32E`                            |
| `description`  | no       | a sentence displayed on the sheet card         |
| `tags`         | no       | `[wifi, bluetooth]`                            |
| `specs`        | no       | `Label: value` list, displayed as a table; labels are unrestricted |
| `links`        | no       | list of `{ title, url }` (datasheets, guides)  |

## Package

All dimensions are in millimetres, with a **top view**: `width` is horizontal,
`length` is vertical, and `x`/`y` positions are measured from the top-left corner.

```yaml
package:
  type: board          # board | module | dip | to92
  length: 54.4
  width: 27.9
  thickness: 1.6       # PCB thickness or package height
  color: "#16181d"     # solder mask (or package body), always in quotes
  marking: NE555P      # marking for a DIP or TO-92
  finish: gold         # pads: gold (ENIG) or tin (HASL)
  corner_radius: 0.8   # board corner radius
  silkscreen:          # printed text in addition to pin names
    - { text: EN, x: 7.2, y: 47.1, size: 1.0 }
    - { text: "ESP32-DevKitC V4", x: 14, y: 30, size: 1.2, side: bottom }
  holes:               # holes in addition to pins (uninstalled connector or mounting)
    - { x: 6.46, y: 40.9, drill: 1.0, pad: 1.7, square: true }
    - { x: 2.5, y: 2.5, drill: 3.2 }   # without a pad: non-plated hole
```

| Type     | 3D Model                                                                    |
|----------|-----------------------------------------------------------------------------|
| `board`  | complete PCB: FR4 core, solder mask, silkscreen, plated holes, pads, solder joints |
| `module` | like `board`, for small modules (sensors, converters)                       |
| `dip`    | DIP package: `width` = spacing between rows (7.62 for a DIP-8)              |
| `to92`   | TO-92 transistor or regulator, flat face toward the bottom of the view with long leads |

On a board, each pin receives a 1 mm plated hole and a 1.7 mm pad, with a square pad for pin 1,
and solder on the side opposite the headers.

## Pinout

```yaml
pinout:
  pitch: 2.54            # pin spacing (default: 2.54; 1.27 for to92)
  rows:
    - name: J2
      side: left         # left | right | top | bottom
      start: 4.6         # position of the first pin along the side (default: centered row)
      inset: 1.27        # distance from edge (default: 1.27; 0 for dip and to92)
      pins:
        - { n: 1, name: 3V3, type: power, description: "3.3 V output" }
        - { n: 3, name: GPIO36, silkscreen: SVP, type: analog, functions: [ADC1_CH0, SENSOR_VP] }
```

Pins in a row are listed in **physical order**: top to bottom for `left` and `right`, and
left to right for `top` and `bottom`. For a DIP package, the right-hand row therefore reads
8, 7, 6, 5.

| Key           | Purpose                                                    |
|---------------|------------------------------------------------------------|
| `n`           | displayed number (default: position in the row)            |
| `name`        | pin name in the table and diagram                          |
| `silkscreen`  | text printed beside the pin on the actual board, if different from `name` |
| `type`        | colour and filter (see below)                              |
| `functions`   | alternative functions: `[SDA, ADC2_CH0]`                   |
| `description` | detail shown on hover and in the table                     |

| Type       | Display name        |
|------------|---------------------|
| `power`    | Power               |
| `ground`   | Ground              |
| `gpio`     | Digital I/O         |
| `analog`   | Analog              |
| `pwm`      | PWM                 |
| `i2c`      | I²C                 |
| `spi`      | SPI                 |
| `uart`     | UART                |
| `control`  | Control (reset, enable, boot…) |
| `reserved` | Reserved (do not use) |
| `nc`       | No connection       |
| `other`    | Other               |

## Components (3D Model)

Each component placed on a device is either a **real model** from the KiCad 3D library,
declared in `tools/parts.yaml` and converted into `tools/parts/`, or a **simple shape**
for components that do not have a model (relay, display, terminal block, etc.).

```yaml
parts:
  - { name: ESP32 Module, model: esp32-wroom-32e, x: 13.95, y: 12.75, color: "#c8ccd2", label: "ESP32-WROOM-32E" }
  - { name: J2 Header, model: pin-header-1x19, x: 1.27, y: 27.46, side: bottom }
  - { name: Microcontroller, model: tqfp-32, x: 9, y: 26.5, rotation: 45, label: "ATMEGA328P" }
  - { name: Relay, shape: box, x: 20, y: 15, width: 15.5, length: 19, height: 15.5, color: "#1f5fc4", label: "SRD-05VDC" }
```

| Key        | Purpose                                                           |
|------------|-------------------------------------------------------------------|
| `model`    | name of a component in `tools/parts.yaml`                         |
| `shape`    | when no model exists: `box` or `cylinder`, with `width`, `length`, `height` |
| `x`, `y`   | position of the **centre** of the component                       |
| `rotation` | angle in degrees, counterclockwise in the top view                |
| `side`     | `top` (default) or `bottom`: component mounted on underside (male headers…) |
| `z`        | vertical offset in mm (rarely needed)                             |
| `color`    | colour of a simple shape and of the component in the 2D diagram   |
| `label`    | printed text on top (chips, shields)                              |

For a `dip` or `to92`, a single component represents the package and is centred on the device;
its text comes from `package.marking`.

To add a KiCad model, add its STEP file to `tools/parts.yaml`, then rerun
`python tools/build_models.py`. A manufacturer's STEP model may also be added if its
license permits redistribution.

## Equipment Catalog (New Items)

`sheets/catalog.yaml` lists commonly used equipment, whether or not it already has a sheet.
The **Name** field of a new item suggests entries from this list, and choosing a device fills in
all the other item fields. Only `id`, `name`, and `category` are required.

```yaml
devices:
  - id: l7805                     # unique; also the sheet identifier (sheets/l7805.md)
    name: L7805 Voltage Regulator # suggested name and item name
    category: Power Supply
    manufacturer: STMicroelectronics
    part_number: L7805CV          # with manufacturer: “Ref.: …” in item notes
    package: TO-220               # package
    value: 5 V                    # value
    description: 5 V, 1.5 A linear voltage regulator in TO-220.   # used as a fallback
    links: [https://www.st.com/resource/en/datasheet/l78.pdf] # datasheet
  - id: resistor-1-4w
    name: 1/4 W Resistor
    category: Resistor
    package: THT 1/4 W
    values: [10 Ω, 220 Ω, 1 kΩ, 10 kΩ]  # values suggested in the Value field
```

When a sheet uses the identifier of a device in the catalog, the item is linked to that sheet.
Every distributed sheet therefore has an entry in the catalog (verified by the tests). Links in
both the catalog and sheets are checked by `python tools/check_links.py` (the **Links** workflow,
weekly and on every change).

## YAML Pitfalls

- Put colours (`"#1d5c3a"`) and text containing `:` or `#` in quotes.
- The names `ON`, `OFF`, `YES`, and `NO` remain text in Prométhée, but other YAML tools
  interpret them as booleans. Quoting costs nothing.
- Use spaces for indentation, never tabs.

An invalid sheet does not prevent other sheets from appearing. It is reported at the top of the
**Sheets** page, with the error message.

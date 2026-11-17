---
name: Arduino Nano
category: Carte de développement
manufacturer: Arduino
part_number: A000005
description: Petite carte ATmega328P en 5 V, compatible avec le code Arduino Uno, à enficher sur plaque d'essai.
tags: [avr, microcontrôleur, 5V]

specs:
  Microcontrôleur: ATmega328P à 16 MHz
  Mémoire: 32 Ko de flash (2 Ko pour le chargeur), 2 Ko SRAM, 1 Ko EEPROM
  Alimentation: 5 V par USB, 7 à 12 V sur VIN
  Entrées-sorties: 14 numériques (6 PWM), 8 analogiques
  Courant par broche: 40 mA au plus (20 mA conseillés)
  Dimensions: 18 × 45 mm

links:
  - title: Documentation Arduino
    url: https://docs.arduino.cc/hardware/nano/
  - title: Fiche technique ATmega328P
    url: https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf

package:
  type: board
  length: 45
  width: 18
  color: "#1c4f8c"

pinout:
  pitch: 2.54
  rows:
    - name: J1
      side: left
      inset: 1.38
      start: 4.7
      pins:
        - { n: 16, name: D13, type: spi, functions: [SCK, LED], description: "LED intégrée" }
        - { n: 17, name: 3V3, type: power, description: "Sortie 3,3 V du pont USB (50 mA au plus)" }
        - { n: 18, name: AREF, type: analog, description: "Référence externe du convertisseur" }
        - { n: 19, name: A0, type: analog, functions: [D14] }
        - { n: 20, name: A1, type: analog, functions: [D15] }
        - { n: 21, name: A2, type: analog, functions: [D16] }
        - { n: 22, name: A3, type: analog, functions: [D17] }
        - { n: 23, name: A4, type: i2c, functions: [SDA, D18] }
        - { n: 24, name: A5, type: i2c, functions: [SCL, D19] }
        - { n: 25, name: A6, type: analog, description: "Entrée analogique seule" }
        - { n: 26, name: A7, type: analog, description: "Entrée analogique seule" }
        - { n: 27, name: 5V, type: power, description: "Sortie du régulateur, ou entrée 5 V régulée" }
        - { n: 28, name: RST, type: control, description: "Reset à l'état bas" }
        - { n: 29, name: GND, type: ground }
        - { n: 30, name: VIN, type: power, description: "Entrée 7 à 12 V non régulée" }
    - name: J2
      side: right
      inset: 1.38
      start: 4.7
      pins:
        - { n: 15, name: D12, type: spi, functions: [MISO] }
        - { n: 14, name: D11, type: spi, functions: [MOSI, PWM] }
        - { n: 13, name: D10, type: spi, functions: [SS, PWM] }
        - { n: 12, name: D9, type: pwm }
        - { n: 11, name: D8, type: gpio }
        - { n: 10, name: D7, type: gpio }
        - { n: 9, name: D6, type: pwm }
        - { n: 8, name: D5, type: pwm }
        - { n: 7, name: D4, type: gpio }
        - { n: 6, name: D3, type: pwm, functions: [INT1] }
        - { n: 5, name: D2, type: gpio, functions: [INT0] }
        - { n: 4, name: GND, type: ground }
        - { n: 3, name: RST, type: control, description: "Reset à l'état bas" }
        - { n: 2, name: RX0, type: uart, functions: [D0], description: "Partagée avec le port USB" }
        - { n: 1, name: TX1, type: uart, functions: [D1], description: "Partagée avec le port USB" }

# Vrais modèles 3D (sheets/models, bibliothèque KiCad), placés par leur centre.
parts:
  - { name: Connecteur mini-USB, model: models/usb-mini-b.glb, x: 9, y: 3.5, color: "#c8ccd2" }
  - { name: Barrette J1, model: models/pin-header-1x15.glb, x: 1.38, y: 22.48, side: bottom }
  - { name: Barrette J2, model: models/pin-header-1x15.glb, x: 16.62, y: 22.48, side: bottom }
  - { name: Microcontrôleur ATmega328P, model: models/tqfp-32.glb, x: 9, y: 26.5, rotation: 45, label: "ATMEGA328P" }
  - { name: Bouton reset, model: models/button-kmr2.glb, x: 9, y: 14.5, color: "#c8ccd2" }
  - { name: Quartz 16 MHz, model: models/crystal-3225.glb, x: 9, y: 34.5 }
  - { name: LED L, model: models/led-0805.glb, x: 5.6, y: 31, rotation: 90 }
  - { name: LED PWR, model: models/led-0805.glb, x: 12.4, y: 31, rotation: 90 }
  - { name: LED TX, model: models/led-0805.glb, x: 5.6, y: 35, rotation: 90 }
  - { name: LED RX, model: models/led-0805.glb, x: 12.4, y: 35, rotation: 90 }
  - { name: Condensateur, model: models/c-0805.glb, x: 6, y: 19.5, rotation: 90 }
  - { name: Condensateur, model: models/c-0805.glb, x: 12, y: 19.5, rotation: 90 }
  - { name: Résistance, model: models/r-0603.glb, x: 9, y: 39 }
  - { name: Pont USB-série FT232RL, model: models/ssop-28.glb, x: 9, y: 22, side: bottom }
  - { name: Régulateur 5 V, model: models/sot-223.glb, x: 9, y: 37, side: bottom }
---

## Présentation

Le Nano reprend le microcontrôleur de l'Uno sur une carte de 18 × 45 mm qui s'enfiche
directement sur une plaque d'essai. Les clones utilisent souvent un pont **CH340**
au lieu du FT232 : installer son pilote si le port n'apparaît pas.

## Mise en route

Dans l'IDE Arduino, choisir **Arduino Nano**, puis le processeur
**ATmega328P** ou **ATmega328P (Old Bootloader)** pour la plupart des clones.

```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);  // D13
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
```

## Bon à savoir

- **A6 et A7** sont des entrées analogiques seules (pas de `digitalRead`).
- PWM sur **D3, D5, D6, D9, D10 et D11**.
- I²C sur **A4 (SDA)** et **A5 (SCL)** ; SPI sur **D10 à D13**.
- D0 et D1 servent au téléversement : les laisser libres pendant la programmation.

## Précautions

- 200 mA au plus pour l'ensemble des broches.
- Le 3V3 vient du pont USB : il ne fournit que quelques dizaines de mA.

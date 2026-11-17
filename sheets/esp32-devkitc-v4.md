---
name: ESP32-DevKitC V4
category: Carte de développement
manufacturer: Espressif
part_number: ESP32-DevKitC-32E
description: Carte de développement ESP32 (Wi-Fi, Bluetooth), 38 broches, programmable par USB.
tags: [wifi, bluetooth, microcontrôleur, 3.3V]

specs:
  Microcontrôleur: ESP32-D0WD-V3, double cœur Xtensa LX6 à 240 MHz
  Mémoire: 520 Ko SRAM, 4 Mo de flash
  Sans fil: Wi-Fi 802.11 b/g/n, Bluetooth 4.2 et BLE
  Alimentation: 5 V par micro-USB ou broche 5V ; logique en 3,3 V
  Courant par broche: 40 mA au plus (20 mA conseillés)
  Convertisseurs: 18 voies ADC 12 bits, 2 DAC 8 bits
  Pont USB-série: CP2102N

links:
  - title: Guide de la carte (Espressif)
    url: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html
  - title: Fiche technique ESP32
    url: https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf

package:
  type: board
  length: 54.4
  width: 27.9
  thickness: 1.6
  color: "#16181d"
  finish: gold
  corner_radius: 0.8
  silkscreen:
    - { text: EN, x: 7.2, y: 47.1, size: 1.0 }
    - { text: Boot, x: 20.7, y: 47.1, size: 1.0 }

pinout:
  pitch: 2.54
  rows:
    - name: J2
      side: left
      start: 4.6
      pins:
        - { n: 1, name: 3V3, type: power, description: "Sortie du régulateur 3,3 V (600 mA au plus)" }
        - { n: 2, name: EN, type: control, description: "Activation de la puce ; reset à l'état bas" }
        - { n: 3, name: GPIO36, silkscreen: SVP, type: analog, functions: [ADC1_CH0, SENSOR_VP], description: "Entrée seule, sans résistance de tirage" }
        - { n: 4, name: GPIO39, silkscreen: SVN, type: analog, functions: [ADC1_CH3, SENSOR_VN], description: "Entrée seule, sans résistance de tirage" }
        - { n: 5, name: GPIO34, silkscreen: IO34, type: analog, functions: [ADC1_CH6], description: "Entrée seule" }
        - { n: 6, name: GPIO35, silkscreen: IO35, type: analog, functions: [ADC1_CH7], description: "Entrée seule" }
        - { n: 7, name: GPIO32, silkscreen: IO32, type: gpio, functions: [ADC1_CH4, TOUCH9, XTAL32_P] }
        - { n: 8, name: GPIO33, silkscreen: IO33, type: gpio, functions: [ADC1_CH5, TOUCH8, XTAL32_N] }
        - { n: 9, name: GPIO25, silkscreen: IO25, type: analog, functions: [DAC1, ADC2_CH8] }
        - { n: 10, name: GPIO26, silkscreen: IO26, type: analog, functions: [DAC2, ADC2_CH9] }
        - { n: 11, name: GPIO27, silkscreen: IO27, type: gpio, functions: [ADC2_CH7, TOUCH7] }
        - { n: 12, name: GPIO14, silkscreen: IO14, type: spi, functions: [HSPI_CLK, ADC2_CH6, TOUCH6], description: "Émet un signal PWM au démarrage" }
        - { n: 13, name: GPIO12, silkscreen: IO12, type: spi, functions: [HSPI_MISO, ADC2_CH5, TOUCH5], description: "Broche de configuration (MTDI) : doit être basse au démarrage" }
        - { n: 14, name: GND, type: ground }
        - { n: 15, name: GPIO13, silkscreen: IO13, type: spi, functions: [HSPI_MOSI, ADC2_CH4, TOUCH4] }
        - { n: 16, name: SD2, type: reserved, functions: [GPIO9], description: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 17, name: SD3, type: reserved, functions: [GPIO10], description: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 18, name: CMD, type: reserved, functions: [GPIO11], description: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 19, name: 5V, type: power, description: "Entrée 5 V (ou sortie du 5 V USB)" }
    - name: J3
      side: right
      start: 4.6
      pins:
        - { n: 1, name: GND, type: ground }
        - { n: 2, name: GPIO23, silkscreen: IO23, type: spi, functions: [VSPI_MOSI] }
        - { n: 3, name: GPIO22, silkscreen: IO22, type: i2c, functions: [SCL, U0RTS], description: "SCL par défaut dans Arduino" }
        - { n: 4, name: TX0, silkscreen: TXD0, type: uart, functions: [GPIO1], description: "Reliée au pont USB-série" }
        - { n: 5, name: RX0, silkscreen: RXD0, type: uart, functions: [GPIO3], description: "Reliée au pont USB-série" }
        - { n: 6, name: GPIO21, silkscreen: IO21, type: i2c, functions: [SDA], description: "SDA par défaut dans Arduino" }
        - { n: 7, name: GND, type: ground }
        - { n: 8, name: GPIO19, silkscreen: IO19, type: spi, functions: [VSPI_MISO, U0CTS] }
        - { n: 9, name: GPIO18, silkscreen: IO18, type: spi, functions: [VSPI_CLK] }
        - { n: 10, name: GPIO5, silkscreen: IO5, type: spi, functions: [VSPI_CS], description: "Broche de configuration : haute au démarrage" }
        - { n: 11, name: GPIO17, silkscreen: IO17, type: uart, functions: [U2TXD] }
        - { n: 12, name: GPIO16, silkscreen: IO16, type: uart, functions: [U2RXD] }
        - { n: 13, name: GPIO4, silkscreen: IO4, type: gpio, functions: [ADC2_CH0, TOUCH0] }
        - { n: 14, name: GPIO0, silkscreen: IO0, type: control, functions: [BOOT, ADC2_CH1, TOUCH1], description: "Bouton BOOT : basse au démarrage = mode programmation" }
        - { n: 15, name: GPIO2, silkscreen: IO2, type: gpio, functions: [ADC2_CH2, TOUCH2], description: "Broche de configuration : basse ou flottante au démarrage" }
        - { n: 16, name: GPIO15, silkscreen: IO15, type: spi, functions: [HSPI_CS, ADC2_CH3, TOUCH3], description: "Broche de configuration (MTDO)" }
        - { n: 17, name: SD1, type: reserved, functions: [GPIO8], description: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 18, name: SD0, type: reserved, functions: [GPIO7], description: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 19, name: CLK, type: reserved, functions: [GPIO6], description: "Reliée à la flash SPI : ne pas utiliser" }

# Pièces du modèle 3D (tools/parts.yaml), placées par leur centre.
parts:
  - { name: Module ESP32-WROOM-32E, model: esp32-wroom-32e, x: 13.95, y: 12.75, color: "#c8ccd2", label: "ESP32-WROOM-32E" }
  - { name: Barrette J2, model: pin-header-1x19, x: 1.27, y: 27.46, side: bottom }
  - { name: Barrette J3, model: pin-header-1x19, x: 26.63, y: 27.46, side: bottom }
  - { name: Connecteur micro-USB, model: usb-micro-b, x: 13.95, y: 52.2, color: "#c8ccd2" }
  - { name: Pont USB-série CP2102N, model: qfn-28-5x5, x: 19.5, y: 38 }
  - { name: Régulateur AMS1117, model: sot-223, x: 10.5, y: 40.5 }
  - { name: Bouton EN, model: button-kmr2, x: 7.2, y: 50.3, rotation: 90, color: "#c8ccd2" }
  - { name: Bouton BOOT, model: button-kmr2, x: 20.7, y: 50.3, rotation: 90, color: "#c8ccd2" }
  - { name: LED d'alimentation, model: led-0603, x: 21.5, y: 31.5 }
  - { name: Résistance de la LED, model: r-0603, x: 21.5, y: 33.5 }
  - { name: Condensateur, model: c-0603, x: 13.95, y: 30.5 }
  - { name: Condensateur, model: c-0603, x: 15.5, y: 38, rotation: 90 }
  - { name: Condensateur d'entrée, model: c-0805, x: 11.2, y: 45.6 }
  - { name: Condensateur de sortie, model: c-0805, x: 10.5, y: 35.6 }
---

## Présentation

La DevKitC est la carte de référence d'Espressif pour l'ESP32. Elle porte un module
ESP32-WROOM-32E (antenne gravée en haut), un régulateur 3,3 V, un pont USB-série et
deux boutons : **EN** (reset) et **BOOT** (GPIO0, mode programmation).

## Mise en route (Arduino IDE)

1. Ajouter l'URL des cartes ESP32 dans *Préférences* :
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
2. Installer **esp32 by Espressif Systems** dans le gestionnaire de cartes.
3. Choisir la carte **ESP32 Dev Module** et le port série.

```cpp
const int LED = 2;  // LED externe sur GPIO2 (pas de LED sur la DevKitC officielle)

void setup() {
  pinMode(LED, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  digitalWrite(LED, !digitalRead(LED));
  Serial.println(analogRead(34));  // lecture ADC1, compatible avec le Wi-Fi
  delay(500);
}
```

## Bon à savoir

- Les entrées **ADC2** ne fonctionnent pas quand le Wi-Fi est actif : préférer l'ADC1 (GPIO32 à 39).
- **GPIO34 à 39** sont des entrées seules, sans résistance de tirage interne.
- **GPIO6 à 11** sont reliées à la flash : ne jamais les utiliser.
- Broches de configuration au démarrage : GPIO0, 2, 5, 12 et 15. Éviter d'y brancher
  un circuit qui force leur niveau pendant le reset.
- Si le téléversement échoue avec « Failed to connect », maintenir **BOOT** appuyé au début du transfert.

## Précautions

- Logique en **3,3 V** : les entrées ne tolèrent pas le 5 V.
- Ne pas alimenter par USB et par la broche 5V en même temps sans diode.

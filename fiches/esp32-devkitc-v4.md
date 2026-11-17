---
nom: ESP32-DevKitC V4
categorie: Carte de développement
fabricant: Espressif
reference: ESP32-DevKitC-32E
description: Carte de développement ESP32 (Wi-Fi, Bluetooth), 38 broches, programmable par USB.
tags: [wifi, bluetooth, microcontrôleur, 3.3V]

caracteristiques:
  Microcontrôleur: ESP32-D0WD-V3, double cœur Xtensa LX6 à 240 MHz
  Mémoire: 520 Ko SRAM, 4 Mo de flash
  Sans fil: Wi-Fi 802.11 b/g/n, Bluetooth 4.2 et BLE
  Alimentation: 5 V par micro-USB ou broche 5V ; logique en 3,3 V
  Courant par broche: 40 mA au plus (20 mA conseillés)
  Convertisseurs: 18 voies ADC 12 bits, 2 DAC 8 bits
  Pont USB-série: CP2102N

liens:
  - titre: Guide de la carte (Espressif)
    url: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html
  - titre: Fiche technique ESP32
    url: https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf

boitier:
  type: carte
  longueur: 54.4
  largeur: 27.9
  epaisseur: 1.6
  couleur: "#16181d"

brochage:
  pas: 2.54
  rangees:
    - nom: J2
      cote: gauche
      debut: 4.6
      broches:
        - { n: 1, nom: 3V3, type: alim, desc: "Sortie du régulateur 3,3 V (600 mA au plus)" }
        - { n: 2, nom: EN, type: controle, desc: "Activation de la puce ; reset à l'état bas" }
        - { n: 3, nom: GPIO36, type: analogique, fonctions: [ADC1_CH0, SENSOR_VP], desc: "Entrée seule, sans résistance de tirage" }
        - { n: 4, nom: GPIO39, type: analogique, fonctions: [ADC1_CH3, SENSOR_VN], desc: "Entrée seule, sans résistance de tirage" }
        - { n: 5, nom: GPIO34, type: analogique, fonctions: [ADC1_CH6], desc: "Entrée seule" }
        - { n: 6, nom: GPIO35, type: analogique, fonctions: [ADC1_CH7], desc: "Entrée seule" }
        - { n: 7, nom: GPIO32, type: gpio, fonctions: [ADC1_CH4, TOUCH9, XTAL32_P] }
        - { n: 8, nom: GPIO33, type: gpio, fonctions: [ADC1_CH5, TOUCH8, XTAL32_N] }
        - { n: 9, nom: GPIO25, type: analogique, fonctions: [DAC1, ADC2_CH8] }
        - { n: 10, nom: GPIO26, type: analogique, fonctions: [DAC2, ADC2_CH9] }
        - { n: 11, nom: GPIO27, type: gpio, fonctions: [ADC2_CH7, TOUCH7] }
        - { n: 12, nom: GPIO14, type: spi, fonctions: [HSPI_CLK, ADC2_CH6, TOUCH6], desc: "Émet un signal PWM au démarrage" }
        - { n: 13, nom: GPIO12, type: spi, fonctions: [HSPI_MISO, ADC2_CH5, TOUCH5], desc: "Broche de configuration (MTDI) : doit être basse au démarrage" }
        - { n: 14, nom: GND, type: masse }
        - { n: 15, nom: GPIO13, type: spi, fonctions: [HSPI_MOSI, ADC2_CH4, TOUCH4] }
        - { n: 16, nom: SD2, type: reserve, fonctions: [GPIO9], desc: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 17, nom: SD3, type: reserve, fonctions: [GPIO10], desc: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 18, nom: CMD, type: reserve, fonctions: [GPIO11], desc: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 19, nom: 5V, type: alim, desc: "Entrée 5 V (ou sortie du 5 V USB)" }
    - nom: J3
      cote: droite
      debut: 4.6
      broches:
        - { n: 1, nom: GND, type: masse }
        - { n: 2, nom: GPIO23, type: spi, fonctions: [VSPI_MOSI] }
        - { n: 3, nom: GPIO22, type: i2c, fonctions: [SCL, U0RTS], desc: "SCL par défaut dans Arduino" }
        - { n: 4, nom: TX0, type: uart, fonctions: [GPIO1], desc: "Reliée au pont USB-série" }
        - { n: 5, nom: RX0, type: uart, fonctions: [GPIO3], desc: "Reliée au pont USB-série" }
        - { n: 6, nom: GPIO21, type: i2c, fonctions: [SDA], desc: "SDA par défaut dans Arduino" }
        - { n: 7, nom: GND, type: masse }
        - { n: 8, nom: GPIO19, type: spi, fonctions: [VSPI_MISO, U0CTS] }
        - { n: 9, nom: GPIO18, type: spi, fonctions: [VSPI_CLK] }
        - { n: 10, nom: GPIO5, type: spi, fonctions: [VSPI_CS], desc: "Broche de configuration : haute au démarrage" }
        - { n: 11, nom: GPIO17, type: uart, fonctions: [U2TXD] }
        - { n: 12, nom: GPIO16, type: uart, fonctions: [U2RXD] }
        - { n: 13, nom: GPIO4, type: gpio, fonctions: [ADC2_CH0, TOUCH0] }
        - { n: 14, nom: GPIO0, type: controle, fonctions: [BOOT, ADC2_CH1, TOUCH1], desc: "Bouton BOOT : basse au démarrage = mode programmation" }
        - { n: 15, nom: GPIO2, type: gpio, fonctions: [ADC2_CH2, TOUCH2], desc: "Broche de configuration : basse ou flottante au démarrage" }
        - { n: 16, nom: GPIO15, type: spi, fonctions: [HSPI_CS, ADC2_CH3, TOUCH3], desc: "Broche de configuration (MTDO)" }
        - { n: 17, nom: SD1, type: reserve, fonctions: [GPIO8], desc: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 18, nom: SD0, type: reserve, fonctions: [GPIO7], desc: "Reliée à la flash SPI : ne pas utiliser" }
        - { n: 19, nom: CLK, type: reserve, fonctions: [GPIO6], desc: "Reliée à la flash SPI : ne pas utiliser" }

composants:
  - { nom: Module ESP32-WROOM-32E, x: 13.95, y: 12.2, largeur: 18, longueur: 25.5, hauteur: 3.1, couleur: "#b9bec6", texte: "ESP32-WROOM-32E" }
  - { nom: Pont USB-série CP2102N, x: 13.95, y: 38.5, largeur: 4, longueur: 4, hauteur: 0.9, couleur: "#202227", texte: "CP2102N" }
  - { nom: Régulateur AMS1117, x: 13.95, y: 31.5, largeur: 6.5, longueur: 3.5, hauteur: 1.6, couleur: "#202227", texte: "AMS1117" }
  - { nom: Bouton EN, x: 6.5, y: 49.5, largeur: 3.5, longueur: 4.5, hauteur: 1.8, couleur: "#d9dbe0" }
  - { nom: Bouton BOOT, x: 21.4, y: 49.5, largeur: 3.5, longueur: 4.5, hauteur: 1.8, couleur: "#d9dbe0" }
  - { nom: Connecteur micro-USB, x: 13.95, y: 52.6, largeur: 7.6, longueur: 5.4, hauteur: 2.7, couleur: "#c8ccd2" }
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

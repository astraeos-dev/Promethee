---
nom: Arduino Nano
categorie: Carte de développement
fabricant: Arduino
reference: A000005
description: Petite carte ATmega328P en 5 V, compatible avec le code Arduino Uno, à enficher sur plaque d'essai.
tags: [avr, microcontrôleur, 5V]

caracteristiques:
  Microcontrôleur: ATmega328P à 16 MHz
  Mémoire: 32 Ko de flash (2 Ko pour le chargeur), 2 Ko SRAM, 1 Ko EEPROM
  Alimentation: 5 V par USB, 7 à 12 V sur VIN
  Entrées-sorties: 14 numériques (6 PWM), 8 analogiques
  Courant par broche: 40 mA au plus (20 mA conseillés)
  Dimensions: 18 × 45 mm

liens:
  - titre: Documentation Arduino
    url: https://docs.arduino.cc/hardware/nano/
  - titre: Fiche technique ATmega328P
    url: https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf

boitier:
  type: carte
  longueur: 45
  largeur: 18
  couleur: "#1c4f8c"

brochage:
  pas: 2.54
  rangees:
    - nom: J1
      cote: gauche
      retrait: 1.38
      debut: 4.7
      broches:
        - { n: 16, nom: D13, type: spi, fonctions: [SCK, LED], desc: "LED intégrée" }
        - { n: 17, nom: 3V3, type: alim, desc: "Sortie 3,3 V du pont USB (50 mA au plus)" }
        - { n: 18, nom: AREF, type: analogique, desc: "Référence externe du convertisseur" }
        - { n: 19, nom: A0, type: analogique, fonctions: [D14] }
        - { n: 20, nom: A1, type: analogique, fonctions: [D15] }
        - { n: 21, nom: A2, type: analogique, fonctions: [D16] }
        - { n: 22, nom: A3, type: analogique, fonctions: [D17] }
        - { n: 23, nom: A4, type: i2c, fonctions: [SDA, D18] }
        - { n: 24, nom: A5, type: i2c, fonctions: [SCL, D19] }
        - { n: 25, nom: A6, type: analogique, desc: "Entrée analogique seule" }
        - { n: 26, nom: A7, type: analogique, desc: "Entrée analogique seule" }
        - { n: 27, nom: 5V, type: alim, desc: "Sortie du régulateur, ou entrée 5 V régulée" }
        - { n: 28, nom: RST, type: controle, desc: "Reset à l'état bas" }
        - { n: 29, nom: GND, type: masse }
        - { n: 30, nom: VIN, type: alim, desc: "Entrée 7 à 12 V non régulée" }
    - nom: J2
      cote: droite
      retrait: 1.38
      debut: 4.7
      broches:
        - { n: 15, nom: D12, type: spi, fonctions: [MISO] }
        - { n: 14, nom: D11, type: spi, fonctions: [MOSI, PWM] }
        - { n: 13, nom: D10, type: spi, fonctions: [SS, PWM] }
        - { n: 12, nom: D9, type: pwm }
        - { n: 11, nom: D8, type: gpio }
        - { n: 10, nom: D7, type: gpio }
        - { n: 9, nom: D6, type: pwm }
        - { n: 8, nom: D5, type: pwm }
        - { n: 7, nom: D4, type: gpio }
        - { n: 6, nom: D3, type: pwm, fonctions: [INT1] }
        - { n: 5, nom: D2, type: gpio, fonctions: [INT0] }
        - { n: 4, nom: GND, type: masse }
        - { n: 3, nom: RST, type: controle, desc: "Reset à l'état bas" }
        - { n: 2, nom: RX0, type: uart, fonctions: [D0], desc: "Partagée avec le port USB" }
        - { n: 1, nom: TX1, type: uart, fonctions: [D1], desc: "Partagée avec le port USB" }

composants:
  - { nom: Connecteur mini-USB, x: 9, y: 2.6, largeur: 7.7, longueur: 7.2, hauteur: 3.9, couleur: "#c8ccd2" }
  - { nom: Microcontrôleur ATmega328P, x: 9, y: 25, largeur: 7, longueur: 7, hauteur: 1.2, couleur: "#202227", texte: "ATMEGA328P" }
  - { nom: Bouton reset, x: 9, y: 13.5, largeur: 3.5, longueur: 6, hauteur: 2.2, couleur: "#d9dbe0" }
  - { nom: Quartz 16 MHz, x: 9, y: 34, largeur: 3.2, longueur: 5, hauteur: 1, couleur: "#c8ccd2" }
  - { nom: Connecteur ICSP, x: 9, y: 41.5, largeur: 7.6, longueur: 5.1, hauteur: 1, couleur: "#202227" }
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

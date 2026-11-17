---
name: Ethernet Shield ENC28J60
category: Carte de développement
manufacturer: AZ-Delivery
part_number: ENC28J60
description: Module Ethernet SPI avec contrôleur ENC28J60, connecteur RJ45 et embase 10 broches.
tags: [ethernet, réseau, spi, arduino, rj45]

specs:
  Contrôleur: Microchip ENC28J60
  Interface: SPI
  Réseau: Ethernet 10 Mbit/s, 802.3
  Mémoire tampon: 8 Ko dans le contrôleur
  Alimentation: 5 V sur la broche VCC
  Connecteur: RJ45
  Broches de commande: 10 broches
  Broches SPI: SCK, SI, SO et CS
  Dimensions: 50,7 × 32,7 × 17,3 mm

links:
  - title: Page AZ-Delivery
    url: https://www.az-delivery.de/fr/products/enc28j60-netzwerkmodul
  - title: Datasheet ENC28J60
    url: https://ww1.microchip.com/downloads/en/DeviceDoc/39662e.pdf
  - title: Bibliothèque EthernetENC
    url: https://github.com/jandrassy/EthernetENC

package:
  type: board
  length: 50.7
  width: 32.7
  thickness: 1.6
  color: "#1d6b3b"
  finish: gold
  corner_radius: 0.8
  silkscreen:
    - { text: ENC28J60, x: 16.35, y: 25.5, size: 1.2 }

pinout:
  pitch: 2.54
  rows:
    - name: J1
      side: bottom
      start: 4.92
      pins:
        - { n: 1, name: CLKOUT, type: control, description: "Sortie d'horloge configurable ; laisser non connecté si elle n'est pas nécessaire" }
        - { n: 2, name: WOL, type: control, description: "Entrée Wake-on-LAN" }
        - { n: 3, name: SCK, type: spi, functions: [SPI_CLK], description: "Horloge SPI" }
        - { n: 4, name: SI, type: spi, functions: [SPI_MOSI], description: "Entrée données SPI" }
        - { n: 5, name: CS, type: spi, functions: [SPI_SS], description: "Sélection de la puce SPI" }
        - { n: 6, name: VCC, type: power, description: "Alimentation 5 V" }
        - { n: 7, name: INT, type: control, description: "Sortie d'interruption" }
        - { n: 8, name: SO, type: spi, functions: [SPI_MISO], description: "Sortie données SPI" }
        - { n: 9, name: RESET, type: control, description: "Réinitialisation active à l'état bas" }
        - { n: 10, name: GND, type: ground, description: "Masse" }

parts:
  - { name: Contrôleur ENC28J60, model: ssop-28, x: 16.35, y: 19.5, rotation: 0, label: "ENC28J60" }
  - { name: Embase J1, model: pin-header-1x10, x: 16.35, y: 46.8, rotation: 90, side: bottom }
  - { name: Cristal, model: crystal-3225, x: 7.5, y: 19.5, rotation: 90 }
  - { name: Transformateur Ethernet, shape: box, x: 25.5, y: 10.5, width: 12, length: 15, height: 10, color: "#cfc89d", label: "HR" }
  - { name: Connecteur RJ45, shape: box, x: 25.5, y: 36.5, width: 15, length: 11, height: 13, color: "#d7dbe0", label: "RJ45" }
  - { name: LED verte, model: led-0603, x: 27.5, y: 28.5 }
  - { name: LED jaune, model: led-0603, x: 30.5, y: 28.5 }
---

## Présentation

Le module ENC28J60 ajoute une liaison Ethernet filaire à un microcontrôleur via le bus SPI.
Il offre un débit théorique de 10 Mbit/s et dispose de son propre tampon mémoire. Un câble
Ethernet standard permet de relier la carte à un routeur ou à un commutateur.

## Câblage

| Module | Arduino Uno/Nano | ESP32 |
|--------|-------------------|-------|
| VCC | 5 V | 5 V* |
| GND | GND | GND |
| SCK | D13 | GPIO18 |
| SI | D11 | GPIO23 |
| SO | D12 | GPIO19 |
| CS | D10 | GPIO5 |
| RESET | D8 ou 3V3 | 3V3 |
| INT | D2 | GPIO4 |

\* Vérifier que la version du module accepte l'alimentation 5 V ; la logique SPI doit être compatible
avec les niveaux du microcontrôleur.

## Utilisation

Installer la bibliothèque **EthernetENC** avec le gestionnaire de bibliothèques Arduino, puis
charger l'exemple `EthernetENC` ou adapter le sketch ci-dessous :

```cpp
#include <SPI.h>
#include <EthernetENC.h>

byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};

void setup() {
  Serial.begin(115200);

  Ethernet.init(10);  // broche CS
  if (Ethernet.begin(mac)) {
    Serial.print("Adresse IP : ");
    Serial.println(Ethernet.localIP());
  } else {
    Serial.println("Obtention d'une adresse IP impossible");
  }
}

void loop() {
  Ethernet.maintain();
}
```

## Bon à savoir

- Le module utilise le SPI matériel sur les broches indiquées par la carte.
- Les broches **CLKOUT** et **WOL** ne sont pas utilisées dans la plupart des applications.
- Préférer une adresse MAC unique par appareil sur le réseau local.

## Précautions

- Alimenter le module en **5 V** sur VCC et respecter les niveaux logiques du contrôleur.
- Ne pas relier plusieurs sorties CS sur la même broche SPI.
- Un câble Ethernet trop long ou une polarité incorrecte ne sont pas détectés par le contrôleur ;
  utiliser un câble conforme pour le test.

---
nom: Module BME280
categorie: Capteur
fabricant: Bosch Sensortec
reference: GY-BME280
description: Capteur de température, d'humidité et de pression sur petit module I²C à 4 broches.
tags: [capteur, i2c, météo, 3.3V]

caracteristiques:
  Mesures: température, humidité relative, pression atmosphérique
  Précision: ±1 °C, ±3 % HR, ±1 hPa
  Interface: I²C (adresse 0x76, ou 0x77 selon le module)
  Alimentation: 3,3 V (les modules avec régulateur acceptent 5 V)
  Consommation: 3,6 µA à une mesure par seconde

liens:
  - titre: Fiche technique BME280
    url: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf
  - titre: Bibliothèque Adafruit BME280
    url: https://github.com/adafruit/Adafruit_BME280_Library

boitier:
  type: module
  longueur: 13
  largeur: 10.5
  couleur: "#5b2a86"

brochage:
  rangees:
    - nom: J1
      cote: haut
      broches:
        - { n: 1, nom: VIN, type: alim, desc: "3,3 V (5 V seulement si le module a un régulateur)" }
        - { n: 2, nom: GND, type: masse }
        - { n: 3, nom: SCL, type: i2c, desc: "Horloge I²C" }
        - { n: 4, nom: SDA, type: i2c, desc: "Données I²C" }

composants:
  - { nom: Capteur BME280, x: 5.25, y: 8.5, largeur: 2.5, longueur: 2.5, hauteur: 0.93, couleur: "#c8ccd2" }
  - { nom: Résistances de tirage, x: 8.6, y: 8.5, largeur: 1, longueur: 2, hauteur: 0.45, couleur: "#202227" }
---

## Présentation

Le BME280 mesure la température, l'humidité et la pression. Ne pas le confondre avec
le **BMP280**, sans humidité : la puce du BME280 est carrée, celle du BMP280 rectangulaire.

## Câblage

| Module | ESP32   | Arduino Nano |
|--------|---------|--------------|
| VIN    | 3V3     | 3V3 ou 5V*   |
| GND    | GND     | GND          |
| SCL    | GPIO22  | A5           |
| SDA    | GPIO21  | A4           |

\* 5 V seulement pour un module avec régulateur et adaptateur de niveau.

## Utilisation

```cpp
#include <Wire.h>
#include <Adafruit_BME280.h>

Adafruit_BME280 bme;

void setup() {
  Serial.begin(115200);
  if (!bme.begin(0x76)) {  // essayer 0x77 si rien ne répond
    Serial.println("BME280 introuvable");
    while (true) delay(10);
  }
}

void loop() {
  Serial.printf("%.1f °C  %.0f %%  %.1f hPa\n",
                bme.readTemperature(), bme.readHumidity(), bme.readPressure() / 100.0);
  delay(2000);
}
```

## Précautions

- L'auto-échauffement fausse la température en mesure continue : préférer le mode forcé.

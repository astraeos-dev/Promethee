---
name: Module BME280
category: Capteur
manufacturer: Bosch Sensortec
part_number: GY-BME280
description: Capteur de température, d'humidité et de pression sur petit module I²C à 4 broches.
tags: [capteur, i2c, météo, 3.3V]

specs:
  Mesures: température, humidité relative, pression atmosphérique
  Précision: ±1 °C, ±3 % HR, ±1 hPa
  Interface: I²C (adresse 0x76, ou 0x77 selon le module)
  Alimentation: 3,3 V (les modules avec régulateur acceptent 5 V)
  Consommation: 3,6 µA à une mesure par seconde

links:
  - title: Fiche technique BME280
    url: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf
  - title: Bibliothèque Adafruit BME280
    url: https://github.com/adafruit/Adafruit_BME280_Library

package:
  type: module
  length: 13
  width: 10.5
  color: "#5b2a86"
  finish: tin
  corner_radius: 0.4

pinout:
  rows:
    - name: J1
      side: top
      pins:
        - { n: 1, name: VIN, type: power, description: "3,3 V (5 V seulement si le module a un régulateur)" }
        - { n: 2, name: GND, type: ground }
        - { n: 3, name: SCL, type: i2c, description: "Horloge I²C" }
        - { n: 4, name: SDA, type: i2c, description: "Données I²C" }

# Pièces du modèle 3D (tools/parts.yaml), placées par leur centre.
parts:
  - { name: Barrette, model: pin-header-1x04, x: 5.25, y: 1.27, rotation: 90, side: bottom }
  - { name: Capteur BME280, model: bosch-lga-8-2.5x2.5, x: 5.25, y: 8.8, color: "#c8ccd2" }
  - { name: Régulateur 3,3 V, model: sot-23-5, x: 8.3, y: 7.4 }
  - { name: Résistance de tirage SDA, model: r-0603, x: 2.9, y: 6.6, rotation: 90 }
  - { name: Résistance de tirage SCL, model: r-0603, x: 2.9, y: 9.2, rotation: 90 }
  - { name: Condensateur, model: c-0603, x: 8.6, y: 10.3, rotation: 90 }
  - { name: Condensateur, model: c-0603, x: 8.6, y: 12.0, rotation: 90 }
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

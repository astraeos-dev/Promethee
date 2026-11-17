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

pinout:
  rows:
    - name: J1
      side: top
      pins:
        - { n: 1, name: VIN, type: power, description: "3,3 V (5 V seulement si le module a un régulateur)" }
        - { n: 2, name: GND, type: ground }
        - { n: 3, name: SCL, type: i2c, description: "Horloge I²C" }
        - { n: 4, name: SDA, type: i2c, description: "Données I²C" }

components:
  - { name: Capteur BME280, x: 5.25, y: 8.5, width: 2.5, length: 2.5, height: 0.93, color: "#c8ccd2" }
  - { name: Résistances de tirage, x: 8.6, y: 8.5, width: 1, length: 2, height: 0.45, color: "#202227" }
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

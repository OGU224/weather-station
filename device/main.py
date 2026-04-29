"""Point d entree M5Stack Core2 (MicroPython/UIFlow).
Boucle principale :
  1. Sync depuis BigQuery au demarrage (afficher dernieres valeurs connues)
  2. Lire capteurs (ENVIII, air quality, PIR)
  3. POST donnees au middleware Flask
  4. GET meteo depuis le middleware
  5. Mettre a jour l affichage (ecrans navigables via boutons A/B/C)
  6. Si presence detectee + cooldown ecoule -> annonce vocale
  7. Sleep 60s -> reboucle
"""
"""
M5Stack Core2 — Code principal.
À copier dans UIFlow pour exécuter sur le device.

Capteurs:
- ENVIII (Port A) : température + humidité
- PIR (Port C) : détection de mouvement

Envoie les données au middleware Flask toutes les 60 secondes.
"""

from m5stack import *
from m5ui import *
from uiflow import *
import unit
import urequests
import ujson

env3 = unit.get(unit.ENV3, unit.PORTA)
pir = unit.get(unit.PIR, unit.PORTC)

# === CHANGE CETTE IP PAR CELLE DE TON PC ===
API_URL = "http://192.168.1.23:5000"

lcd.clear()
lcd.font(lcd.FONT_DejaVu24)
lcd.print("Demarrage...", 20, 100, 0xFFFFFF)

while True:
    temp = round(env3.temperature, 1)
    hum = round(env3.humidity, 1)
    motion = pir.state

    lcd.clear()
    lcd.font(lcd.FONT_DejaVu18)
    lcd.print("Temp:   " + str(temp) + " C", 20, 30, 0x00FF00)
    lcd.print("Hum:    " + str(hum) + " %", 20, 60, 0x00BFFF)
    lcd.print("Motion: " + str(motion), 20, 90, 0xFF5500)

    try:
        data = ujson.dumps({
            "temperature_c": temp,
            "humidity_pct": hum,
            "air_quality_index": 0,
            "motion_detected": motion
        })
        resp = urequests.post(
            API_URL + "/api/sensors/reading",
            headers={"Content-Type": "application/json"},
            data=data
        )
        lcd.print("Envoi: OK (" + str(resp.status_code) + ")", 20, 130, 0x00FF00)
        resp.close()
    except Exception as e:
        lcd.print("Envoi: ERREUR", 20, 130, 0xFF0000)
        lcd.print(str(e)[:30], 20, 160, 0xFF0000)

    wait(60)
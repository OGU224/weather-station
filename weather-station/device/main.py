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

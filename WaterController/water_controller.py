"""
Sistema de Control de Bomba y Válvula para Raspberry Pi Zero 2 W
Controla una bomba eléctrica (GPIO 15) y una válvula eléctrica (GPIO 29)
con pausas programadas para evitar sobrecalentamiento de la bomba.
"""

import RPi.GPIO as GPIO
import time
import signal
import sys

# Configuración de pines GPIO
PIN_BOMBA = 15      # GPIO 15 - Bomba eléctrica
PIN_VALVULA = 29    # GPIO 29 - Válvula eléctrica
# Alimentación: Pin 1 (3.3V o 5V según tu circuito)
# Ground: Pin 6

# Tiempos de operación (en segundos)
TIEMPO_BOMBA_ON = 30      # Tiempo que la bomba está encendida
TIEMPO_BOMBA_OFF = 10     # Tiempo de pausa para evitar sobrecalentamiento
TIEMPO_VALVULA_ON = 40    # Tiempo que la válvula está abierta


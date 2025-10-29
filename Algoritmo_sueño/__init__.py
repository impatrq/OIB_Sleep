# Smart Bed Controller Package
"""
Sistema de control inteligente para cama.
Incluye detección de sueño, control térmico y monitoreo de presencia.
"""

__version__ = "1.0.0"
__author__ = "Smart Bed Team"

# Importaciones principales con la nueva estructura
from src.core.smart_bed_controller import SmartBedController
from src.core.presence_detector import BedPresenceDetector
from src.core.analyzer import detect_sleep_onset
from src.sensors.drivers.MAX30102 import MAX30102
from src.sensors.drivers.HTU21D import HTU21D
from src.sensors.drivers.MMA import MMA8452Q

# Exportar las clases principales
__all__ = [
    'SmartBedController',
    'BedPresenceDetector', 
    'detect_sleep_onset',
    'MAX30102',
    'HTU21D',
    'MMA8452Q'
]
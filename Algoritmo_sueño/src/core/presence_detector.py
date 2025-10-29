#!/usr/bin/env python3
"""
Detector de Presencia para Cama Inteligente
Sistema multi-sensor para detectar si hay alguien en la cama
Combina: temperatura, actividad, HR y patrones temporales
"""

import time
import numpy as np
from ..config import bed_config

class BedPresenceDetector:
    def __init__(self):
        """
        Inicializar detector de presencia en la cama
        """
        # Estado de presencia
        self.bed_occupied = False
        self.presence_confidence = 0.0
        self.presence_history = []
        self.presence_start_time = None
        
        # Valores baseline para comparación
        self.baseline_temperature = None
        self.baseline_activity = None
        
        # Configuración de umbrales (desde bed_config)
        self.confidence_threshold_enter = getattr(bed_config, 'PRESENCE_CONFIDENCE_THRESHOLD_ENTER', 60)
        self.confidence_threshold_exit = getattr(bed_config, 'PRESENCE_CONFIDENCE_THRESHOLD_EXIT', 20)
        self.thermal_threshold = getattr(bed_config, 'PRESENCE_THERMAL_THRESHOLD', 1.5)
        self.activity_threshold = getattr(bed_config, 'PRESENCE_ACTIVITY_THRESHOLD', 0.001)
        self.hr_min = getattr(bed_config, 'PRESENCE_HR_MIN', 40)
        self.hr_max = getattr(bed_config, 'PRESENCE_HR_MAX', 150)
        self.history_size = getattr(bed_config, 'PRESENCE_HISTORY_SIZE', 30)
        self.confirmation_time = getattr(bed_config, 'PRESENCE_CONFIRMATION_TIME', 15)
        
        print("✅ Detector de presencia inicializado")
        print(f"   🎯 Umbral entrada: {self.confidence_threshold_enter}%")
        print(f"   🎯 Umbral salida: {self.confidence_threshold_exit}%")
        print(f"   🌡️ Umbral térmico: +{self.thermal_threshold}°C")
        print(f"   🏃 Umbral actividad: {self.activity_threshold}")
        print(f"   ❤️ Rango HR: {self.hr_min}-{self.hr_max} BPM")

    def detect_presence(self, sensor_data):
        """
        Detectar presencia en la cama usando múltiples sensores
        
        Args:
            sensor_data: Diccionario con datos de sensores:
                - bed_temperature: Temperatura actual de la cama
                - activity: Nivel de actividad del acelerómetro
                - heart_rate: Frecuencia cardíaca actual
                - hr_valid: True si HR es válida
                - finger_present: True si hay contacto con MAX30102
        
        Returns:
            dict: Información de presencia y confianza
        """
        current_time = time.time()
        presence_indicators = {}
        confidence_score = 0.0
        
        # Extraer datos de sensores
        bed_temp = sensor_data.get('bed_temperature', 22.0)
        activity = sensor_data.get('activity', 0.0)
        heart_rate = sensor_data.get('heart_rate', 60)
        hr_valid = sensor_data.get('hr_valid', False)
        finger_present = sensor_data.get('finger_present', False)
        
        # Establecer baseline de temperatura si es la primera vez
        if self.baseline_temperature is None:
            self.baseline_temperature = bed_temp
        
        # 1. 🌡️ INDICADOR TÉRMICO - Temperatura de cama elevada
        temp_elevation = bed_temp - self.baseline_temperature
        if temp_elevation > self.thermal_threshold:
            presence_indicators['thermal'] = True
            confidence_score += 30
            if temp_elevation > self.thermal_threshold * 2:  # Bonus por elevación alta
                confidence_score += 10
        else:
            presence_indicators['thermal'] = False
        
        # 2. 🏃 INDICADOR DE ACTIVIDAD - Movimiento detectado
        if activity > self.activity_threshold:
            presence_indicators['movement'] = True
            # Escalar puntuación según nivel de actividad
            activity_score = min(25, int(activity * 25 / 0.1))  # Máximo 25 puntos
            confidence_score += activity_score
        else:
            presence_indicators['movement'] = False
        
        # 3. ❤️ INDICADOR CARDIOVASCULAR - HR válida
        if hr_valid and self.hr_min <= heart_rate <= self.hr_max:
            presence_indicators['heart_rate'] = True
            confidence_score += 35
            # Bonus por HR en rango óptimo de sueño
            if 50 <= heart_rate <= 80:
                confidence_score += 5
        else:
            presence_indicators['heart_rate'] = False
        
        # 4. 👆 INDICADOR DE CONTACTO - Dedo en sensor
        if finger_present:
            presence_indicators['contact'] = True
            confidence_score += 20
        else:
            presence_indicators['contact'] = False
        
        # 5. ⏰ INDICADOR TEMPORAL - Consistencia en el tiempo
        self.presence_history.append(confidence_score)
        if len(self.presence_history) > self.history_size:
            self.presence_history.pop(0)
        
        # Calcular confianza promedio en ventana temporal
        if len(self.presence_history) >= 5:
            avg_confidence = sum(self.presence_history[-5:]) / 5
            if avg_confidence > 50:  # 50% de confianza sostenida
                presence_indicators['temporal'] = True
                confidence_score += 10
            else:
                presence_indicators['temporal'] = False
        
        # DECISIÓN FINAL DE PRESENCIA
        self.presence_confidence = min(confidence_score, 100)
        
        # Aplicar histéresis para evitar falsas detecciones
        presence_changed = self._update_presence_state(current_time)
        
        return {
            'occupied': self.bed_occupied,
            'confidence': self.presence_confidence,
            'indicators': presence_indicators,
            'time_occupied': self._get_time_occupied(current_time),
            'temp_elevation': temp_elevation,
            'presence_changed': presence_changed
        }

    def _update_presence_state(self, current_time):
        """
        Actualizar estado de presencia con histéresis
        
        Returns:
            bool: True si hubo cambio de estado
        """
        presence_changed = False
        
        # Entrada a la cama: alta confianza
        if not self.bed_occupied and self.presence_confidence >= self.confidence_threshold_enter:
            self.bed_occupied = True
            self.presence_start_time = current_time
            presence_changed = True
            print("🛏️ ✅ PRESENCIA DETECTADA en la cama")
            print(f"   📊 Confianza: {self.presence_confidence:.0f}%")
            
        # Salida de la cama: baja confianza sostenida
        elif self.bed_occupied and self.presence_confidence <= self.confidence_threshold_exit:
            if len(self.presence_history) >= self.confirmation_time:
                # Verificar baja confianza sostenida
                recent_low = all(score <= 30 for score in self.presence_history[-self.confirmation_time:])
                if recent_low:
                    self.bed_occupied = False
                    self.presence_start_time = None
                    presence_changed = True
                    print("🛏️ ❌ AUSENCIA DETECTADA - Cama vacía")
                    print(f"   📊 Confianza: {self.presence_confidence:.0f}%")
        
        return presence_changed

    def _get_time_occupied(self, current_time):
        """
        Calcular tiempo en la cama en minutos
        """
        if self.presence_start_time:
            return (current_time - self.presence_start_time) / 60
        return 0

    def update_baseline_temperature(self, current_temp):
        """
        Actualizar temperatura baseline cuando la cama está vacía
        """
        if not self.bed_occupied:
            if self.baseline_temperature is None:
                self.baseline_temperature = current_temp
            else:
                # Filtro de paso bajo para actualización suave
                alpha = 0.05  # Factor de suavizado
                self.baseline_temperature = (1 - alpha) * self.baseline_temperature + alpha * current_temp

    def get_presence_summary(self):
        """
        Obtener resumen del estado de presencia
        """
        return {
            'occupied': self.bed_occupied,
            'confidence': self.presence_confidence,
            'baseline_temp': self.baseline_temperature,
            'time_occupied': self._get_time_occupied(time.time()),
            'history_length': len(self.presence_history)
        }

    def reset_presence_state(self):
        """
        Resetear estado de presencia (útil para reiniciar el sistema)
        """
        self.bed_occupied = False
        self.presence_confidence = 0.0
        self.presence_history.clear()
        self.presence_start_time = None
        print("🔄 Estado de presencia reseteado")

    def get_detailed_indicators(self, sensor_data):
        """
        Obtener análisis detallado de indicadores para debugging
        """
        bed_temp = sensor_data.get('bed_temperature', 22.0)
        activity = sensor_data.get('activity', 0.0)
        heart_rate = sensor_data.get('heart_rate', 60)
        hr_valid = sensor_data.get('hr_valid', False)
        finger_present = sensor_data.get('finger_present', False)
        
        temp_elevation = bed_temp - (self.baseline_temperature or bed_temp)
        
        return {
            'thermal': {
                'current_temp': bed_temp,
                'baseline_temp': self.baseline_temperature,
                'elevation': temp_elevation,
                'threshold': self.thermal_threshold,
                'active': temp_elevation > self.thermal_threshold
            },
            'movement': {
                'current_activity': activity,
                'threshold': self.activity_threshold,
                'active': activity > self.activity_threshold
            },
            'cardiovascular': {
                'heart_rate': heart_rate,
                'valid': hr_valid,
                'in_range': self.hr_min <= heart_rate <= self.hr_max,
                'active': hr_valid and self.hr_min <= heart_rate <= self.hr_max
            },
            'contact': {
                'finger_present': finger_present,
                'active': finger_present
            },
            'temporal': {
                'history_size': len(self.presence_history),
                'avg_confidence': sum(self.presence_history[-5:]) / min(5, len(self.presence_history)) if self.presence_history else 0,
                'active': len(self.presence_history) >= 5 and sum(self.presence_history[-5:]) / 5 > 50
            }
        }

    def calibrate_baseline(self, temperature_readings, duration_minutes=5):
        """
        Calibrar baseline de temperatura con múltiples lecturas
        
        Args:
            temperature_readings: Lista de lecturas de temperatura
            duration_minutes: Duración de calibración en minutos
        """
        if len(temperature_readings) >= 3:
            # Usar mediana para evitar outliers
            self.baseline_temperature = np.median(temperature_readings)
            print(f"📊 Baseline térmico calibrado: {self.baseline_temperature:.1f}°C")
            print(f"   📈 Basado en {len(temperature_readings)} lecturas en {duration_minutes} min")
        else:
            print("⚠️ Insuficientes lecturas para calibración de baseline")

    def __str__(self):
        """
        Representación string del estado del detector
        """
        status = "OCUPADA" if self.bed_occupied else "VACÍA"
        return f"BedPresenceDetector: {status} (Confianza: {self.presence_confidence:.0f}%)"

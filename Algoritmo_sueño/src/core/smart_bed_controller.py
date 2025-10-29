#!/usr/bin/env python3
"""
Sistema de Control Inteligente para Cama Ortopédica
Ajusta temperatura basado en estado de sueño, temperatura ambiente y corporal
Control de válvulas eléctricas de 220V para tanques de agua fría y caliente
Usa sensor MAX30102 para monitoreo de HR y SpO2
"""

import asyncio
import time
import numpy as np
from ..config import bed_config
from . import analyzer
from . import presence_detector
from ..sensors.drivers import MMA
from ..sensors.drivers import MAX30102
from ..sensors.drivers import HTU21D

# Importar driver AHT10 para temperatura ambiente
try:
    import adafruit_ahtx0
    import board
    import busio
    AHT10_AVAILABLE = True
except ImportError:
    print("⚠️ AHT10 no disponible - Usando temperatura del MAX30102")
    AHT10_AVAILABLE = False

# Importar GPIO para control de relés
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️ GPIO no disponible - Modo simulación")
    GPIO_AVAILABLE = False

# Estados de sueño
WAKE = 0
LIGHT_SLEEP = 1
REM_SLEEP = 2
DEEP_SLEEP = 3

# Configuración de pines GPIO para relés de válvulas (220V)
VALVE_HOT_WATER_PIN = bed_config.VALVE_HOT_WATER_PIN    # Pin para relé de válvula agua caliente
VALVE_COLD_WATER_PIN = bed_config.VALVE_COLD_WATER_PIN  # Pin para relé de válvula agua fría
VALVE_SAFETY_PIN = bed_config.VALVE_SAFETY_PIN          # Pin para relé de seguridad (corte general)

class SmartBedController:
    def __init__(self):
        """
        Controlador inteligente para cama ortopédica con válvulas de agua
        Usa MAX30102 para monitoreo de HR y SpO2
        """
        # Sensor MAX30102 para HR y SpO2
        try:
            self.max30102 = MAX30102.MAX30102(bed_config.I2C_MAX30102_ADDR)
            self.max30102_available = True
            print("✅ MAX30102 inicializado correctamente")
        except Exception as e:
            print(f"⚠️ MAX30102 no disponible: {e}")
            self.max30102_available = False
        
        # Acelerómetro para detección de movimiento
        try:
            self.mma8452q = MMA.MMA8452Q()
            self.activity_threshold = bed_config.ACCELEROMETER_ACTIVITY_THRESHOLD
            print("✅ Acelerómetro MMA8452Q inicializado")
        except Exception as e:
            print(f"⚠️ Acelerómetro no disponible: {e}")
            self.mma8452q = None
        
        # Sensor AHT10 para temperatura corporal (pulsera)
        try:
            if AHT10_AVAILABLE:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.aht10 = adafruit_ahtx0.AHTx0(i2c)
                self.aht10_available = True
                print("✅ Sensor AHT10 (pulsera) inicializado correctamente")
            else:
                self.aht10_available = False
        except Exception as e:
            print(f"⚠️ AHT10 (pulsera) no disponible: {e}")
            self.aht10_available = False
        
        # Sensor HTU21D para temperatura de la cama
        try:
            self.htu21d = HTU21D.HTU21D(bed_config.I2C_HTU21D_ADDR)
            self.htu21d_available = self.htu21d.is_available()
            if self.htu21d_available:
                print("✅ Sensor HTU21D (temperatura cama) inicializado correctamente")
            else:
                print("⚠️ HTU21D no disponible - Usando temperatura simulada")
        except Exception as e:
            print(f"⚠️ HTU21D no disponible: {e}")
            self.htu21d_available = False
            self.htu21d = None
        
        # Variables de estado
        self.activity = 0.0
        self.last_spike = -1e10
        self.last_acc = [0.0, 0.0, 0.0]
        self.last_t = int(round(time.time() * 1000))
        self.current_sleep_state = WAKE
        self.current_hr = 60
        self.current_spo2 = 98
        
        # Historial para cálculos HRV y análisis avanzado
        self.hr_history = []
        self.ibi_history = []  # Inter-beat intervals
        self.activity_history = []
        self.sleep_state_history = []
        self.timestamps = []
        
        # Análisis en tiempo real
        self.current_stress_score = 0.0
        self.current_sleep_quality = 0.0
        self.sleep_onset_detected = False
        self.sleep_onset_time = None
        self.last_analysis_time = time.time()
        
        # Detector de presencia en la cama
        self.presence_detector = presence_detector.BedPresenceDetector()
        
        # Control de temperatura con válvulas - BASADO EN ESTUDIOS CIENTÍFICOS
        # Datos: Descenso natural de ~0.8°C durante sueño, variabilidad ±1-2°C
        self.target_temperature = 22.0
        self.current_temperature = 22.0  # Temperatura actual del HTU21D
        self.comfort_zone = {
            # Ajustado según estudios de temperatura rectal y microclima
            WAKE: {"min": 21, "max": 25},        # Vigilia - temperatura basal alta
            LIGHT_SLEEP: {"min": 19, "max": 23}, # Inicio descenso (0.2-0.4°C)
            REM_SLEEP: {"min": 20, "max": 24},   # REM - actividad cerebral = similar vigilia
            DEEP_SLEEP: {"min": 17, "max": 21}   # Profundo - descenso máximo (0.8°C)
        }
        
        # Variables para control predictivo basado en estudios
        self.thermal_trend = 0.0           # Tendencia térmica para anticipación
        self.sleep_thermal_offset = 0.0    # Offset térmico acumulado durante sueño
        self.last_temp_reading_time = time.time()
        self.temp_change_rate = 0.0        # Velocidad de cambio térmico (°C/min)
        
        # Estado de válvulas
        self.hot_valve_open = False
        self.cold_valve_open = False
        self.safety_active = True
        
        # Configurar GPIO para control de válvulas
        self.setup_gpio()
        
        print("🛏️ Sistema de cama inteligente con MAX30102 inicializado")
        print(f"💧 Válvula agua caliente: Pin {VALVE_HOT_WATER_PIN}")
        print(f"❄️ Válvula agua fría: Pin {VALVE_COLD_WATER_PIN}")
        print(f"🔒 Seguridad: Pin {VALVE_SAFETY_PIN}")
        print(f"❤️ Sensor MAX30102: {'✅ Disponible' if self.max30102_available else '❌ No disponible'}")
        print(f"📱 Acelerómetro: {'✅ Disponible' if self.mma8452q else '❌ No disponible'}")
        print(f"🌡️ Sensor HTU21D (cama): {'✅ Disponible' if self.htu21d_available else '❌ No disponible'}")
        print(f"🌡️ Sensor AHT10 (pulsera): {'✅ Disponible' if self.aht10_available else '❌ No disponible'}")
        print(f"🛏️ Detector de presencia: ✅ Activo")
        
        # Configurar GPIO para control de válvulas
        self.setup_gpio()

    def setup_gpio(self):
        """Configurar pines GPIO para control de relés de válvulas"""
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Configurar pines como salida
                GPIO.setup(VALVE_HOT_WATER_PIN, GPIO.OUT)
                GPIO.setup(VALVE_COLD_WATER_PIN, GPIO.OUT)
                GPIO.setup(VALVE_SAFETY_PIN, GPIO.OUT)
                
                # Inicializar en estado seguro (válvulas cerradas)
                GPIO.output(VALVE_HOT_WATER_PIN, GPIO.LOW)   # Relé OFF = Válvula cerrada
                GPIO.output(VALVE_COLD_WATER_PIN, GPIO.LOW)  # Relé OFF = Válvula cerrada
                GPIO.output(VALVE_SAFETY_PIN, GPIO.HIGH)     # Relé ON = Seguridad activa
                
                print("✅ GPIO configurado correctamente")
            except Exception as e:
                print(f"❌ Error configurando GPIO: {e}")
        else:
            print("⚠️ GPIO no disponible - Funcionando en modo simulación")

    def get_accel_data(self):
        """Obtener datos del acelerómetro"""
        if not self.mma8452q:
            return None, None
            
        try:
            acc = self.mma8452q.read_accl()
            accl = [acc['x'], acc['y'], acc['z']]
            millis = int(round(time.time() * 1000))
            return millis, accl
        except Exception as e:
            print(f"❌ Error leyendo acelerómetro: {e}")
            return None, None

    def get_body_temperature(self):
        """Obtener temperatura corporal del sensor AHT10 en la pulsera"""
        if not self.aht10_available:
            return 36.5  # Temperatura corporal normal por defecto
            
        try:
            temperature = self.aht10.temperature
            # Validar que la temperatura esté en rango corporal normal
            if 35.0 <= temperature <= 42.0:  # Rango de temperatura corporal válido
                return temperature
            else:
                print(f"⚠️ Temperatura corporal fuera de rango: {temperature}°C")
                return 36.5  # Retornar temperatura normal si está fuera de rango
        except Exception as e:
            print(f"❌ Error leyendo AHT10 (pulsera): {e}")
            return 36.5

    def get_bed_temperature(self):
        """Obtener temperatura directa de la cama del sensor HTU21D"""
        if not self.htu21d_available or not self.htu21d:
            # Simular temperatura de cama si no hay sensor
            return 22.0 + np.random.uniform(-1.0, 3.0)
            
        try:
            data = self.htu21d.read_data()
            if data['valid'] and data['temperature'] is not None:
                # Validar rango razonable para temperatura de cama
                temp = data['temperature']
                if bed_config.BED_TEMP_MIN <= temp <= bed_config.BED_TEMP_MAX:
                    return temp
                else:
                    print(f"⚠️ Temperatura de cama fuera de rango: {temp}°C")
                    return self.current_temperature  # Mantener última temperatura válida
            else:
                print("⚠️ HTU21D: Datos no válidos")
                return self.current_temperature
        except Exception as e:
            print(f"❌ Error leyendo HTU21D: {e}")
            return self.current_temperature

    def get_bed_humidity(self):
        """Obtener humedad de la cama del sensor HTU21D"""
        if not self.htu21d_available or not self.htu21d:
            return 50.0  # Humedad normal por defecto
            
        try:
            data = self.htu21d.read_data()
            if data['valid'] and data['humidity'] is not None:
                return data['humidity']
            else:
                return 50.0
        except Exception as e:
            print(f"❌ Error leyendo humedad HTU21D: {e}")
            return 50.0

    def analyze_thermal_trends(self):
        """
        Analizar tendencias térmicas basado en estudios científicos
        Implementa predicción basada en patrones observados en investigación
        """
        if not hasattr(self, 'temperature_history'):
            self.temperature_history = []
            self.time_history = []
        
        current_time = time.time()
        current_temp = self.get_bed_temperature()
        
        # Mantener historial de temperaturas (últimas 30 lecturas = ~10 minutos)
        self.temperature_history.append(current_temp)
        self.time_history.append(current_time)
        
        if len(self.temperature_history) > 30:
            self.temperature_history.pop(0)
            self.time_history.pop(0)
        
        # Calcular tendencia térmica si tenemos suficientes datos
        if len(self.temperature_history) >= 5:
            # Calcular velocidad de cambio térmico (°C/min)
            time_span = (self.time_history[-1] - self.time_history[0]) / 60  # minutos
            temp_change = self.temperature_history[-1] - self.temperature_history[0]
            
            if time_span > 0:
                self.temp_change_rate = temp_change / time_span
                
                # Detectar patrones anómalos basados en estudios
                if abs(self.temp_change_rate) > 0.5:  # Cambio > 0.5°C/min es anómalo
                    if self.temp_change_rate > 0:
                        print(f"🌡️ Calentamiento rápido detectado: +{self.temp_change_rate:.2f}°C/min")
                    else:
                        print(f"🌡️ Enfriamiento rápido detectado: {self.temp_change_rate:.2f}°C/min")
                
                # Predicción térmica para los próximos 5 minutos
                predicted_temp = current_temp + (self.temp_change_rate * 5)
                
                # Alertas predictivas basadas en estudios
                if predicted_temp > bed_config.BED_TEMP_MAX:
                    print(f"🔮 PREDICCIÓN: Sobrecalentamiento en 5 min ({predicted_temp:.1f}°C)")
                    return "preventive_cooling"
                elif predicted_temp < bed_config.BED_TEMP_MIN:
                    print(f"🔮 PREDICCIÓN: Subenfriamiento en 5 min ({predicted_temp:.1f}°C)")
                    return "preventive_heating"
        
        # Análisis de estabilidad térmica según estudios
        if len(self.temperature_history) >= 10:
            recent_temps = self.temperature_history[-10:]
            temp_variance = np.var(recent_temps)
            
            if temp_variance > bed_config.THERMAL_VARIANCE_TOLERANCE:
                print(f"⚠️ Alta variabilidad térmica detectada: σ²={temp_variance:.2f}")
                return "stabilization_needed"
            elif temp_variance < 0.1:
                print(f"✅ Estabilidad térmica óptima: σ²={temp_variance:.2f}")
                return "stable"
        
        return "normal"

    def apply_scientific_thermal_control(self, target_temp, current_temp):
        """
        Aplicar control térmico basado en hallazgos científicos
        """
        # Analizar tendencias antes del control
        thermal_trend = self.analyze_thermal_trends()
        
        # Ajustar tolerancia basada en estudios de variabilidad
        base_tolerance = bed_config.BED_TEMP_TOLERANCE
        
        # Durante sueño profundo, permitir mayor variabilidad (según estudios)
        if self.current_sleep_state == DEEP_SLEEP:
            adjusted_tolerance = base_tolerance * 1.5  # ±0.75°C en sueño profundo
            print(f"🌌 Tolerancia ampliada para sueño profundo: ±{adjusted_tolerance:.1f}°C")
        elif self.current_sleep_state == REM_SLEEP:
            adjusted_tolerance = base_tolerance * 0.8  # ±0.4°C en REM (más sensible)
            print(f"🌙 Tolerancia reducida para REM: ±{adjusted_tolerance:.1f}°C")
        else:
            adjusted_tolerance = base_tolerance
        
        # Control predictivo basado en tendencias
        if thermal_trend == "preventive_cooling":
            return self.control_valves(target_temp - 0.5, current_temp, adjusted_tolerance)
        elif thermal_trend == "preventive_heating":
            return self.control_valves(target_temp + 0.5, current_temp, adjusted_tolerance)
        elif thermal_trend == "stabilization_needed":
            # Usar tolerancia más estricta para estabilizar
            return self.control_valves(target_temp, current_temp, adjusted_tolerance * 0.5)
        else:
            # Control normal con tolerancia ajustada por estado de sueño
            return self.control_valves(target_temp, current_temp, adjusted_tolerance)

    def perform_advanced_analysis(self):
        """
        Realizar análisis avanzado usando funciones de analyzer.py
        """
        current_time = time.time()
        
        # Calcular HRV si tenemos suficientes datos de HR
        rmssd = None
        sdnn = None
        if len(self.hr_history) >= 5:
            # Simular IBI desde HR (60000/HR para obtener ms entre latidos)
            simulated_ibi = [60000 / hr for hr in self.hr_history[-10:]]
            rmssd = analyzer.calculate_rmssd(simulated_ibi)
            sdnn = analyzer.calculate_sdnn(simulated_ibi)
        
        # Calcular puntuación de estrés
        if rmssd is not None and sdnn is not None:
            self.current_stress_score = analyzer.calculate_stress_score(
                self.current_hr, rmssd, sdnn
            )
        
        # Calcular calidad de sueño si tenemos suficiente historial
        if len(self.sleep_state_history) >= 30:  # Al menos 30 muestras (1 hora a 2 seg/muestra)
            self.current_sleep_quality = analyzer.calculate_sleep_quality(
                self.sleep_state_history,
                self.hr_history[-len(self.sleep_state_history):] if len(self.hr_history) >= len(self.sleep_state_history) else None,
                self.activity_history[-len(self.sleep_state_history):] if len(self.activity_history) >= len(self.sleep_state_history) else None
            )
        
        # Detectar inicio del sueño
        if not self.sleep_onset_detected and len(self.sleep_state_history) >= 10:
            onset_index = analyzer.detect_sleep_onset(self.sleep_state_history)
            if onset_index is not None:
                self.sleep_onset_detected = True
                self.sleep_onset_time = current_time - (len(self.sleep_state_history) - onset_index) * 2  # 2 seg por muestra
                print(f"🌙 INICIO DE SUEÑO detectado hace {(len(self.sleep_state_history) - onset_index) * 2 // 60} minutos")
        
        # Análisis de fragmentación (cada 5 minutos)
        if len(self.sleep_state_history) >= 150 and len(self.sleep_state_history) % 150 == 0:  # Cada 5 minutos
            transitions, fragmentation_index = analyzer.analyze_sleep_transitions(self.sleep_state_history)
            if fragmentation_index is not None:
                if fragmentation_index > 15:  # Más de 15 transiciones por hora = fragmentado
                    print(f"⚠️ Sueño fragmentado detectado: {fragmentation_index:.1f} transiciones/hora")
                else:
                    print(f"✅ Sueño consolidado: {fragmentation_index:.1f} transiciones/hora")
        
        # Detectar períodos de vigilia durante el sueño
        if len(self.sleep_state_history) >= 60:  # Analizar últimos 60 muestras (2 minutos)
            recent_states = self.sleep_state_history[-60:]
            wake_periods = analyzer.detect_wake_periods(recent_states, min_duration=3)
            if wake_periods:
                total_wake_time = sum(duration for _, duration in wake_periods)
                if total_wake_time > 10:  # Más de 10 muestras despierto en 2 minutos
                    print(f"😴 Despertar nocturno detectado: {total_wake_time * 2} segundos despierto")
        
        self.last_analysis_time = current_time

    def generate_sleep_report(self):
        """
        Generar reporte completo de la sesión de sueño
        """
        if len(self.sleep_state_history) < 10:
            print("⚠️ Datos insuficientes para generar reporte")
            return
        
        print("\n" + "="*60)
        print("📊 REPORTE FINAL DE SUEÑO")
        print("="*60)
        
        # Duración total
        total_duration_min = len(self.sleep_state_history) * 2 / 60  # 2 seg por muestra
        print(f"⏱️ Duración total de monitoreo: {total_duration_min:.0f} minutos")
        
        # Distribución de estados
        wake_count = self.sleep_state_history.count(0)
        light_count = self.sleep_state_history.count(1)
        rem_count = self.sleep_state_history.count(2)
        deep_count = self.sleep_state_history.count(3)
        
        total_samples = len(self.sleep_state_history)
        
        print(f"\n📈 DISTRIBUCIÓN DE ESTADOS:")
        print(f"   😴 Despierto: {wake_count/total_samples*100:.1f}% ({wake_count*2/60:.0f} min)")
        print(f"   💤 Sueño Ligero: {light_count/total_samples*100:.1f}% ({light_count*2/60:.0f} min)")
        print(f"   🌙 Sueño REM: {rem_count/total_samples*100:.1f}% ({rem_count*2/60:.0f} min)")
        print(f"   🌌 Sueño Profundo: {deep_count/total_samples*100:.1f}% ({deep_count*2/60:.0f} min)")
        
        # Análisis avanzado final
        if len(self.sleep_state_history) >= 30:
            final_quality = analyzer.calculate_sleep_quality(
                self.sleep_state_history, 
                self.hr_history[-len(self.sleep_state_history):] if len(self.hr_history) >= len(self.sleep_state_history) else None,
                self.activity_history
            )
            
            if final_quality:
                print(f"\n🎯 CALIDAD FINAL DE SUEÑO: {final_quality:.1f}/100")
                if final_quality >= 80:
                    print("🌟 ¡Excelente calidad de sueño!")
                elif final_quality >= 60:
                    print("✅ Buena calidad de sueño")
                elif final_quality >= 40:
                    print("⚠️ Calidad de sueño regular")
                else:
                    print("❌ Calidad de sueño deficiente")
        
        # Análisis de fragmentación
        transitions, fragmentation_index = analyzer.analyze_sleep_transitions(self.sleep_state_history)
        if fragmentation_index:
            print(f"\n🔄 FRAGMENTACIÓN:")
            print(f"   Transiciones totales: {transitions}")
            print(f"   Índice de fragmentación: {fragmentation_index:.1f} transiciones/hora")
            if fragmentation_index < 10:
                print("   ✅ Sueño muy consolidado")
            elif fragmentation_index < 15:
                print("   ✅ Sueño consolidado")
            elif fragmentation_index < 25:
                print("   ⚠️ Sueño ligeramente fragmentado")
            else:
                print("   ❌ Sueño muy fragmentado")
        
        # Inicio del sueño
        if self.sleep_onset_detected and self.sleep_onset_time:
            onset_delay = (self.sleep_onset_time - self.timestamps[0]) / 60
            print(f"\n🌙 LATENCIA DEL SUEÑO: {onset_delay:.0f} minutos")
            if onset_delay <= 15:
                print("   ✅ Latencia normal")
            elif onset_delay <= 30:
                print("   ⚠️ Latencia elevada")
            else:
                print("   ❌ Latencia muy elevada")
        
        # Despertares nocturnos
        wake_periods = analyzer.detect_wake_periods(self.sleep_state_history, min_duration=5)
        if wake_periods:
            total_wake_time = sum(duration for _, duration in wake_periods) * 2 / 60  # minutos
            print(f"\n😴 DESPERTARES NOCTURNOS:")
            print(f"   Número de despertares: {len(wake_periods)}")
            print(f"   Tiempo total despierto: {total_wake_time:.0f} minutos")
            if len(wake_periods) <= 2 and total_wake_time <= 30:
                print("   ✅ Despertares mínimos")
            elif len(wake_periods) <= 4 and total_wake_time <= 60:
                print("   ⚠️ Despertares moderados")
            else:
                print("   ❌ Despertares excesivos")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        if final_quality and final_quality < 60:
            print("   • Considerar mejoras en el ambiente de sueño")
            print("   • Revisar horarios de acostarse")
        if fragmentation_index and fragmentation_index > 20:
            print("   • Evaluar posibles interrupciones externas")
            print("   • Consultar con especialista en sueño")
        if len(wake_periods) > 3:
            print("   • Revisar temperatura ambiente y corporal")
            print("   • Evaluar nivel de estrés antes de dormir")
        
        print("="*60)

    def integrate_activity(self, activity, diff, dt, now, last_spike):
        """Calcular nivel de actividad integrado"""
        thresh = self.activity_threshold
        decay = bed_config.ACTIVITY_DECAY_CONSTANT
        spike_strength = bed_config.ACTIVITY_SPIKE_STRENGTH
        decay_delay = bed_config.ACTIVITY_DECAY_DELAY

        if diff > thresh:
            activity += (1.0 - activity) * spike_strength
            last_spike = now

        if now - last_spike > decay_delay and activity > bed_config.ACTIVITY_LOWER_BOUND:
            activity += -activity / decay * dt

        if activity < bed_config.ACTIVITY_LOWER_BOUND:
            activity = 0.0

        return activity, last_spike

    def detect_sleep_state(self, activity, heart_rate):
        """
        Detectar estado de sueño combinando actividad y HR
        Retorna: 0=WAKE, 1=LIGHT_SLEEP, 2=REM_SLEEP, 3=DEEP_SLEEP
        """
        # Clasificación por actividad
        if activity < bed_config.ACTIVITY_THRESHOLD_DEEP_SLEEP:  # < 0.01
            activity_state = DEEP_SLEEP
        elif activity < bed_config.ACTIVITY_THRESHOLD_REM:  # < 0.008 (micro-movimientos REM)
            activity_state = "REM_OR_LIGHT"
        elif activity < bed_config.ACTIVITY_THRESHOLD_WAKE:  # < 0.7
            activity_state = LIGHT_SLEEP
        else:
            activity_state = WAKE
        
        # Clasificación por frecuencia cardíaca
        if heart_rate < bed_config.HR_THRESHOLD_DEEP_SLEEP:  # < 55
            hr_state = DEEP_SLEEP
        elif heart_rate < bed_config.HR_THRESHOLD_WAKE:  # < 75
            hr_state = LIGHT_SLEEP
        else:
            hr_state = WAKE
        
        # Lógica combinada para distinguir REM
        if activity_state == DEEP_SLEEP and hr_state == DEEP_SLEEP:
            return DEEP_SLEEP  # ✅ Sueño profundo claro (baja actividad + HR bajo)
        
        elif activity_state == "REM_OR_LIGHT":
            if heart_rate >= bed_config.HR_THRESHOLD_REM and activity < bed_config.ACTIVITY_THRESHOLD_REM:
                return REM_SLEEP  # ✅ REM: HR alta + actividad muy baja con micro-movimientos
            elif heart_rate < 65:
                return LIGHT_SLEEP  # ✅ Sueño ligero NREM
            else:
                return WAKE  # Despierto pero quieto
        
        elif activity_state == LIGHT_SLEEP:
            if hr_state == WAKE:
                return WAKE  # Movimiento moderado + HR alta = despierto
            else:
                return LIGHT_SLEEP  # Sueño ligero NREM
        
        else:  # activity_state == WAKE
            return WAKE

    def calculate_target_temperature(self, sleep_state, ambient_temp, body_temp=None):
        """
        Calcular temperatura objetivo basada en estudios científicos:
        - Descenso térmico natural de ~0.8°C durante sueño
        - Variabilidad de microclima ±1-2°C
        - Estado de sueño específico
        - Temperatura ambiente (MAX30102)  
        - Temperatura corporal (AHT10 en pulsera)
        """
        comfort = self.comfort_zone[sleep_state]
        base_temp = (comfort["min"] + comfort["max"]) / 2
        
        # 🧬 AJUSTE BASADO EN ESTUDIOS CIENTÍFICOS
        # Aplicar descenso térmico natural según fase de sueño
        if sleep_state == LIGHT_SLEEP:
            # Inicio del descenso térmico (0.2-0.4°C)
            thermal_offset = -0.3
        elif sleep_state == REM_SLEEP:
            # REM mantiene temperatura similar a vigilia (actividad cerebral)
            thermal_offset = 0.0
        elif sleep_state == DEEP_SLEEP:
            # Descenso máximo observado en estudios (0.8°C)
            thermal_offset = -0.8
        else:  # WAKE
            thermal_offset = 0.0
        
        # Aplicar offset térmico científico
        base_temp += thermal_offset
        
        # Ajustar según temperatura ambiente (como antes)
        if ambient_temp > 25:
            adjustment = -1.0  # Enfriar más si hace calor
        elif ambient_temp < 15:
            adjustment = 1.0   # Calentar más si hace frío
        else:
            adjustment = 0.0
        
        # ✅ AJUSTE PRINCIPAL: Temperatura corporal del AHT10 en pulsera
        if body_temp:
            # Detectar desviaciones de la temperatura corporal normal (36.5-37.2°C)
            normal_body_temp = 36.8  # Temperatura basal promedio según estudios
            body_deviation = body_temp - normal_body_temp
            
            # Ajustar temperatura ambiente para compensar desviaciones corporales
            if body_temp >= 38.0:  # Fiebre
                adjustment -= 3.0 + (body_temp - 38.0) * 0.5  # Enfriamiento progresivo
                print(f"🌡️ Fiebre detectada ({body_temp:.1f}°C) - Enfriamiento científico aplicado")
            elif body_temp >= 37.5:  # Temperatura elevada
                adjustment -= 1.5 + (body_deviation * 0.3)
                print(f"🌡️ Temperatura corporal elevada ({body_temp:.1f}°C) - Ajuste: {adjustment:.1f}°C")
            elif body_temp <= 35.5:  # Hipotermia leve
                adjustment += 2.0 + abs(body_deviation) * 0.4  # Calentamiento progresivo
                print(f"🌡️ Temperatura corporal baja ({body_temp:.1f}°C) - Calentamiento científico aplicado")
            elif body_deviation < -0.5:  # Temperatura baja pero no crítica
                adjustment += abs(body_deviation) * 0.6
        
        # 📊 CONTROL PREDICTIVO - Anticipar cambios térmicos
        if hasattr(self, 'sleep_state_history') and len(self.sleep_state_history) >= 10:
            # Detectar transiciones de estado para anticipar necesidades térmicas
            recent_states = self.sleep_state_history[-10:]
            if recent_states[-1] != recent_states[-5]:  # Cambio de estado detectado
                if recent_states[-1] == DEEP_SLEEP and recent_states[-5] != DEEP_SLEEP:
                    # Entrando en sueño profundo - anticipar enfriamiento
                    adjustment -= 0.3
                    print("🔮 Control predictivo: Anticipando sueño profundo (-0.3°C)")
                elif recent_states[-1] == WAKE and recent_states[-5] != WAKE:
                    # Despertando - anticipar calentamiento
                    adjustment += 0.4
                    print("🔮 Control predictivo: Anticipando despertar (+0.4°C)")
        
        target = base_temp + adjustment
        
        # Limitar dentro del rango de confort científico y seguro
        target = max(comfort["min"], min(comfort["max"], target))
        target = max(bed_config.BED_TEMP_MIN, min(bed_config.BED_TEMP_MAX, target))
        
        # Aplicar suavizado para evitar cambios bruscos (según variabilidad observada)
        if hasattr(self, 'last_target_temp'):
            max_change = bed_config.THERMAL_VARIANCE_TOLERANCE / 4  # Cambio máximo por ciclo
            temp_change = target - self.last_target_temp
            if abs(temp_change) > max_change:
                target = self.last_target_temp + (max_change if temp_change > 0 else -max_change)
                print(f"🌊 Suavizado térmico aplicado: cambio limitado a ±{max_change:.1f}°C")
        
        self.last_target_temp = target
        return target

    def control_valves(self, target_temp, current_temp, tolerance=None):
        """
        Controlar válvulas de agua caliente y fría basado en temperatura objetivo
        
        Args:
            target_temp: Temperatura objetivo (°C)
            current_temp: Temperatura actual de la cama (HTU21D) (°C) 
            tolerance: Tolerancia antes de activar válvulas (°C)
        """
        if tolerance is None:
            tolerance = bed_config.BED_TEMP_TOLERANCE
            
        temp_diff = target_temp - current_temp
        
        # Determinar acción necesaria
        if abs(temp_diff) <= tolerance:
            # Temperatura en rango objetivo - cerrar todas las válvulas
            action = "maintain"
            hot_needed = False
            cold_needed = False
        elif temp_diff > tolerance:
            # Necesita calentamiento - abrir válvula agua caliente
            action = "heat"
            hot_needed = True
            cold_needed = False
        else:
            # Necesita enfriamiento - abrir válvula agua fría
            action = "cool"
            hot_needed = False
            cold_needed = True
        
        # Aplicar control de válvulas con seguridad
        self.set_valve_states(hot_needed, cold_needed, action)
        
        return action

    def set_valve_states(self, hot_open, cold_open, action):
        """
        Controlar estado de las válvulas con medidas de seguridad
        
        Args:
            hot_open: True para abrir válvula agua caliente
            cold_open: True para abrir válvula agua fría
            action: Descripción de la acción para logging
        """
        # Medida de seguridad: nunca abrir ambas válvulas simultáneamente
        if hot_open and cold_open:
            print("🚨 ALERTA DE SEGURIDAD: Intentando abrir ambas válvulas - BLOQUEADO")
            hot_open = False
            cold_open = False
            action = "safety_block"
        
        # Controlar válvula de agua caliente
        if hot_open != self.hot_valve_open:
            self.hot_valve_open = hot_open
            if GPIO_AVAILABLE:
                GPIO.output(VALVE_HOT_WATER_PIN, GPIO.HIGH if hot_open else GPIO.LOW)
                print(f"💧 Válvula agua caliente: {'ABIERTA' if hot_open else 'CERRADA'}")
            else:
                print(f"💧 [SIM] Válvula agua caliente: {'ABIERTA' if hot_open else 'CERRADA'}")
        
        # Controlar válvula de agua fría
        if cold_open != self.cold_valve_open:
            self.cold_valve_open = cold_open
            if GPIO_AVAILABLE:
                GPIO.output(VALVE_COLD_WATER_PIN, GPIO.HIGH if cold_open else GPIO.LOW)
                print(f"❄️ Válvula agua fría: {'ABIERTA' if cold_open else 'CERRADA'}")
            else:
                print(f"❄️ [SIM] Válvula agua fría: {'ABIERTA' if cold_open else 'CERRADA'}")
        
        # Log de acción
        action_icons = {
            "heat": "🔥",
            "cool": "❄️", 
            "maintain": "✅",
            "safety_block": "🚨"
        }
        
        action_descriptions = {
            "heat": "CALENTANDO - Agua caliente activada",
            "cool": "ENFRIANDO - Agua fría activada", 
            "maintain": "TEMPERATURA ÓPTIMA - Válvulas cerradas",
            "safety_block": "SEGURIDAD ACTIVADA - Todas las válvulas cerradas"
        }
        
        print(f"{action_icons.get(action, '🔧')} {action_descriptions.get(action, action.upper())}")

    def emergency_stop(self):
        """Parada de emergencia - cerrar todas las válvulas inmediatamente"""
        print("🚨 PARADA DE EMERGENCIA - Cerrando todas las válvulas")
        
        if GPIO_AVAILABLE:
            GPIO.output(VALVE_HOT_WATER_PIN, GPIO.LOW)
            GPIO.output(VALVE_COLD_WATER_PIN, GPIO.LOW)
            GPIO.output(VALVE_SAFETY_PIN, GPIO.LOW)  # Desactivar seguridad
        
        self.hot_valve_open = False
        self.cold_valve_open = False
        self.safety_active = False
        
        print("🔒 Todas las válvulas cerradas por seguridad")

    def control_bed_temperature(self, target_temp):
        """
        Controlar la temperatura de la cama mediante válvulas de agua
        Usa lectura real del sensor HTU21D + control científico predictivo
        """
        state_names = ["DESPIERTO", "SUEÑO LIGERO", "SUEÑO REM", "SUEÑO PROFUNDO"]
        
        # 🌡️ LEER TEMPERATURA REAL DE LA CAMA (HTU21D)
        self.current_temperature = self.get_bed_temperature()
        bed_humidity = self.get_bed_humidity()
        
        print(f"\n🌡️ Estado: {state_names[self.current_sleep_state]}")
        print(f"🎯 Temperatura objetivo: {target_temp:.1f}°C")
        print(f"🛏️ Temperatura cama (HTU21D): {self.current_temperature:.1f}°C")
        print(f"💧 Humedad cama: {bed_humidity:.1f}%")
        print(f"❤️ Frecuencia cardíaca: {self.current_hr} BPM")
        print(f"🏃 Actividad: {self.activity:.3f}")
        
        # 🧬 APLICAR CONTROL TÉRMICO CIENTÍFICO
        action = self.apply_scientific_thermal_control(target_temp, self.current_temperature)
        
        # Calcular eficiencia del control térmico con base científica
        temp_error = abs(target_temp - self.current_temperature)
        
        # Criterios de eficiencia basados en estudios de variabilidad
        if temp_error <= bed_config.BED_TEMP_TOLERANCE:
            efficiency = "🌟 EXCELENTE"
            efficiency_score = 100
        elif temp_error <= 1.0:
            efficiency = "✅ BUENA"
            efficiency_score = 85
        elif temp_error <= bed_config.THERMAL_VARIANCE_TOLERANCE:
            efficiency = "🟡 ACEPTABLE"  # Dentro de variabilidad natural observada
            efficiency_score = 70
        elif temp_error <= 3.0:
            efficiency = "🟠 REGULAR"
            efficiency_score = 50
        else:
            efficiency = "🔴 DEFICIENTE"
            efficiency_score = 25
        
        print(f"🎯 Error térmico: ±{temp_error:.1f}°C ({efficiency}) - Score: {efficiency_score}/100")
        
        # Mostrar velocidad de cambio térmico si está disponible
        if hasattr(self, 'temp_change_rate') and self.temp_change_rate != 0:
            trend_icon = "📈" if self.temp_change_rate > 0 else "📉"
            print(f"{trend_icon} Tendencia térmica: {self.temp_change_rate:.2f}°C/min")
        
        # ⚠️ ALERTAS DE TEMPERATURA BASADAS EN ESTUDIOS
        if self.current_temperature > bed_config.BED_TEMP_MAX:
            print(f"🚨 ALERTA CIENTÍFICA: Temperatura excede rango fisiológico ({self.current_temperature:.1f}°C)")
        elif self.current_temperature < bed_config.BED_TEMP_MIN:
            print(f"🚨 ALERTA CIENTÍFICA: Temperatura por debajo del confort térmico ({self.current_temperature:.1f}°C)")
            
        # Alertas basadas en desviación de patrones naturales
        if hasattr(self, 'sleep_state_history') and len(self.sleep_state_history) >= 30:
            sleep_duration_min = len(self.sleep_state_history) * 2 / 60
            expected_thermal_descent = 0.0
            
            # Calcular descenso térmico esperado según tiempo de sueño
            if sleep_duration_min > 60:  # Más de 1 hora dormido
                deep_sleep_ratio = self.sleep_state_history.count(DEEP_SLEEP) / len(self.sleep_state_history)
                expected_thermal_descent = deep_sleep_ratio * bed_config.THERMAL_DESCENT_RATE
                
                if expected_thermal_descent > 0.3 and temp_error > 2.0:
                    print(f"📊 PATRÓN ANÓMALO: Descenso térmico esperado {expected_thermal_descent:.1f}°C no alcanzado")
        
        # Mostrar estado de sensores de temperatura
        sensor_status = "HTU21D-Real" if self.htu21d_available else "Simulado"
        print(f"📡 Sensor temperatura cama: {sensor_status}")
        
        # Recomendaciones científicas basadas en eficiencia
        if efficiency_score < 70:
            print(f"💡 RECOMENDACIÓN CIENTÍFICA: Revisar aislamiento térmico de la cama")
        elif efficiency_score > 90:
            print(f"🏆 CONTROL ÓPTIMO: Sistema térmico funcionando según parámetros científicos")
        
        return action
    def get_max30102_data(self):
        """Obtener datos del sensor MAX30102"""
        if not self.max30102_available:
            # Simular datos si no hay sensor
            return {
                'heart_rate': 60 + np.random.randint(-5, 5),
                'spo2': 98 + np.random.randint(-2, 2),
                'valid_hr': False,
                'valid_spo2': False,
                'temperature': 22.0,
                'finger_present': False
            }
        
        try:
            data = self.max30102.update()
            data['finger_present'] = self.max30102.is_finger_present()
            return data
        except Exception as e:
            print(f"❌ Error leyendo MAX30102: {e}")
            return {
                'heart_rate': self.current_hr,
                'spo2': self.current_spo2,
                'valid_hr': False,
                'valid_spo2': False,
                'temperature': 22.0,
                'finger_present': False
            }

    def process_sensor_data(self):
        """Procesar datos de todos los sensores"""
        # Obtener datos del MAX30102
        max_data = self.get_max30102_data()
        
        # Actualizar HR y SpO2 si son válidos
        if max_data['valid_hr']:
            self.current_hr = max_data['heart_rate']
            
            # Mantener historial para HRV y análisis avanzado
            self.hr_history.append(self.current_hr)
            if len(self.hr_history) > 100:  # Mantener últimas 100 muestras (3+ minutos)
                self.hr_history.pop(0)
                
        if max_data['valid_spo2']:
            self.current_spo2 = max_data['spo2']
        
        # Obtener datos de acelerómetro
        t, acc = self.get_accel_data()
        if acc is not None and t is not None:
            # Calcular diferencia de movimiento
            diff = abs(((acc[0] - self.last_acc[0]) + 
                        (acc[1] - self.last_acc[1]) + 
                        (acc[2] - self.last_acc[2])) / 3)
            
            # Actualizar nivel de actividad
            dt = t - self.last_t if self.last_t is not None and self.last_t > 0 else 0
            self.activity, self.last_spike = self.integrate_activity(
                self.activity, diff, dt, t, self.last_spike)
            
            # Actualizar variables
            self.last_acc = acc
            self.last_t = t
        else:
            # Si no hay acelerómetro, usar actividad basada en variabilidad de HR
            if len(self.hr_history) >= 3:
                hr_variance = np.std(self.hr_history[-3:])
                self.activity = min(float(hr_variance / 10.0), 1.0)  # Normalizar
        
        # Detectar presencia en la cama usando el detector modular
        sensor_data_for_presence = {
            'bed_temperature': self.get_bed_temperature(),
            'activity': self.activity,
            'heart_rate': self.current_hr,
            'hr_valid': max_data['valid_hr'],
            'finger_present': max_data['finger_present']
        }
        
        presence_info = self.presence_detector.detect_presence(sensor_data_for_presence)
        
        # Actualizar baseline de temperatura
        self.presence_detector.update_baseline_temperature(sensor_data_for_presence['bed_temperature'])
        
        # Solo procesar sueño si hay alguien en la cama
        if not presence_info['occupied']:
            print(f"🛏️ Cama vacía (Confianza: {presence_info['confidence']:.0f}%) - Pausando análisis de sueño")
            # Reset de variables de sueño cuando no hay nadie
            if self.current_sleep_state != WAKE:
                self.current_sleep_state = WAKE
                self.sleep_onset_detected = False
                self.sleep_onset_time = None
            return
        
        # Detectar estado de sueño solo si hay presencia confirmada
        new_sleep_state = self.detect_sleep_state(self.activity, self.current_hr)
        
        # Actualizar historiales para análisis avanzado
        self.sleep_state_history.append(new_sleep_state)
        self.activity_history.append(self.activity)
        self.timestamps.append(time.time())
        
        # Mantener historiales de tamaño razonable (últimas 1800 muestras = 1 hora)
        max_history_size = 1800
        if len(self.sleep_state_history) > max_history_size:
            self.sleep_state_history.pop(0)
            self.activity_history.pop(0)
            self.timestamps.pop(0)
        
        # Si el estado cambió, recalcular temperatura
        if new_sleep_state != self.current_sleep_state:
            self.current_sleep_state = new_sleep_state
            print(f"🔄 Cambio de estado de sueño detectado")
        
        # Realizar análisis avanzado cada 30 segundos
        if time.time() - self.last_analysis_time >= 30:
            self.perform_advanced_analysis()
        
        # Calcular temperaturas antes de mostrar
        ambient_temp = max_data['temperature']  # Temperatura ambiente del MAX30102
        body_temp = self.get_body_temperature()  # Temperatura corporal del AHT10 en pulsera
        bed_temp = self.get_bed_temperature()    # Temperatura de la cama del HTU21D
        
        target_temp = self.calculate_target_temperature(
            self.current_sleep_state, ambient_temp, body_temp)
        
        # Mostrar datos en tiempo real
        sleep_states = ["😴 DESPIERTO", "💤 SUEÑO LIGERO", "🌙 SUEÑO REM", "🌌 SUEÑO PROFUNDO"]
        finger_status = "👆 Dedo detectado" if max_data['finger_present'] else "❌ Sin dedo"
        
        # Estado de presencia
        presence_icon = "🛏️ ✅" if presence_info['occupied'] else "🛏️ ❌"
        presence_status = f"OCUPADA ({presence_info['confidence']:.0f}%)" if presence_info['occupied'] else f"VACÍA ({presence_info['confidence']:.0f}%)"
        
        print(f"━━━ ESTADO ACTUAL ━━━")
        print(f"{presence_icon} Cama: {presence_status}")
        if presence_info['occupied']:
            print(f"⏰ Tiempo en cama: {presence_info['time_occupied']:.0f} min")
            print(f"🔍 Indicadores: {[k for k, v in presence_info['indicators'].items() if v]}")
        print(f"Estado: {sleep_states[self.current_sleep_state]}")
        print(f"❤️  HR: {self.current_hr:3d} BPM {'✅' if max_data['valid_hr'] else '❌'}")
        print(f"🩸 SpO2: {self.current_spo2:2d}% {'✅' if max_data['valid_spo2'] else '❌'}")
        print(f"📱 Sensor: {finger_status}")
        print(f"🏃 Actividad: {self.activity:.3f}")
        print(f"🌡️ Temp ambiente: {ambient_temp:.1f}°C (MAX30102)")
        print(f"🌡️ Temp corporal: {body_temp:.1f}°C (AHT10 pulsera)")
        print(f"🛏️ Temp cama: {bed_temp:.1f}°C (HTU21D)")
        
        # Mostrar información de temperatura baseline desde el detector
        baseline_temp = self.presence_detector.baseline_temperature
        if baseline_temp:
            temp_diff = bed_temp - baseline_temp
            print(f"📊 Δ Temp baseline: {temp_diff:+.1f}°C")
        print(f"🎯 Temp objetivo: {target_temp:.1f}°C")
        
        # ✅ ANÁLISIS AVANZADO
        if self.current_stress_score and self.current_stress_score > 0:
            stress_level = "🔴 ALTO" if self.current_stress_score > 70 else "🟡 MEDIO" if self.current_stress_score > 40 else "🟢 BAJO"
            print(f"😰 Estrés: {self.current_stress_score:.1f}/100 ({stress_level})")
        
        if self.current_sleep_quality and self.current_sleep_quality > 0:
            quality_level = "🌟 EXCELENTE" if self.current_sleep_quality > 80 else "✅ BUENA" if self.current_sleep_quality > 60 else "⚠️ REGULAR" if self.current_sleep_quality > 40 else "❌ MALA"
            print(f"💤 Calidad sueño: {self.current_sleep_quality:.1f}/100 ({quality_level})")
        
        if self.sleep_onset_detected and self.sleep_onset_time:
            sleep_duration_min = (time.time() - self.sleep_onset_time) / 60
            print(f"⏰ Tiempo dormido: {sleep_duration_min:.0f} min")
        
        # Mostrar estadísticas de sesión
        if len(self.sleep_state_history) >= 30:
            wake_pct = (self.sleep_state_history.count(0) / len(self.sleep_state_history)) * 100
            light_pct = (self.sleep_state_history.count(1) / len(self.sleep_state_history)) * 100
            rem_pct = (self.sleep_state_history.count(2) / len(self.sleep_state_history)) * 100
            deep_pct = (self.sleep_state_history.count(3) / len(self.sleep_state_history)) * 100
            print(f"📊 Distribución: Despierto {wake_pct:.0f}% | Ligero {light_pct:.0f}% | REM {rem_pct:.0f}% | Profundo {deep_pct:.0f}%")
        
        # Alertas de salud
        if max_data['valid_spo2'] and self.current_spo2 < bed_config.SPO2_MIN_ALERT:
            print(f"🚨 ALERTA: SpO2 bajo ({self.current_spo2}%) - Revisar!")
        
        # Controles de seguridad por HR
        if self.current_hr > bed_config.MAX_HR_ALERT:  # HR muy alta
            print("⚠️ ALERTA: Frecuencia cardíaca muy alta - Activando enfriamiento")
            self.set_valve_states(False, True, "hr_safety")
        elif self.current_hr < bed_config.MIN_HR_ALERT:  # HR muy baja
            print("⚠️ ALERTA: Frecuencia cardíaca muy baja - Activando calentamiento")
            self.set_valve_states(True, False, "hr_safety")
        
        # Alertas de temperatura corporal
        if body_temp >= bed_config.BODY_TEMP_FEVER:
            print(f"🚨 ALERTA: FIEBRE detectada ({body_temp:.1f}°C) - Activando enfriamiento")
        elif body_temp <= bed_config.BODY_TEMP_MIN_ALERT:
            print(f"🚨 ALERTA: Temperatura corporal baja ({body_temp:.1f}°C) - Activando calentamiento")
        
        # Aplicar control de temperatura
        self.control_bed_temperature(target_temp)
        
        print("-" * 50)

    async def start_monitoring(self):
        """Iniciar monitoreo continuo con MAX30102"""
        print("🚀 Iniciando monitoreo de cama inteligente con MAX30102...")
        print("👆 Coloca tu dedo en el sensor MAX30102 para mejores lecturas")
        
        try:
            while True:
                # Procesar datos de sensores
                self.process_sensor_data()
                
                # Pausa entre lecturas
                await asyncio.sleep(2)  # Leer cada 2 segundos
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoreo detenido por usuario")
        except Exception as e:
            print(f"❌ Error en monitoreo: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpiar recursos al salir"""
        print("🧹 Limpiando recursos...")
        
        # Generar reporte final de sueño
        if len(self.sleep_state_history) >= 10:
            self.generate_sleep_report()
        
        self.emergency_stop()
        
        if self.max30102_available:
            try:
                self.max30102.cleanup()
                print("✅ MAX30102 limpiado")
            except:
                pass
        
        if self.htu21d_available and self.htu21d:
            try:
                self.htu21d.cleanup()
                print("✅ HTU21D limpiado")
            except:
                pass
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            print("✅ GPIO limpiado")

    def __del__(self):
        """Destructor - asegurar limpieza al eliminar objeto"""
        self.cleanup()

async def main():
    """Función principal"""
    print("🛏️ === SISTEMA DE CAMA ORTOPÉDICA INTELIGENTE CON MAX30102 ===")
    print("📊 Configuración:")
    print(f"   • Sensor HR/SpO2: MAX30102 (I2C Address: 0x{bed_config.I2C_MAX30102_ADDR:02X})")
    print(f"   • Sensor temp cama: HTU21D (I2C Address: 0x{bed_config.I2C_HTU21D_ADDR:02X})")
    print(f"   • Sensor temp corporal: AHT10 (I2C Address: 0x{bed_config.I2C_AHT10_ADDR:02X})")
    print(f"   • Tolerancia temperatura: ±{bed_config.BED_TEMP_TOLERANCE}°C")
    print(f"   • Rango temperatura cama: {bed_config.BED_TEMP_MIN}-{bed_config.BED_TEMP_MAX}°C")
    print(f"   • Umbral sueño profundo (actividad): {bed_config.ACTIVITY_THRESHOLD_DEEP_SLEEP}")
    print(f"   • Umbral REM (actividad): {bed_config.ACTIVITY_THRESHOLD_REM}")
    print(f"   • Umbral despertar (actividad): {bed_config.ACTIVITY_THRESHOLD_WAKE}")
    print(f"   • Umbral sueño profundo (HR): {bed_config.HR_THRESHOLD_DEEP_SLEEP} BPM")
    print(f"   • Umbral REM (HR): {bed_config.HR_THRESHOLD_REM} BPM")
    print(f"   • Umbral despertar (HR): {bed_config.HR_THRESHOLD_WAKE} BPM")
    print(f"   • Alerta SpO2 mínimo: {bed_config.SPO2_MIN_ALERT}%")
    print(f"   • Detector presencia: Entrada {getattr(bed_config, 'PRESENCE_CONFIDENCE_THRESHOLD_ENTER', 60)}% / Salida {getattr(bed_config, 'PRESENCE_CONFIDENCE_THRESHOLD_EXIT', 20)}%")
    print()
    
    # Crear controlador de cama
    bed_controller = SmartBedController()
    
    try:
        # Iniciar monitoreo
        await bed_controller.start_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo sistema...")
        bed_controller.cleanup()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        bed_controller.emergency_stop()
    finally:
        bed_controller.cleanup()

if __name__ == "__main__":
    print("✅ Sistema preparado con sensores MAX30102 y HTU21D")
    print("💡 Para verificar la conexión I2C, ejecuta: sudo i2cdetect -y 1")
    print("📝 Deberías ver los dispositivos en:")
    print("   • 0x57 - MAX30102 (HR/SpO2)")
    print("   • 0x40 - HTU21D (Temperatura cama)")
    print("   • 0x38 - AHT10 (Temperatura corporal)")
    print("   • 0x1D - MMA8452Q (Acelerómetro)")
    print()
    
    # Ejecutar sistema:
    asyncio.run(main())

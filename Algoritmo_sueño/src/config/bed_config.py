# CONFIGURACIÓN UNIFICADA PARA CAMA ORTOPÉDICA INTELIGENTE
# =========================================================
# Unifica config.py y bed_config.py en una sola configuración completa

# CONFIGURACIÓN BÁSICA
# --------------------
VERBOSE_OUTPUT = True  # Mostrar información detallada
STIMULUS_ACTIVE = False  # Activar estímulos (obsoleto)
SYSTEM_NAME = "Cama Ortopédica Inteligente v2.0 - REM Edition"

# HARDWARE - I2C ADDRESSES
# ------------------------
I2C_ACCEL_ADDR = 0x1D        # Dirección del acelerómetro MMA8452Q
I2C_MAX30102_ADDR = 0x57     # Dirección del sensor MAX30102
I2C_AHT10_ADDR = 0x38        # Dirección del sensor AHT10 (pulsera)
I2C_HTU21D_ADDR = 0x40       # Dirección del sensor HTU21D (temperatura cama)
ACCELEROMETER_ACTIVITY_THRESHOLD = 12.5  # Umbral de detección de movimiento

# SENSOR MAX30102 (Oximetría + HR + Temperatura ambiente)
# -------------------------------------------------------
MAX30102_ENABLED = True  # Usar MAX30102 en lugar de Bluetooth
FINGER_DETECTION_THRESHOLD = 50000  # Umbral para detectar dedo
SPO2_MIN_ALERT = 88  # SpO2 mínimo antes de alerta
SPO2_MAX_NORMAL = 100  # SpO2 máximo normal

# SENSOR AHT10 (Temperatura corporal en pulsera)
# ----------------------------------------------
AHT10_ENABLED = True  # Usar AHT10 para temperatura corporal
BODY_TEMP_MIN_ALERT = 35.5   # Temperatura corporal mínima (°C)
BODY_TEMP_MAX_ALERT = 38.0   # Temperatura corporal máxima (°C)
BODY_TEMP_FEVER = 38.0       # Umbral de fiebre (°C)

# SENSOR HTU21D (Temperatura de la cama)
# --------------------------------------
HTU21D_ENABLED = True        # Usar HTU21D para temperatura de la cama
BED_TEMP_MIN = 15.0          # Temperatura mínima de la cama (°C)
BED_TEMP_MAX = 30.0          # Temperatura máxima de la cama (°C)
BED_TEMP_TOLERANCE = 0.5     # Tolerancia antes de activar válvulas (°C)
BED_TEMP_UPDATE_INTERVAL = 5 # Intervalo de actualización en segundos

# CONTROL TÉRMICO PREDICTIVO - Basado en estudios científicos
# ----------------------------------------------------------
THERMAL_DESCENT_RATE = 0.8   # Descenso térmico natural durante sueño (°C)
THERMAL_VARIANCE_TOLERANCE = 2.0  # Variabilidad térmica normal (±°C)
THERMAL_ANTICIPATION_TIME = 10    # Tiempo de anticipación térmica (minutos)
THERMAL_RESPONSE_SENSITIVITY = 0.3 # Sensibilidad de respuesta térmica
SLEEP_THERMAL_ADAPTATION = True   # Activar adaptación térmica durante sueño

# ESTADOS DE SUEÑO (4 Estados - Incluye REM)
# ------------------------------------------
SLEEP_STATE_WAKE = 0
SLEEP_STATE_LIGHT = 1
SLEEP_STATE_REM = 2          # ✅ Nuevo estado REM
SLEEP_STATE_DEEP = 3         # ✅ Actualizado a valor 3

# DETECCIÓN DE SUEÑO - ACTIVIDAD
# ------------------------------
ACTIVITY_THRESHOLD_DEEP_SLEEP = 0.01   # < 0.01 = sueño profundo
ACTIVITY_THRESHOLD_REM = 0.008          # < 0.008 = REM (con micro-movimientos)
ACTIVITY_THRESHOLD_WAKE = 0.7           # > 0.7 = despierto

# DETECCIÓN DE SUEÑO - FRECUENCIA CARDÍACA  
# ----------------------------------------
HR_THRESHOLD_DEEP_SLEEP = 55   # < 55 BPM = sueño profundo
HR_THRESHOLD_REM = 70          # ≥ 70 BPM + baja actividad = REM
HR_THRESHOLD_WAKE = 75         # ≥ 75 BPM = despierto

# PESOS PARA ALGORITMO COMBINADO
# ------------------------------
ACTIVITY_WEIGHT = 0.6  # Peso de la actividad en la detección (60%)
HR_WEIGHT = 0.4        # Peso del HR en la detección (40%)

# INTEGRADOR DE ACTIVIDAD
# -----------------------
ACTIVITY_DECAY_CONSTANT = 2 * 60 * 1000.0      # Constante de decaimiento (2 min)
ACTIVITY_SPIKE_STRENGTH = 0.05                  # Fuerza del pico de actividad
ACTIVITY_DECAY_DELAY = 5 * 60 * 1000.0          # Retardo antes del decaimiento (5 min)
ACTIVITY_LOWER_BOUND = 1e-3                     # Límite inferior de actividad

# CONTROL DE TEMPERATURA POR ESTADO (4 Estados)
# -----------------------------------------------
# Rangos de temperatura por estado de sueño (°C)
TEMP_WAKE = {"min": 20, "max": 24}              # Despierto: confort normal
TEMP_LIGHT_SLEEP = {"min": 18, "max": 22}       # Sueño ligero: ligeramente más fresco
TEMP_REM_SLEEP = {"min": 19, "max": 23}         # ✅ REM: similar a vigilia (termorregulación alterada)
TEMP_DEEP_SLEEP = {"min": 16, "max": 20}        # Sueño profundo: más fresco para mejor descanso

# Ajustes automáticos
TEMP_ADJUSTMENT_STEP = 0.5      # Paso de ajuste de temperatura (°C)
TEMP_CHANGE_THRESHOLD = 1.0     # Umbral para cambiar temperatura (°C)
TEMP_UPDATE_INTERVAL = 30       # Intervalo de actualización (segundos)

# LÍMITES DE SEGURIDAD
# --------------------
MIN_SAFE_TEMP = 10     # Temperatura mínima absoluta (°C)
MAX_SAFE_TEMP = 30     # Temperatura máxima absoluta (°C)
MAX_HR_ALERT = 120     # HR máxima antes de alerta (BPM)
MIN_HR_ALERT = 40      # HR mínima antes de alerta (BPM)

# HARDWARE ESPECÍFICO - GPIO PARA VÁLVULAS (220V)
# ------------------------------------------------
VALVE_HOT_WATER_PIN = 18    # Pin GPIO para relé de válvula agua caliente
VALVE_COLD_WATER_PIN = 19   # Pin GPIO para relé de válvula agua fría
VALVE_SAFETY_PIN = 20       # Pin GPIO para relé de seguridad (corte general)

# PWM PARA CONTROL VARIABLE (Opcional)
# ------------------------------------
# PWM_FREQUENCY = 1000           # Frecuencia PWM para control de potencia
# GPIO_FAN_PIN = 21              # Pin GPIO para ventilador

# SENSORES ADICIONALES (Opcional)
# -------------------------------
# SENSOR_TEMP_AMBIENT_PIN = 22   # Pin para sensor de temperatura ambiente adicional
# SENSOR_PRESSURE_PIN = 23       # Pin para sensor de presión en cama

# COMUNICACIÓN IOT (Opcional)
# ---------------------------
# MQTT_BROKER = "localhost"      # Broker MQTT para IoT
# MQTT_PORT = 1883
# MQTT_TOPIC_TEMP = "bed/temperature"
# MQTT_TOPIC_STATE = "bed/sleep_state"
# MQTT_TOPIC_HEALTH = "bed/health_alerts"

# CONFIGURACIÓN DE LOGGING (Solo para debug, no persistencia)
# ----------------------------------------------------------
LOG_TO_CONSOLE = True
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# DETECCIÓN DE PRESENCIA EN LA CAMA
# ---------------------------------
PRESENCE_CONFIDENCE_THRESHOLD_ENTER = 60  # Umbral para confirmar presencia (%)
PRESENCE_CONFIDENCE_THRESHOLD_EXIT = 20   # Umbral para confirmar ausencia (%)
PRESENCE_THERMAL_THRESHOLD = 1.5          # Elevación térmica mínima (°C)
PRESENCE_ACTIVITY_THRESHOLD = 0.001       # Actividad mínima para detección
PRESENCE_HR_MIN = 40                      # HR mínima válida (BPM)
PRESENCE_HR_MAX = 150                     # HR máxima válida (BPM)
PRESENCE_HISTORY_SIZE = 30                # Tamaño del historial de presencia (muestras)
PRESENCE_CONFIRMATION_TIME = 15           # Tiempo para confirmar ausencia (muestras)

print(f"✅ {SYSTEM_NAME} - Configuración unificada cargada")
print(f"🛏️ Estados de sueño: WAKE(0), LIGHT(1), REM(2), DEEP(3)")
print(f"🌡️ Control térmico con {len([TEMP_WAKE, TEMP_LIGHT_SLEEP, TEMP_REM_SLEEP, TEMP_DEEP_SLEEP])} zonas de confort")

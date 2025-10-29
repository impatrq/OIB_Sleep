# 🛏️ Detector de Presencia para Cama Inteligente

El **Detector de Presencia** es un módulo independiente que determina si hay alguien en la cama usando múltiples sensores. Ha sido extraído del controlador principal para mayor modularidad y reutilización.

## 📊 Características

### **Algoritmo Multi-Sensor**
Combina 5 indicadores diferentes con puntuaciones específicas:

1. **🌡️ Térmico (30 pts)**: Detecta elevación de temperatura por presencia corporal
2. **🏃 Movimiento (25 pts)**: Usa acelerómetro para detectar actividad
3. **❤️ Cardiovascular (35 pts)**: Monitorea frecuencia cardíaca válida
4. **👆 Contacto (20 pts)**: Detecta contacto directo con sensor MAX30102
5. **⏰ Temporal (10 pts)**: Valida consistencia en el tiempo

### **Sistema de Histéresis**
- **Entrada**: Requiere ≥60% de confianza para confirmar presencia
- **Salida**: Requiere ≤20% de confianza sostenida por 30 segundos
- **Evita**: Falsas detecciones por ruido temporal

### **Baseline Adaptativo**
- Aprende la temperatura normal de la cama vacía
- Se actualiza automáticamente cuando no hay presencia
- Usa filtro de paso bajo para estabilidad

## 🚀 Uso Básico

### **Importar y Crear Detector**
```python
from presence_detector import BedPresenceDetector

# Crear detector con configuración por defecto
detector = BedPresenceDetector()
```

### **Detectar Presencia**
```python
# Preparar datos de sensores
sensor_data = {
    'bed_temperature': 23.5,    # Temperatura de la cama (°C)
    'activity': 0.005,          # Nivel de actividad del acelerómetro
    'heart_rate': 72,           # Frecuencia cardíaca (BPM)
    'hr_valid': True,           # Si la HR es válida
    'finger_present': False     # Si hay contacto con MAX30102
}

# Detectar presencia
result = detector.detect_presence(sensor_data)

print(f"Ocupada: {result['occupied']}")
print(f"Confianza: {result['confidence']}%")
print(f"Tiempo en cama: {result['time_occupied']:.1f} min")
```

### **Resultado Típico**
```python
{
    'occupied': True,
    'confidence': 85.0,
    'indicators': {
        'thermal': True,
        'movement': True, 
        'heart_rate': True,
        'contact': False,
        'temporal': True
    },
    'time_occupied': 45.2,
    'temp_elevation': 2.3,
    'presence_changed': False
}
```

## ⚙️ Configuración

### **Parámetros Configurables (bed_config.py)**
```python
# Umbrales de confianza
PRESENCE_CONFIDENCE_THRESHOLD_ENTER = 60   # % para confirmar entrada
PRESENCE_CONFIDENCE_THRESHOLD_EXIT = 20    # % para confirmar salida

# Umbrales de sensores
PRESENCE_THERMAL_THRESHOLD = 1.5           # Elevación térmica mínima (°C)
PRESENCE_ACTIVITY_THRESHOLD = 0.001        # Actividad mínima
PRESENCE_HR_MIN = 40                       # HR mínima válida (BPM)
PRESENCE_HR_MAX = 150                      # HR máxima válida (BPM)

# Control temporal
PRESENCE_HISTORY_SIZE = 30                 # Tamaño historial (muestras)
PRESENCE_CONFIRMATION_TIME = 15            # Tiempo confirmación salida
```

### **Personalizar Configuración**
```python
# Crear detector con configuración personalizada
detector = BedPresenceDetector()

# Modificar umbrales después de la creación
detector.confidence_threshold_enter = 70   # Más estricto para entrada
detector.thermal_threshold = 2.0           # Requiere más calor corporal
```

## 🔧 Métodos Avanzados

### **Calibración de Baseline**
```python
# Calibrar con múltiples lecturas
temperature_readings = [20.1, 20.3, 19.9, 20.2, 20.0]
detector.calibrate_baseline(temperature_readings, duration_minutes=5)
```

### **Análisis Detallado**
```python
# Obtener información detallada de cada indicador
detailed = detector.get_detailed_indicators(sensor_data)

for indicator, data in detailed.items():
    print(f"{indicator}: {data['active']} - {data}")
```

### **Reset del Sistema**
```python
# Resetear estado (útil para reiniciar)
detector.reset_presence_state()
```

### **Información de Estado**
```python
# Obtener resumen completo
summary = detector.get_presence_summary()
print(f"Estado: {summary}")
```

## 📈 Integración con Sistema Principal

### **En SmartBedController**
```python
# Inicialización
self.presence_detector = BedPresenceDetector()

# En el bucle principal
sensor_data = {
    'bed_temperature': self.get_bed_temperature(),
    'activity': self.activity,
    'heart_rate': self.current_hr,
    'hr_valid': max_data['valid_hr'],
    'finger_present': max_data['finger_present']
}

presence_info = self.presence_detector.detect_presence(sensor_data)

# Solo procesar sueño si hay presencia
if presence_info['occupied']:
    # Procesar análisis de sueño
    pass
else:
    # Pausar análisis y resetear estados
    pass
```

## 🧪 Demo y Pruebas

### **Ejecutar Demo**
```bash
python demo_presence.py
```

La demo simula diferentes escenarios:
- 🛏️ Cama vacía inicial
- 🚶 Persona entrando
- 😴 Persona despierta
- 💤 Persona durmiendo  
- 🚶 Persona saliendo
- 🛏️ Cama vacía final

### **Salida de Demo**
```
🛏️ === DEMO: Detector de Presencia en Cama Inteligente ===
📊 Simulando diferentes escenarios de uso

🛏️ Cama vacía inicial (20 muestras)
--------------------------------------------------
📊 Muestra   1: ❌ Confianza:   0% | Indicadores: 0/5 | Temp: 19.8°C

🚶 Persona subiendo a la cama (15 muestras)
--------------------------------------------------
📊 Muestra  21: ✅ Confianza:  75% | Indicadores: 3/5 | Temp: 23.2°C
🔔 ¡CAMBIO DETECTADO! ENTRADA en la cama
```

## 🔍 Debugging y Monitoreo

### **Información de Debug**
```python
# Ver estado detallado
print(detector)  # Usa __str__ para resumen

# Monitorear cambios
if result['presence_changed']:
    change = "ENTRADA" if result['occupied'] else "SALIDA"
    print(f"🔔 Cambio detectado: {change}")
    
# Verificar indicadores activos
active_indicators = [k for k, v in result['indicators'].items() if v]
print(f"Indicadores activos: {active_indicators}")
```

### **Logs Típicos**
```
✅ Detector de presencia inicializado
   🎯 Umbral entrada: 60%
   🎯 Umbral salida: 20%
   🌡️ Umbral térmico: +1.5°C
   🏃 Umbral actividad: 0.001
   ❤️ Rango HR: 40-150 BPM

🌡️ Elevación térmica detectada: +2.3°C
🛏️ ✅ PRESENCIA DETECTADA en la cama
   📊 Confianza: 85%

🛏️ ❌ AUSENCIA DETECTADA - Cama vacía
   📊 Confianza: 15%
```

## 🎯 Ventajas del Diseño Modular

1. **🔧 Reutilizable**: Puede usarse en otros proyectos
2. **🧪 Testeable**: Fácil de probar de forma independiente
3. **⚙️ Configurable**: Parámetros ajustables sin modificar código
4. **📊 Observable**: Información detallada para análisis
5. **🛡️ Robusto**: Manejo de errores y estados edge case
6. **🚀 Eficiente**: Optimizado para tiempo real

## 📋 Requisitos

- Python 3.7+
- NumPy (para cálculos estadísticos)
- bed_config.py (para configuración)

## 🤝 Contribuir

Para mejorar el detector:

1. **Agregar nuevos indicadores** en `detect_presence()`
2. **Ajustar algoritmos** de puntuación
3. **Implementar ML** para patrones personalizados
4. **Optimizar rendimiento** para sistemas embebidos

---

**📝 Nota**: Este detector es parte del sistema de cama inteligente pero puede funcionar independientemente para cualquier aplicación de detección de presencia basada en sensores múltiples.

# 🛏️ Sistema de Cama Ortopédica Inteligente

Control automático de temperatura basado en estado de sueño, temperatura ambiente y **temperatura corporal**.

## 🎯 Funcionalidades

- **Detección de Estado de Sueño**: Combina acelerómetro + frecuencia cardíaca
- **Control de Temperatura Inteligente**: Ajusta automáticamente según el sueño y temperatura corporal
- **Monitoreo en Tiempo Real**: Seguimiento continuo de HR, SpO2 y temperatura
- **Seguridad**: Límites de temperatura y alertas de frecuencia cardíaca + fiebre

## 📊 Estados de Sueño y Temperatura (4 Estados)

| Estado | Descripción | Rango Temperatura | HR Típica | Actividad |
|--------|-------------|-------------------|-----------|-----------|
| 🌅 **DESPIERTO** | Actividad normal | 20-24°C | >75 BPM | >0.7 |
| 😴 **SUEÑO LIGERO** | Poco movimiento | 18-22°C | 55-75 BPM | 0.01-0.7 |
| 🌙 **SUEÑO REM** | HR alta + micro-mov | 19-23°C | ≥70 BPM | <0.008 |
| 🌌 **SUEÑO PROFUNDO** | Sin movimiento | 16-20°C | <55 BPM | <0.01 |

## 🎯 **Arquitectura de Sensores**

### **1. MAX30102 (I2C: 0x57)**
- **Función**: Oximetría (SpO2) + Frecuencia cardíaca + Temperatura ambiente
- **Ubicación**: Dedo (sensor principal)
- **Datos**: HR, SpO2, Temperatura ambiente del entorno

### **2. MMA8452Q (I2C: 0x1D)**  
- **Función**: Acelerómetro 3-axis para detección de movimiento
- **Ubicación**: Cama/colchón
- **Datos**: Actividad física durante el sueño

### **3. AHT10 (I2C: 0x38)**
- **Función**: Temperatura corporal + Humedad de la piel
- **Ubicación**: **Pulsera** (contacto directo con piel)
- **Datos**: Temperatura corporal real del usuario para detección de fiebre

## 🔧 Hardware Requerido

### Obligatorio
- **Raspberry Pi** con I2C habilitado
- **MAX30102** (I2C 0x57): Oximetría + HR + Temperatura ambiente
- **MMA8452Q** (I2C 0x1D): Acelerómetro 3-axis
- **AHT10** (I2C 0x38): Temperatura corporal en pulsera 🏃‍♂️

### Sistema de Temperatura (implementar según tu hardware)
- Resistencias calefactoras / Módulo Peltier
- Ventiladores para enfriamiento
- Válvulas de agua caliente/fría (implementación actual)
- Relés/MOSFETs para control de potencia

## 🚀 Instalación

1. **Dependencias Python**:
```bash
pip install -r requirements.txt
```

2. **Script de instalación Windows**:
```powershell
./install.ps1
```

3. **Habilitar I2C en Raspberry Pi**:
```bash
sudo raspi-config
# Interfacing Options > I2C > Yes
sudo reboot
```

4. **Verificar sensores**:
```bash
sudo i2cdetect -y 1
# Debe mostrar 0x1D (MMA8452Q), 0x57 (MAX30102), 0x38 (AHT10)
```

## 🧪 Pruebas

### Probar MAX30102
```bash
python test_max30102.py
```

### Probar AHT10 en pulsera
```bash
python test_aht10_wristband.py
```

### Sistema completo
```bash
python smart_bed_controller.py
```

## ⚙️ Configuración

### 1. Configurar Bluetooth HR
```bash
python scan.py
# Copiar dirección MAC del dispositivo
```

### 2. Editar `bed_config.py`:
```python
HR_DEVICE_ADDRESS = "XX:XX:XX:XX:XX:XX"  # Tu dispositivo real
GPIO_HEATING_PIN = 18    # Pin para calefacción
GPIO_COOLING_PIN = 19    # Pin para enfriamiento
```

### 3. Configurar umbrales según tus necesidades:
```python
ACTIVITY_THRESHOLD_DEEP_SLEEP = 0.01   # Sensibilidad sueño profundo
HR_THRESHOLD_DEEP_SLEEP = 55           # HR para sueño profundo
TEMP_DEEP_SLEEP = {"min": 16, "max": 20}  # Rango temperatura sueño profundo
```

## 🎮 Uso

### Modo Principal (con Hardware Real)
```python
from smart_bed_controller import SmartBedController
import asyncio

async def main():
    bed = SmartBedController("XX:XX:XX:XX:XX:XX", "2A37")
    await bed.start_monitoring()

asyncio.run(main())
```

### Modo Simulación (para pruebas)
```bash
python smart_bed_controller.py
```

## 📋 Archivos del Sistema

### 🔧 **Archivos PRINCIPALES**:
- `smart_bed_controller.py` - **Controlador principal de la cama**
- `bed_config.py` - **Configuración específica para cama**
- `monitor.py` - Monitoreo HR + acelerómetro (sin BD)
- `analyzer.py` - Algoritmos de análisis de sueño
- `config.py` - Configuración general de sensores
- `scan.py` - Buscar dispositivos Bluetooth HR

### 📁 **Drivers**:
- `drivers/MMA.py` - Driver del acelerómetro MMA8452Q

### 🗑️ **Archivos ELIMINADOS** (no necesarios):
- ~~`database.py`~~ - No almacenamos datos
- ~~`sleepLogger.py`~~ - Funcionalidad duplicada
- ~~`example_usage.py`~~ - Reemplazado por smart_bed_controller

## 🌡️ Implementación del Control de Temperatura

El sistema detecta el estado de sueño pero **TÚ DEBES IMPLEMENTAR** el control real del hardware:

```python
def control_bed_temperature(self, target_temp):
    # IMPLEMENTAR SEGÚN TU HARDWARE:
    
    if target_temp > current_temp:
        # Activar calefacción
        GPIO.output(HEATING_PIN, GPIO.HIGH)
        # O usar PWM para control gradual
        
    elif target_temp < current_temp:
        # Activar enfriamiento  
        GPIO.output(COOLING_PIN, GPIO.HIGH)
        
    else:
        # Mantener temperatura
        pass
```

## 🔒 Características de Seguridad

- **Límites de temperatura**: 10-30°C máximo
- **Alertas de HR**: <40 BPM o >120 BPM
- **Timeout de conexión**: Reconexión automática
- **Failsafe**: Temperatura por defecto si falla sensor

## 🛠️ Personalización

### Ajustar Sensibilidad
```python
# En bed_config.py
ACTIVITY_THRESHOLD_DEEP_SLEEP = 0.005  # Más sensible
HR_THRESHOLD_DEEP_SLEEP = 50           # HR más baja para sueño profundo
```

### Cambiar Rangos de Temperatura
```python
TEMP_DEEP_SLEEP = {"min": 15, "max": 18}  # Más fresco para sueño profundo
```

### Integrar con Home Assistant / IoT
```python
# Descomentar en bed_config.py:
MQTT_BROKER = "192.168.1.100"
MQTT_TOPIC_TEMP = "bedroom/bed/temperature"
```

## 📈 Monitoreo

El sistema muestra en tiempo real:
- Estado de sueño actual
- Temperatura objetivo
- Frecuencia cardíaca
- Nivel de actividad
- Acciones de control (calentar/enfriar)

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| No detecta acelerómetro | Verificar conexiones I2C y dirección 0x1D |
| HR no conecta | Usar `scan.py`, verificar que dispositivo esté en modo pairing |
| Temperatura no cambia | Implementar control real de hardware |
| Estado incorrecto | Ajustar umbrales en `bed_config.py` |

## 🔗 Integración con Hardware

### GPIO (Raspberry Pi)
```python
import RPi.GPIO as GPIO

# Configurar pines
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)  # Calefacción
GPIO.setup(19, GPIO.OUT)  # Enfriamiento
```

### PWM para Control Gradual
```python
heating_pwm = GPIO.PWM(18, 1000)  # 1kHz
heating_pwm.start(0)  # 0% duty cycle
heating_pwm.ChangeDutyCycle(50)   # 50% potencia
```

---

## 🎯 **¡Tu cama inteligente está lista!**

1. Configura tu hardware de temperatura
2. Ajusta `bed_config.py` según tus necesidades
3. Ejecuta `smart_bed_controller.py`
4. ¡Disfruta del sueño óptimo! 😴

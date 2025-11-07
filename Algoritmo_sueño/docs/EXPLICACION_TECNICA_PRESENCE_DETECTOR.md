# EXPLICACIÓN TÉCNICA DETALLADA - PRESENCE DETECTOR

## ARQUITECTURA GENERAL DEL SISTEMA

El módulo `presence_detector.py` implementa un sistema de detección de presencia en cama inteligente mediante fusión multi-sensor, utilizando cinco indicadores independientes que se combinan para generar un nivel de confianza global

## CLASE PRINCIPAL: BedPresenceDetector

### Atributos de Estado

**Estado de presencia actual:**
- `bed_occupied` (bool): Bandera que indica si la cama está ocupada actualmente
- `presence_confidence` (float): Nivel de confianza de presencia expresado en porcentaje (0-100)
- `presence_history` (list): Buffer circular que almacena los últimos N valores de confianza para análisis temporal
- `presence_start_time` (float): Timestamp Unix del momento en que se detectó entrada a la cama

**Valores de referencia (baseline):**
- `baseline_temperature` (float): Temperatura de referencia de la cama vacía, se actualiza dinámicamente cuando no hay presencia
- `baseline_activity` (float): Nivel de actividad de referencia (actualmente no utilizado)

**Parámetros configurables:**
- `confidence_threshold_enter`: Umbral de confianza requerido para detectar entrada (por defecto 60%)
- `confidence_threshold_exit`: Umbral de confianza bajo el cual se detecta salida (por defecto 20%)
- `thermal_threshold`: Incremento de temperatura sobre baseline para considerar presencia térmica (por defecto 1.5°C)
- `activity_threshold`: Nivel mínimo de actividad del acelerómetro para detectar movimiento (por defecto 0.001)
- `hr_min` y `hr_max`: Rango válido de frecuencia cardíaca (40-150 BPM)
- `history_size`: Tamaño del buffer de historial de confianza (30 muestras)
- `confirmation_time`: Número de muestras consecutivas de baja confianza requeridas para confirmar salida (15 muestras)

Todos estos parámetros se cargan desde el módulo `bed_config`, permitiendo ajuste sin modificar el código

## MÉTODO PRINCIPAL: detect_presence()

### Flujo de Procesamiento

El método recibe un diccionario `sensor_data` con las siguientes claves:
- `bed_temperature`: Lectura actual del sensor HTU21D
- `activity`: Magnitud del vector de aceleración del MMA8451
- `heart_rate`: Frecuencia cardíaca calculada por el MAX30102
- `hr_valid`: Booleano indicando si la medición de HR es confiable
- `finger_present`: Booleano indicando contacto físico con el sensor óptico

### Sistema de Puntuación Multi-Indicador

**1. INDICADOR TÉRMICO (máximo 40 puntos)**

Compara la temperatura actual con el baseline almacenado
```
temp_elevation = bed_temp - baseline_temperature
```

Criterios de puntuación:
- Si `temp_elevation > thermal_threshold`: otorga 30 puntos base
- Si `temp_elevation > thermal_threshold * 2`: otorga 10 puntos adicionales (total 40)

Fundamento: La presencia humana eleva la temperatura de la cama entre 1.5°C y 4°C debido al calor corporal, siendo uno de los indicadores más confiables de presencia sostenida

**2. INDICADOR DE MOVIMIENTO (máximo 25 puntos)**

Analiza la actividad del acelerómetro en tiempo real

Criterios de puntuación:
```
activity_score = min(25, int(activity * 25 / 0.1))
```

La puntuación escala linealmente con el nivel de actividad hasta un máximo de 25 puntos cuando la actividad alcanza 0.1

Fundamento: Los micro-movimientos durante el sueño (cambios de posición, respiración) generan actividad detectable por el acelerómetro, aunque una persona dormida puede permanecer inmóvil por períodos prolongados

**3. INDICADOR CARDIOVASCULAR (máximo 40 puntos)**

Valida la presencia de señal de frecuencia cardíaca válida

Criterios de puntuación:
- Si HR es válida y está en rango 40-150 BPM: otorga 35 puntos
- Si HR está en rango óptimo de sueño (50-80 BPM): otorga 5 puntos adicionales (total 40)

Fundamento: La detección de frecuencia cardíaca válida confirma presencia humana con alta certeza, ya que requiere contacto directo con el sensor óptico y flujo sanguíneo detectable

**4. INDICADOR DE CONTACTO (máximo 20 puntos)**

Detecta contacto físico con el sensor MAX30102 mediante análisis de la señal infrarroja

Criterios de puntuación:
- Si `finger_present == True`: otorga 20 puntos

Fundamento: El sensor óptico detecta contacto cuando la señal infrarroja reflejada supera un umbral mínimo, indicando que hay tejido biológico en contacto con el sensor

**5. INDICADOR TEMPORAL (máximo 10 puntos)**

Analiza la consistencia de la presencia en una ventana temporal deslizante

Criterios de puntuación:
```
avg_confidence = sum(presence_history[-5:]) / 5
```
- Si el promedio de los últimos 5 valores supera 50%: otorga 10 puntos

Fundamento: La presencia real en la cama genera señales consistentes en el tiempo, mientras que las falsas detecciones tienden a ser esporádicas

### Cálculo de Confianza Global

El puntaje final se calcula como suma de todos los indicadores activos, limitado a un máximo de 100%:
```
confidence = min(sum(all_indicators), 100)
```

Esta arquitectura permite que ningún sensor individual sea crítico, el sistema es tolerante a fallos de sensores individuales mientras múltiples indicadores estén activos

## MECANISMO DE HISTÉRESIS

### Propósito

Evitar transiciones rápidas (flapping) entre estados de presencia cuando las señales están cerca de los umbrales, proporcionando estabilidad al sistema

### Implementación en _update_presence_state()

**Detección de ENTRADA (vacía → ocupada):**
- Condición: `confidence >= threshold_enter` (60% por defecto)
- Acción inmediata: cambia estado a ocupada y registra timestamp

**Detección de SALIDA (ocupada → vacía):**
- Condición primaria: `confidence <= threshold_exit` (20% por defecto)
- Condición secundaria: requiere confirmación temporal
- Verificación: los últimos `confirmation_time` valores del historial deben ser todos ≤ 30%
- Acción: solo después de confirmar baja confianza sostenida cambia a vacía

Esta asimetría (entrada rápida, salida lenta) es intencional para evitar falsas detecciones de salida durante momentos de quietud prolongada (sueño profundo)

## GESTIÓN DE BASELINE TÉRMICO

### Inicialización

Al arrancar el sistema, `baseline_temperature` se inicializa con `None`, la primera lectura térmica se toma automáticamente como referencia inicial

### Actualización Dinámica (método update_baseline_temperature)

Solo se actualiza cuando `bed_occupied == False`, utilizando filtro de paso bajo con factor de suavizado α = 0.05:
```
baseline = (1 - α) * baseline_old + α * temp_current
```

Este filtro exponencial permite que el baseline se adapte lentamente a cambios de temperatura ambiente sin reaccionar a fluctuaciones breves

### Calibración Manual (método calibrate_baseline)

Permite establecer un baseline preciso mediante múltiples lecturas:
- Toma N lecturas durante un período definido (típicamente 5 minutos)
- Calcula la mediana (no la media) para eliminar outliers
- Reemplaza el baseline con este valor calibrado

El uso de la mediana es crucial para robustez contra lecturas anómalas

## MÉTODOS DE UTILIDAD Y DEBUGGING

**get_presence_summary()**

Retorna un diccionario con el estado global del detector, útil para monitoreo y logging

**get_detailed_indicators()**

Proporciona análisis granular de cada indicador individual con sus valores actuales, umbrales y estado de activación, esencial para debug y ajuste de parámetros

**reset_presence_state()**

Limpia completamente el estado del detector (limpia historial, resetea banderas), útil para reinicio del sistema sin reiniciar el proceso completo

**_get_time_occupied()**

Calcula el tiempo transcurrido desde que se detectó entrada a la cama, convertido a minutos para facilitar interpretación

## CONSIDERACIONES DE DISEÑO

**Fusión de Sensores**

El sistema implementa fusión de sensores heterogéneos (térmico, inercial, óptico) mediante suma ponderada de indicadores, cada sensor tiene un peso máximo diferente basado en su confiabilidad empírica

**Tolerancia a Fallos**

Si un sensor falla o proporciona datos inválidos, el sistema continúa operando con los sensores restantes, la confianza se ajusta automáticamente en ausencia de ciertos indicadores

**Adaptabilidad Temporal**

El baseline térmico se adapta automáticamente a cambios de temperatura ambiente durante períodos de ausencia, evitando falsas detecciones por cambios diurnos o estacionales

**Escalabilidad de Parámetros**

Todos los umbrales son configurables externamente mediante `bed_config`, permitiendo ajuste fino sin modificar código, facilitando optimización para diferentes entornos y usuarios

## RETORNO DEL MÉTODO PRINCIPAL

El método `detect_presence()` retorna un diccionario completo con:
- `occupied`: estado binario actual
- `confidence`: nivel de confianza porcentual
- `indicators`: diccionario con estado de cada indicador individual
- `time_occupied`: minutos transcurridos desde entrada
- `temp_elevation`: incremento térmico sobre baseline
- `presence_changed`: bandera indicando si hubo transición de estado en esta iteración

Este formato estructurado facilita la integración con módulos superiores del sistema de cama inteligente


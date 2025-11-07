### ARQUITECTURA GENERAL

El módulo `analyzer.py` centraliza funciones puramente analíticas para el procesamiento de señales fisiológicas y series de estados de sueño. No implementa clases de estado ni IO; su responsabilidad es recibir datos ya muestreados y preprocesados y devolver métricas o eventos de interés que puedan ser consumidos por otros módulos del sistema. La dependencia externa principal es NumPy, utilizada para cálculo vectorizado y estadísticas básicas.

### FUNCIONES PRINCIPALES

calculate_rmssd recibe una secuencia de intervalos interlatidos (IBI) y devuelve el RMSSD, la raíz cuadrática media de las diferencias sucesivas, o `None` si no hay suficientes muestras. Su implementación utiliza diferencias consecutivas (`np.diff`), el cuadrado de esas diferencias y la raíz de la media, proporcionando una medida de la variabilidad de corto plazo del ritmo cardíaco.

calculate_sdnn calcula la desviación estándar simple de la serie de IBI y devuelve `None` si la ventana no contiene al menos dos muestras. SDNN describe la variabilidad global en la ventana temporal considerada y se obtiene con `np.std`.

calculate_stress_score construye un índice heurístico de estrés en escala 0–100 a partir de una lectura de frecuencia cardíaca puntual (`hr`), `rmssd` y `sdnn`. La frecuencia cardíaca se normaliza respecto a un umbral inferior fijo y un tope configurable, RMSSD y SDNN se normalizan frente a máximos esperados y el componente de estrés asociado a variabilidad es `1 - normalized`, de forma que mayor variabilidad reduce la contribución al estrés. Los pesos y umbrales son parámetros internos (por defecto 0.4 para HR, 0.3 para RMSSD y 0.3 para SDNN) y la normalización se recorta para evitar valores superiores a 1. El resultado es útil para alertas rápidas pero requiere calibración en entornos reales.

calculate_sleep_quality produce una puntuación de calidad de sueño entre 0 y 100 combinando tres bloques de información: distribución de estados de sueño, consistencia de frecuencia cardíaca durante las fases de sueño y nivel de actividad durante el sueño. `sleep_states` se interpreta con 0=WAKE, 1=LIGHT_SLEEP, 2=REM_SLEEP y 3=DEEP_SLEEP y se asume que cada muestra representa un minuto de registro. La distribución de estados se compara contra proporciones heurísticas óptimas (por ejemplo deep ≈ 20%, REM ≈ 25%, light ≈ 50%, wake < 5%) y se convierte a un `sleep_distribution_score`. Si se entregan `hr_values` se calcula la variabilidad (desviación estándar) durante las muestras de sueño y se mapea a una puntuación donde menor variabilidad significa mejor resultado. Si se entregan `activity_levels` se penalizan niveles altos de actividad media durante sueño. La puntuación final combina distribución, HR y actividad con pesos 0.5, 0.25 y 0.25 respectivamente y se recorta entre 0 y 100. En ausencia de HR o actividad la función emplea valores neutros para mantener computabilidad con datos parciales.

analyze_sleep_transitions cuenta las transiciones entre estados consecutivos y devuelve una tupla `(transitions, fragmentation_index)`, donde `fragmentation_index` es transiciones por hora de sueño asumiendo 1 muestra = 1 minuto. Si la entrada tiene menos de dos muestras devuelve `(None, None)`.

detect_sleep_onset localiza el índice de la primera ventana sostenida de sueño mediante una búsqueda con ventana deslizante (`window_size`, por defecto 10 muestras) y un umbral de pertenencia de ventana (80% de muestras en estado > 0). Devuelve el índice de inicio o `None` si no se cumple la condición en la serie.

detect_wake_periods detecta segmentos contiguos de estado WAKE (0) y devuelve una lista de tuplas `(start_index, duration)` para los periodos cuya duración supera `min_duration` (por defecto 5 muestras). Este resultado facilita análisis posteriores de número y duración de despertares.

### ENTRADAS Y SALIDAS

Las funciones aceptan listas o arreglos numéricos; la mayoría realiza conversión implícita a `np.array` donde es necesario. `calculate_rmssd` y `calculate_sdnn` devuelven `float` o `None`; `calculate_stress_score` y `calculate_sleep_quality` devuelven `float` en rango 0–100; `analyze_sleep_transitions` devuelve `(int, float)` o `(None, None)`; `detect_sleep_onset` retorna un índice entero o `None`; `detect_wake_periods` retorna `list` de tuplas. El módulo no realiza parsing ni lectura de sensores, por lo que asume que los datos entregados ya están alineados temporalmente y sin valores no numéricos.

### SUPUESTOS Y CONSIDERACIONES TEMPORALES

Se asume que la serie `sleep_states` está uniformemente muestreada y que cada muestra representa un minuto. Los umbrales, pesos y máximos empleados en normalizaciones son heurísticos y deben calibrarse con datos reales del hardware y población objetivo. Las funciones no aplican filtrado de artefactos por defecto, por lo que entradas con picos o artefactos en IBI pueden sesgar RMSSD y SDNN.

### CASOS LÍMITE Y VALIDACIÓN

El módulo maneja casos sencillos de inexistencia de datos retornando `None` o valores neutros cuando procede, pero no sustituye por interpolaciones ni intenta recuperar series corruptas. Es recomendable validar entradas antes de llamar a las funciones: garantizar dtype numérico, longitudes mínimas y eliminar valores atípicos en IBI. Para validar la implementación se aconseja crear pruebas unitarias con casos sintéticos que incluyan ventanas insuficientes, sueño continuo, despertares cortos, ausencia de HR o actividad y valores extremos de HR para verificar saturación en `calculate_stress_score`.

### RECOMENDACIONES DE MEJORA Y USO EN PRODUCCIÓN

Agregar validación explícita de entradas y conversiones forzadas a `np.array` con comprobación de tipo numérico mejora robustez. Implementar un filtrado ligero o truncado de outliers en IBI antes de calcular RMSSD reduce sensibilidad a artefactos. Parametrizar umbrales y pesos para permitir ajustes desde `config/bed_config.py` o similar facilita calibración por entorno. Incluir un ejemplo en `examples/` y pruebas con `pytest` que cubran happy path y 1–2 edge cases aporta confianza en la integración.

### EJEMPLOS DE SALIDA (FORMATO)

Un consumidor del módulo puede esperar los siguientes formatos de retorno: para métricas escalares un `float` o `None`, para transiciones una tupla `(int, float)`, y para periodos de vigilia una lista de tuplas `(start_index, duration)`. Estos valores son adecuados para logging, visualización y fusión con otras señales en módulos superiores.

Si deseas, puedo añadir un ejemplo práctico en `examples/demo_analyzer.py` que muestre cómo llamar a cada función con datos sintéticos y un archivo de pruebas `tests/test_analyzer.py` que valide las salidas más relevantes. Indica si quieres que proceda con esos archivos y los ejecute con `pytest`.

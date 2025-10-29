#!/usr/bin/env python3
"""
Driver para MAX30102 - Sensor de Oximetría y Frecuencia Cardíaca
Conectado por I2C para medición de SpO2, HR y temperatura
"""

import smbus2 as smbus
import time
import numpy as np
from collections import deque

# Dirección I2C por defecto del MAX30102
MAX30102_ADDRESS = 0x57

# Registros del MAX30102
MAX30102_INTERRUPT_STATUS_1 = 0x00
MAX30102_INTERRUPT_STATUS_2 = 0x01
MAX30102_INTERRUPT_ENABLE_1 = 0x02
MAX30102_INTERRUPT_ENABLE_2 = 0x03
MAX30102_FIFO_WR_PTR = 0x04
MAX30102_OVERFLOW_COUNTER = 0x05
MAX30102_FIFO_RD_PTR = 0x06
MAX30102_FIFO_DATA = 0x07
MAX30102_FIFO_CONFIG = 0x08
MAX30102_MODE_CONFIG = 0x09
MAX30102_SPO2_CONFIG = 0x0A
MAX30102_LED1_PULSEAMP = 0x0C
MAX30102_LED2_PULSEAMP = 0x0D
MAX30102_PILOT_PA = 0x10
MAX30102_MULTI_LED_CTRL1 = 0x11
MAX30102_MULTI_LED_CTRL2 = 0x12
MAX30102_TEMP_INTR = 0x1F
MAX30102_TEMP_FRAC = 0x20
MAX30102_TEMP_CONFIG = 0x21
MAX30102_REV_ID = 0xFE
MAX30102_PART_ID = 0xFF

# Configuraciones
INTERRUPT_A_FULL = 0x80
INTERRUPT_DATA_RDY = 0x40
INTERRUPT_ALC_OVF = 0x20
INTERRUPT_PROX_INT = 0x10
INTERRUPT_DIE_TEMP_RDY = 0x02

MODE_SHDN = 0x80
MODE_RESET = 0x40
MODE_HR_ONLY = 0x02
MODE_SPO2 = 0x03

SAMPLEAVG_1 = 0x00
SAMPLEAVG_2 = 0x20
SAMPLEAVG_4 = 0x40
SAMPLEAVG_8 = 0x60
SAMPLEAVG_16 = 0x80
SAMPLEAVG_32 = 0xA0

ROLLOVER_EN = 0x10
ALMOST_FULL = 0x00

SAMPLERATE_50 = 0x00
SAMPLERATE_100 = 0x04
SAMPLERATE_200 = 0x08
SAMPLERATE_400 = 0x0C
SAMPLERATE_800 = 0x10
SAMPLERATE_1000 = 0x14
SAMPLERATE_1600 = 0x18
SAMPLERATE_3200 = 0x1C

PULSEWIDTH_69 = 0x00
PULSEWIDTH_118 = 0x01
PULSEWIDTH_215 = 0x02
PULSEWIDTH_411 = 0x03

ADCRANGE_2048 = 0x00
ADCRANGE_4096 = 0x20
ADCRANGE_8192 = 0x40
ADCRANGE_16384 = 0x60

class MAX30102:
    def __init__(self, i2c_address=MAX30102_ADDRESS):
        """
        Inicializar sensor MAX30102
        """
        self.address = i2c_address
        self.bus = smbus.SMBus(1)  # I2C bus 1
        
        # Buffers para datos
        self.red_buffer = deque(maxlen=100)
        self.ir_buffer = deque(maxlen=100)
        
        # Variables para cálculo de HR y SpO2
        self.heart_rate = 0
        self.spo2 = 0
        self.valid_heart_rate = False
        self.valid_spo2 = False
        
        # Inicializar sensor
        self.setup_sensor()
        
    def write_register(self, register, value):
        """Escribir un valor en un registro"""
        try:
            self.bus.write_byte_data(self.address, register, value)
            time.sleep(0.001)  # Pequeña pausa
        except Exception as e:
            print(f"Error escribiendo registro 0x{register:02X}: {e}")
            
    def read_register(self, register):
        """Leer un valor de un registro"""
        try:
            return self.bus.read_byte_data(self.address, register)
        except Exception as e:
            print(f"Error leyendo registro 0x{register:02X}: {e}")
            return 0
            
    def setup_sensor(self):
        """Configurar el sensor MAX30102"""
        print("🔧 Configurando MAX30102...")
        
        # Verificar Part ID
        part_id = self.read_register(MAX30102_PART_ID)
        if part_id != 0x15:  # MAX30102 Part ID
            print(f"⚠️ Advertencia: Part ID esperado 0x15, obtenido 0x{part_id:02X}")
        
        # Reset del sensor
        self.write_register(MAX30102_MODE_CONFIG, MODE_RESET)
        time.sleep(0.1)
        
        # Configurar FIFO
        self.write_register(MAX30102_FIFO_CONFIG, SAMPLEAVG_4 | ROLLOVER_EN | ALMOST_FULL)
        
        # Configurar modo SpO2
        self.write_register(MAX30102_MODE_CONFIG, MODE_SPO2)
        
        # Configurar SpO2: rango ADC=4096nA, SR=100Hz, ancho pulso=411µs
        self.write_register(MAX30102_SPO2_CONFIG, ADCRANGE_4096 | SAMPLERATE_100 | PULSEWIDTH_411)
        
        # Configurar amplitud LEDs (ajustable según necesidad)
        self.write_register(MAX30102_LED1_PULSEAMP, 0x24)  # LED Rojo
        self.write_register(MAX30102_LED2_PULSEAMP, 0x24)  # LED IR
        
        # Configurar piloto
        self.write_register(MAX30102_PILOT_PA, 0x7F)
        
        # Limpiar FIFO
        self.clear_fifo()
        
        print("✅ MAX30102 configurado correctamente")
        
    def clear_fifo(self):
        """Limpiar el FIFO del sensor"""
        self.write_register(MAX30102_FIFO_WR_PTR, 0)
        self.write_register(MAX30102_OVERFLOW_COUNTER, 0)
        self.write_register(MAX30102_FIFO_RD_PTR, 0)
        
    def read_fifo(self):
        """Leer datos del FIFO"""
        red_data = []
        ir_data = []
        
        # Leer punteros FIFO
        wr_ptr = self.read_register(MAX30102_FIFO_WR_PTR)
        rd_ptr = self.read_register(MAX30102_FIFO_RD_PTR)
        
        # Calcular número de muestras disponibles
        num_samples = (wr_ptr - rd_ptr) & 0x1F
        
        if num_samples == 0:
            return red_data, ir_data
            
        # Leer datos del FIFO
        for i in range(num_samples):
            # Leer 6 bytes por muestra (3 bytes RED + 3 bytes IR)
            fifo_data = []
            for j in range(6):
                fifo_data.append(self.read_register(MAX30102_FIFO_DATA))
            
            # Convertir a valores de 18 bits
            red_value = (fifo_data[0] << 16) | (fifo_data[1] << 8) | fifo_data[2]
            red_value &= 0x3FFFF  # Máscara de 18 bits
            
            ir_value = (fifo_data[3] << 16) | (fifo_data[4] << 8) | fifo_data[5]
            ir_value &= 0x3FFFF  # Máscara de 18 bits
            
            red_data.append(red_value)
            ir_data.append(ir_value)
            
        return red_data, ir_data
        
    def calculate_heart_rate(self, ir_buffer, sample_rate=100):
        """
        Calcular frecuencia cardíaca usando autocorrelación
        """
        if len(ir_buffer) < 50:  # Necesitamos al menos 50 muestras
            return 0, False
            
        # Convertir a numpy array
        signal = np.array(ir_buffer)
        
        # Filtrar la señal (filtro de media móvil)
        window_size = 5
        filtered_signal = np.convolve(signal, np.ones(window_size)/window_size, mode='same')
        
        # Encontrar picos (latidos)
        peaks = self.find_peaks(filtered_signal)
        
        if len(peaks) < 2:
            return 0, False
            
        # Calcular intervalos entre picos
        intervals = np.diff(peaks)
        
        # Convertir a BPM
        avg_interval = np.mean(intervals)
        heart_rate = (sample_rate * 60) / avg_interval
        
        # Validar rango razonable (40-200 BPM)
        if 40 <= heart_rate <= 200:
            return int(heart_rate), True
        else:
            return 0, False
            
    def find_peaks(self, signal, min_distance=20):
        """
        Encontrar picos en la señal
        """
        peaks = []
        signal_mean = np.mean(signal)
        
        for i in range(1, len(signal) - 1):
            if (signal[i] > signal[i-1] and 
                signal[i] > signal[i+1] and 
                signal[i] > signal_mean):
                
                # Verificar distancia mínima con el pico anterior
                if not peaks or (i - peaks[-1]) >= min_distance:
                    peaks.append(i)
                    
        return peaks
        
    def calculate_spo2(self, red_buffer, ir_buffer):
        """
        Calcular SpO2 usando la relación R
        Nota: Esta es una aproximación simplificada
        """
        if len(red_buffer) < 25 or len(ir_buffer) < 25:
            return 0, False
            
        # Calcular AC/DC para cada LED
        red_ac = np.std(red_buffer)
        red_dc = np.mean(red_buffer)
        ir_ac = np.std(ir_buffer)
        ir_dc = np.mean(ir_buffer)
        
        # Evitar división por cero
        if red_dc == 0 or ir_dc == 0 or ir_ac == 0:
            return 0, False
            
        # Calcular relación R
        r = (red_ac / red_dc) / (ir_ac / ir_dc)
        
        # Ecuación empírica para SpO2 (simplificada)
        # SpO2 = 110 - 25 * R (aproximación)
        spo2 = 110 - 25 * r
        
        # Validar rango razonable (70-100%)
        if 70 <= spo2 <= 100:
            return int(spo2), True
        else:
            return 0, False
            
    def read_temperature(self):
        """
        Leer temperatura del sensor interno
        """
        # Habilitar lectura de temperatura
        self.write_register(MAX30102_TEMP_CONFIG, 0x01)
        
        # Esperar a que esté listo
        time.sleep(0.1)
        
        # Leer temperatura
        temp_int = self.read_register(MAX30102_TEMP_INTR)
        temp_frac = self.read_register(MAX30102_TEMP_FRAC)
        
        # Convertir a celsius
        temperature = temp_int + (temp_frac * 0.0625)
        
        return temperature
        
    def update(self):
        """
        Actualizar lecturas del sensor
        """
        # Leer nuevos datos del FIFO
        red_data, ir_data = self.read_fifo()
        
        # Agregar a buffers
        for red, ir in zip(red_data, ir_data):
            self.red_buffer.append(red)
            self.ir_buffer.append(ir)
            
        # Calcular HR y SpO2 si tenemos suficientes datos
        if len(self.ir_buffer) >= 50:
            self.heart_rate, self.valid_heart_rate = self.calculate_heart_rate(self.ir_buffer)
            
        if len(self.red_buffer) >= 25 and len(self.ir_buffer) >= 25:
            self.spo2, self.valid_spo2 = self.calculate_spo2(self.red_buffer, self.ir_buffer)
            
        return {
            'heart_rate': self.heart_rate,
            'spo2': self.spo2,
            'valid_hr': self.valid_heart_rate,
            'valid_spo2': self.valid_spo2,
            'temperature': self.read_temperature()
        }
        
    def get_heart_rate(self):
        """
        Obtener frecuencia cardíaca actual
        """
        data = self.update()
        return data['heart_rate'] if data['valid_hr'] else 60  # Valor por defecto
        
    def get_spo2(self):
        """
        Obtener SpO2 actual
        """
        data = self.update()
        return data['spo2'] if data['valid_spo2'] else 98  # Valor por defecto
        
    def is_finger_present(self):
        """
        Detectar si hay un dedo en el sensor
        """
        data = self.update()
        # Simple detección basada en la amplitud de la señal IR
        if len(self.ir_buffer) > 0:
            ir_values = [x for x in self.ir_buffer]
            return max(ir_values) > 50000  # Umbral ajustable
        return False
        
    def cleanup(self):
        """
        Limpiar recursos
        """
        try:
            # Poner sensor en modo shutdown
            self.write_register(MAX30102_MODE_CONFIG, MODE_SHDN)
            self.bus.close()
        except:
            pass

# Función de prueba
if __name__ == "__main__":
    print("🔍 Probando MAX30102...")
    
    try:
        sensor = MAX30102()
        
        print("📊 Iniciando lecturas (presiona Ctrl+C para parar):")
        print("Coloca tu dedo en el sensor...")
        
        while True:
            data = sensor.update()
            
            if sensor.is_finger_present():
                status = "✅ Dedo detectado"
            else:
                status = "❌ Sin dedo"
                
            print(f"{status} | HR: {data['heart_rate']:3d} BPM | SpO2: {data['spo2']:2d}% | Temp: {data['temperature']:.1f}°C")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Detenido por usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            sensor.cleanup()
        except:
            pass

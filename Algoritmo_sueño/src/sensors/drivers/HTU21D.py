#!/usr/bin/env python3
"""
Driver para sensor HTU21D - Temperatura y Humedad
Usado para medir la temperatura directa de la cama inteligente
I2C Address: 0x40
"""

import time
import struct

class HTU21D:
    """
    Driver para sensor HTU21D de temperatura y humedad
    Medición precisa de temperatura de la cama
    """
    
    # Direcciones I2C
    HTU21D_ADDR = 0x40
    
    # Comandos del sensor
    CMD_TEMP_HOLD = 0xE3      # Medir temperatura con hold master
    CMD_TEMP_NO_HOLD = 0xF3   # Medir temperatura sin hold master
    CMD_HUMID_HOLD = 0xE5     # Medir humedad con hold master  
    CMD_HUMID_NO_HOLD = 0xF5  # Medir humedad sin hold master
    CMD_WRITE_USER_REG = 0xE6 # Escribir registro de usuario
    CMD_READ_USER_REG = 0xE7  # Leer registro de usuario
    CMD_SOFT_RESET = 0xFE     # Reset suave
    
    def __init__(self, address=None):
        """
        Inicializar sensor HTU21D
        
        Args:
            address: Dirección I2C (por defecto 0x40)
        """
        self.address = address if address is not None else self.HTU21D_ADDR
        self.bus = None
        self.available = False
        
        try:
            import smbus2
            self.bus = smbus2.SMBus(1)  # Usar I2C bus 1 (GPIO 2/3)
            
            # Verificar conexión con reset suave
            self.soft_reset()
            time.sleep(0.1)  # Esperar reset
            
            # Leer registro de usuario para verificar comunicación
            user_reg = self.read_user_register()
            if user_reg is not None:
                self.available = True
                print(f"✅ HTU21D inicializado en dirección 0x{self.address:02X}")
                print(f"   Registro de usuario: 0x{user_reg:02X}")
            else:
                print(f"❌ HTU21D no responde en dirección 0x{self.address:02X}")
                
        except ImportError:
            print("⚠️ smbus2 no disponible - HTU21D en modo simulación")
        except Exception as e:
            print(f"❌ Error inicializando HTU21D: {e}")
    
    def soft_reset(self):
        """Realizar reset suave del sensor"""
        if not self.bus:
            return False
            
        try:
            self.bus.write_byte(self.address, self.CMD_SOFT_RESET)
            time.sleep(0.015)  # Esperar 15ms después del reset
            return True
        except Exception as e:
            print(f"❌ Error en reset HTU21D: {e}")
            return False
    
    def read_user_register(self):
        """Leer registro de usuario"""
        if not self.bus:
            return None
            
        try:
            return self.bus.read_byte_data(self.address, self.CMD_READ_USER_REG)
        except Exception as e:
            print(f"❌ Error leyendo registro HTU21D: {e}")
            return None
    
    def _crc8_check(self, data, crc):
        """
        Verificar CRC8 (polinomio 0x131)
        HTU21D usa CRC8 para verificación de integridad
        """
        remainder = data
        for i in range(8):
            if remainder & 0x80:
                remainder = (remainder << 1) ^ 0x131
            else:
                remainder = remainder << 1
            remainder = remainder & 0xFF
        return remainder == crc
    
    def read_temperature(self):
        """
        Leer temperatura en grados Celsius
        
        Returns:
            float: Temperatura en °C, None si error
        """
        if not self.bus or not self.available:
            # Simular temperatura de cama entre 18-25°C
            import random
            return 20.0 + random.uniform(-2.0, 5.0)
            
        try:
            # Enviar comando de lectura de temperatura (no hold master)
            self.bus.write_byte(self.address, self.CMD_TEMP_NO_HOLD)
            
            # Esperar conversión (máximo 50ms según datasheet)
            time.sleep(0.055)
            
            # Leer 3 bytes: MSB, LSB, CRC
            data = self.bus.read_i2c_block_data(self.address, 0, 3)
            
            if len(data) != 3:
                print(f"❌ HTU21D: Datos insuficientes ({len(data)} bytes)")
                return None
            
            msb, lsb, crc = data
            
            # Combinar MSB y LSB (los últimos 2 bits son status)
            raw_temp = (msb << 8) | lsb
            raw_temp &= 0xFFFC  # Quitar bits de status (últimos 2 bits)
            
            # Verificar CRC si está disponible
            temp_data = (msb << 8) | (lsb & 0xFC)
            if not self._crc8_check(temp_data, crc):
                print("⚠️ HTU21D: Error de CRC en temperatura")
                # Continuar pero marcar como posible error
            
            # Convertir a temperatura según fórmula del datasheet
            # T = -46.85 + 175.72 * (Stemp / 2^16)
            temperature = -46.85 + 175.72 * (raw_temp / 65536.0)
            
            # Validar rango razonable para temperatura de cama
            if 10.0 <= temperature <= 40.0:
                return round(temperature, 2)
            else:
                print(f"⚠️ HTU21D: Temperatura fuera de rango: {temperature:.1f}°C")
                return None
                
        except Exception as e:
            print(f"❌ Error leyendo temperatura HTU21D: {e}")
            return None
    
    def read_humidity(self):
        """
        Leer humedad relativa en porcentaje
        
        Returns:
            float: Humedad en %, None si error
        """
        if not self.bus or not self.available:
            # Simular humedad entre 40-60%
            import random
            return 50.0 + random.uniform(-10.0, 10.0)
            
        try:
            # Enviar comando de lectura de humedad (no hold master)
            self.bus.write_byte(self.address, self.CMD_HUMID_NO_HOLD)
            
            # Esperar conversión (máximo 16ms según datasheet)
            time.sleep(0.020)
            
            # Leer 3 bytes: MSB, LSB, CRC
            data = self.bus.read_i2c_block_data(self.address, 0, 3)
            
            if len(data) != 3:
                print(f"❌ HTU21D: Datos insuficientes para humedad ({len(data)} bytes)")
                return None
            
            msb, lsb, crc = data
            
            # Combinar MSB y LSB
            raw_humid = (msb << 8) | lsb
            raw_humid &= 0xFFFC  # Quitar bits de status
            
            # Verificar CRC
            humid_data = (msb << 8) | (lsb & 0xFC)
            if not self._crc8_check(humid_data, crc):
                print("⚠️ HTU21D: Error de CRC en humedad")
            
            # Convertir a humedad según fórmula del datasheet
            # RH = -6 + 125 * (Shumid / 2^16)
            humidity = -6.0 + 125.0 * (raw_humid / 65536.0)
            
            # Validar rango (0-100%)
            humidity = max(0.0, min(100.0, humidity))
            
            return round(humidity, 1)
            
        except Exception as e:
            print(f"❌ Error leyendo humedad HTU21D: {e}")
            return None
    
    def read_data(self):
        """
        Leer temperatura y humedad
        
        Returns:
            dict: {'temperature': float, 'humidity': float, 'valid': bool}
        """
        temperature = self.read_temperature()
        humidity = self.read_humidity()
        
        return {
            'temperature': temperature,
            'humidity': humidity,
            'valid': temperature is not None and humidity is not None,
            'sensor_available': self.available
        }
    
    def is_available(self):
        """Verificar si el sensor está disponible"""
        return self.available
    
    def cleanup(self):
        """Limpiar recursos"""
        if self.bus:
            try:
                self.bus.close()
                print("✅ HTU21D bus cerrado")
            except:
                pass
    
    def __del__(self):
        """Destructor - limpiar recursos"""
        self.cleanup()

# Función de prueba
def test_htu21d():
    """Función de prueba para el sensor HTU21D"""
    print("🧪 Probando sensor HTU21D...")
    
    sensor = HTU21D()
    
    if sensor.is_available():
        print("✅ Sensor HTU21D conectado correctamente")
        
        for i in range(5):
            data = sensor.read_data()
            print(f"Lectura {i+1}:")
            print(f"  🌡️ Temperatura: {data['temperature']:.2f}°C")
            print(f"  💧 Humedad: {data['humidity']:.1f}%")
            print(f"  ✅ Válido: {data['valid']}")
            print()
            time.sleep(2)
    else:
        print("❌ Sensor HTU21D no disponible - Modo simulación")
        data = sensor.read_data()
        print(f"  🌡️ Temperatura (sim): {data['temperature']:.2f}°C")
        print(f"  💧 Humedad (sim): {data['humidity']:.1f}%")
    
    sensor.cleanup()

if __name__ == "__main__":
    test_htu21d()

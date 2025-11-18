#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <HTU21D.h>
#include <MAX30105.h>
#include <heartRate.h>
#include <SparkFun_MMA8452Q.h>

// Configuración WiFi
const char* ssid = "xiaomi";
const char* password = "raspberry";

// Configuración MQTT
const char* mqtt_server = "172.22.39.27";  // IP de tu Raspberry Pi
const int mqtt_port = 1883;
const char* mqtt_user = "tu_usuario";  // opcional
const char* mqtt_password = "tu_password";  // opcional

WiFiClient espClient;
PubSubClient client(espClient);

// Sensores
HTU21D htu21d;
MAX30105 max30102;
MMA8452Q accel;

// Variables de estado
bool htu21d_ok = false;
bool max30102_ok = false;
bool accel_ok = false;

// Variables para Heart Rate (basado en ejemplo oficial)
const byte RATE_SIZE = 4; // Increase this for more averaging. 4 is good.
byte rates[RATE_SIZE]; // Array of heart rates
byte rateSpot = 0;
long lastBeat = 0; // Time at which the last beat occurred
float beatsPerMinute = 0;
int beatAvg = 0;

void setup_wifi() {
  delay(10);
  WiFi.begin(ssid, password);
  
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 30) {
    delay(500);
    intentos++;
  }
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32Client_Sensores", mqtt_user, mqtt_password)) {
      client.publish("sensores/status", "ESP32 conectado - Iniciando lecturas de sensores");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  // Inicializar I2C en pines del ESP32-C3
  Wire.begin(6, 7);  // SDA=GPIO6, SCL=GPIO7
  Wire.setClock(100000);  // 100kHz
  
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  
  // Conectar MQTT
  reconnect();
  
  client.publish("sensores/info", "Inicializando sensores en ESP32-C3");
  client.publish("sensores/config", "I2C: SDA=GPIO6, SCL=GPIO7, 100kHz");
  
  // Inicializar HTU21D (Temperatura y Humedad)
  if (htu21d.begin()) {
    htu21d_ok = true;
    client.publish("sensores/htu21d", "HTU21D inicializado correctamente");
  } else {
    htu21d_ok = false;
    client.publish("sensores/error", "HTU21D no encontrado");
  }
  
  // Inicializar MAX30105 (Pulso cardíaco)
  if (max30102.begin(Wire, I2C_SPEED_FAST)) { // Usar I2C_SPEED_FAST como en el ejemplo
    max30102.setup(); // Configuración por defecto como en el ejemplo
    max30102.setPulseAmplitudeRed(0x0A); // Turn Red LED to low to indicate sensor is running
    max30102.setPulseAmplitudeGreen(0);  // Turn off Green LED
    max30102_ok = true;
    client.publish("sensores/max30105", "MAX30105 inicializado correctamente");
  } else {
    max30102_ok = false;
    client.publish("sensores/error", "MAX30105 no encontrado");
  }
  
  // Inicializar MMA8452Q (Acelerómetro)
  if (accel.begin()) {
    accel.setScale(SCALE_2G);
    accel.setDataRate(ODR_12);
    accel_ok = true;
    client.publish("sensores/mma8452q", "MMA8452Q inicializado correctamente - Escala 2g");
  } else {
    accel_ok = false;
    client.publish("sensores/error", "MMA8452Q no encontrado");
  }
  
  // Resumen de inicialización
  String resumen = "Sensores activos: ";
  if (htu21d_ok) resumen += "HTU21D ";
  if (max30102_ok) resumen += "MAX30105 ";
  if (accel_ok) resumen += "MMA8452Q ";
  if (!htu21d_ok && !max30102_ok && !accel_ok) resumen += "NINGUNO";
  
  client.publish("sensores/resumen", resumen.c_str());
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Leer sensores cada 2 segundos
  static unsigned long lastMsg = 0;
  static int contador = 0;
  unsigned long now = millis();
  
  if (now - lastMsg > 2000) {  // Cada 2 segundos
    lastMsg = now;
    contador++;
    
    client.publish("sensores/contador", String(contador).c_str());
    
    // Enviar resumen cada 10 ciclos (cada 20 segundos)
    if (contador % 10 == 1) {
      String resumen = "Sensores activos: ";
      if (htu21d_ok) resumen += "HTU21D ";
      if (max30102_ok) resumen += "MAX30105 ";
      if (accel_ok) resumen += "MMA8452Q ";
      if (!htu21d_ok && !max30102_ok && !accel_ok) resumen += "NINGUNO";
      
      client.publish("sensores/resumen", resumen.c_str());
    }
    
    // ==================== LEER HTU21D ====================
    if (htu21d_ok) {
      if (htu21d.measure()) {
        float temperatura = htu21d.getTemperature();
        float humedad = htu21d.getHumidity();
        
        if (!isnan(temperatura) && temperatura >= -40 && temperatura <= 125) {
          client.publish("sensores/temperatura", String(temperatura, 2).c_str());
        } else {
          client.publish("sensores/error", "HTU21D: temperatura invalida");
        }
        
        if (!isnan(humedad) && humedad >= 0 && humedad <= 100) {
          client.publish("sensores/humedad", String(humedad, 2).c_str());
        } else {
          client.publish("sensores/error", "HTU21D: humedad invalida");
        }
      } else {
        client.publish("sensores/error", "HTU21D: fallo en medicion");
      }
    }
    
    // ==================== LEER MAX30105 ====================
    if (max30102_ok) {
      // Leer valor IR directamente (como en el ejemplo oficial)
      long irValue = max30102.getIR();
      
      // Publicar valor IR
      client.publish("sensores/ir_value", String(irValue).c_str());
      
      // Usar algoritmo oficial de SparkFun para detectar latidos
      if (checkForBeat(irValue) == true) {
        // ¡Detectamos un latido!
        long delta = millis() - lastBeat;
        lastBeat = millis();
        
        beatsPerMinute = 60 / (delta / 1000.0);
        
        if (beatsPerMinute < 255 && beatsPerMinute > 20) {
          // Almacenar esta lectura en el array
          rates[rateSpot++] = (byte)beatsPerMinute;
          rateSpot %= RATE_SIZE; // Wrap variable
          
          // Calcular promedio de lecturas
          beatAvg = 0;
          for (byte x = 0; x < RATE_SIZE; x++)
            beatAvg += rates[x];
          beatAvg /= RATE_SIZE;
        }
      }
      
      // Estado del dedo (igual que en el ejemplo oficial)
      String finger_status = (irValue < 50000) ? "no_detectado" : "detectado";
      
      // Publicar datos de heart rate
      client.publish("sensores/bpm", String((int)beatsPerMinute).c_str());
      client.publish("sensores/bpm_avg", String(beatAvg).c_str());
      client.publish("sensores/finger_status", finger_status.c_str());
      
      // JSON con datos del corazón
      String heart_json = "{\"ir\":" + String(irValue) + 
                        ",\"bpm\":" + String((int)beatsPerMinute) + 
                        ",\"bpm_avg\":" + String(beatAvg) + 
                        ",\"finger\":\"" + finger_status + "\"}";
      client.publish("sensores/heart_data", heart_json.c_str());
    }
    
    // ==================== LEER MMA8452Q ====================
    if (accel_ok) {
      if (accel.available()) {
        accel.read();
        
        float x = accel.getCalculatedX();
        float y = accel.getCalculatedY();
        float z = accel.getCalculatedZ();
        
        // Verificar valores válidos
        if (x >= -4 && x <= 4) {
          client.publish("sensores/accel_x", String(x, 3).c_str());
        }
        if (y >= -4 && y <= 4) {
          client.publish("sensores/accel_y", String(y, 3).c_str());
        }
        if (z >= -4 && z <= 4) {
          client.publish("sensores/accel_z", String(z, 3).c_str());
        }
        
        // Calcular magnitud
        float magnitud = sqrt(x*x + y*y + z*z);
        client.publish("sensores/accel_mag", String(magnitud, 3).c_str());
        
        // Detectar orientación
        String orientacion = "indefinida";
        if (abs(z) > abs(x) && abs(z) > abs(y)) {
          if (z > 0.5) orientacion = "boca_arriba";
          else if (z < -0.5) orientacion = "boca_abajo";
        }
        client.publish("sensores/orientacion", orientacion.c_str());
        
        // Detectar movimiento
        client.publish("sensores/movimiento", (magnitud > 1.5) ? "SI" : "NO");
        
        // Datos JSON combinados
        String accel_json = "{\"x\":" + String(x,3) + ",\"y\":" + String(y,3) + ",\"z\":" + String(z,3) + ",\"mag\":" + String(magnitud,3) + "}";
        client.publish("sensores/accel_datos", accel_json.c_str());
        
      } else {
        client.publish("sensores/error", "MMA8452Q: sin nuevos datos");
      }
    }
    
    // Estado del sistema
    client.publish("sistema/wifi_ip", WiFi.localIP().toString().c_str());
    client.publish("sistema/wifi_status", (WiFi.status() == WL_CONNECTED) ? "conectado" : "desconectado");
    client.publish("sistema/uptime", String(millis() / 1000).c_str());
    
    // Estado de sensores cada 5 ciclos (cada 10 segundos)
    if (contador % 5 == 0) {
      client.publish("sensores/estado_htu21d", htu21d_ok ? "OK" : "ERROR");
      client.publish("sensores/estado_max30105", max30102_ok ? "OK" : "ERROR");
      client.publish("sensores/estado_mma8452q", accel_ok ? "OK" : "ERROR");
  }
  }
}
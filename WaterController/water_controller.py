"""
Sistema de Control de Flujo de Agua para Raspberry Pi Zero 2 W
Controla una bomba eléctrica (GPIO 22) y una válvula eléctrica (GPIO 5)
para bombear agua a través de una manguera hacia una cama.
La bomba opera con pausas programadas para evitar sobrecalentamiento.
"""

import RPi.GPIO as GPIO
import time
import signal
import sys

# Configuración de pines GPIO
PIN_BOMBA = 22      # GPIO 22 - Bomba eléctrica
PIN_VALVULA = 5    # GPIO 5 - Válvula eléctrica
# Alimentación: Pin 1 (3.3V o 5V según tu circuito)
# Ground: Pin 6

# Tiempos de operación (en segundos)
TIEMPO_BOMBA_ON = 300      # Tiempo que la bomba está encendida (5 minutos)
TIEMPO_BOMBA_OFF = 30      # Tiempo de pausa para evitar sobrecalentamiento (30 segundos)
TIEMPO_TOTAL_FLUJO = 1200  # Tiempo total de flujo de agua (20 minutos)

# Variable de control para detener el programa de forma segura
running = True

def signal_handler(sig, frame):
    """Maneja la señal de interrupción (Ctrl+C) para apagar todo de forma segura"""
    global running
    print("\n\nDeteniendo el sistema de forma segura...")
    running = False

def setup_gpio():
    """Configura los pines GPIO"""
    # Usa numeración BCM (GPIO)
    GPIO.setmode(GPIO.BCM)
    
    # Configura los pines como salidas
    GPIO.setup(PIN_BOMBA, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_VALVULA, GPIO.OUT, initial=GPIO.LOW)
    
    print("GPIO configurado correctamente")
    print(f"Bomba: GPIO {PIN_BOMBA}")
    print(f"Válvula: GPIO {PIN_VALVULA}")

def encender_bomba():
    """Enciende la bomba eléctrica para iniciar el flujo de agua"""
    GPIO.output(PIN_BOMBA, GPIO.HIGH)
    print("✓ Bomba ENCENDIDA - Flujo de agua activo")

def apagar_bomba():
    """Apaga la bomba eléctrica y detiene el flujo de agua"""
    GPIO.output(PIN_BOMBA, GPIO.LOW)
    print("✗ Bomba APAGADA - Flujo de agua detenido")

def abrir_valvula():
    """Abre la válvula eléctrica para permitir el paso del agua"""
    GPIO.output(PIN_VALVULA, GPIO.HIGH)
    print("✓ Válvula ABIERTA - Paso de agua habilitado")

def cerrar_valvula():
    """Cierra la válvula eléctrica y bloquea el paso del agua"""
    GPIO.output(PIN_VALVULA, GPIO.LOW)
    print("✗ Válvula CERRADA - Paso de agua bloqueado")

def cleanup():
    """Limpia la configuración GPIO y apaga todo"""
    apagar_bomba()
    cerrar_valvula()
    GPIO.cleanup()
    print("Sistema apagado y GPIO limpiado")

def ciclo_flujo_agua():
    """
    Ejecuta un ciclo completo de flujo de agua:
    1. Abre la válvula para permitir el paso del agua
    2. Enciende la bomba con pausas para evitar sobrecalentamiento
    3. Bombea agua por la manguera hacia la cama durante 20 minutos
    4. Cierra todo al finalizar
    """
    global running
    
    print("\n" + "="*50)
    print("INICIANDO FLUJO DE AGUA")
    print("="*50)
    
    # Abrir válvula
    abrir_valvula()
    time.sleep(2)  # Espera 2 segundos para que la válvula se abra completamente
    
    # Tiempo total de operación
    tiempo_total = 0
    tiempo_objetivo = TIEMPO_TOTAL_FLUJO
    
    # Ciclo de bomba con pausas
    while tiempo_total < tiempo_objetivo and running:
        # Calcula cuánto tiempo queda
        tiempo_restante = tiempo_objetivo - tiempo_total
        
        # Enciende la bomba
        encender_bomba()
        
        # Determina el tiempo de operación (el menor entre el tiempo configurado y el tiempo restante)
        tiempo_operacion = min(TIEMPO_BOMBA_ON, tiempo_restante)
        minutos = int(tiempo_operacion / 60)
        segundos = int(tiempo_operacion % 60)
        print(f"Bombeando agua por {minutos}m {segundos}s...")
        time.sleep(tiempo_operacion)
        
        # Actualiza el tiempo total
        tiempo_total += tiempo_operacion
        
        # Apaga la bomba
        apagar_bomba()
        
        # Si aún falta tiempo, hace una pausa
        if tiempo_total < tiempo_objetivo and running:
            print(f"Pausa de seguridad: {TIEMPO_BOMBA_OFF} segundos (evita sobrecalentamiento)")
            time.sleep(TIEMPO_BOMBA_OFF)
    
    # Cerrar válvula
    cerrar_valvula()
    
    print("="*50)
    print("FLUJO DE AGUA COMPLETADO")
    print("="*50 + "\n")

def main():
    """Función principal"""
    global running
    
    # Configura el manejador de señales para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Configurar GPIO
        setup_gpio()
        
        print("\n" + "="*50)
        print("SISTEMA DE FLUJO DE AGUA ACTIVADO")
        print("="*50)
        print(f"Tiempo de operación de bomba: {TIEMPO_BOMBA_ON}s ({int(TIEMPO_BOMBA_ON/60)} minutos)")
        print(f"Tiempo de pausa de bomba: {TIEMPO_BOMBA_OFF}s")
        print(f"Tiempo total de flujo: {TIEMPO_TOTAL_FLUJO}s ({int(TIEMPO_TOTAL_FLUJO/60)} minutos)")
        print("\nPresiona Ctrl+C para detener el sistema de forma segura")
        print("="*50 + "\n")
        
        # Espera 3 segundos antes de iniciar
        print("Iniciando en 3 segundos...")
        time.sleep(3)
        
        # Ejecuta el ciclo de flujo de agua continuamente
        while running:
            ciclo_flujo_agua()
            if running:
                print(f"\nEsperando 5 minutos antes del próximo ciclo...")
                time.sleep(300)  # Espera 5 minutos entre ciclos
        
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        # Limpieza al salir
        cleanup()
        print("\nPrograma finalizado")

if __name__ == "__main__":
    main()

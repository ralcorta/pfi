#!/usr/bin/env python3
"""
Capturador simple de tráfico TCP AWS VPC Mirroring con modelo de IA
"""
import signal
import sys
import argparse

from app.sensor.src.tcp_traffic_capture import TCPTrafficCapture


def main():
    parser = argparse.ArgumentParser(description='Capturador TCP con modelo de IA')
    parser.add_argument('--interface', default='eth0', help='Interfaz de red')
    parser.add_argument('--filter', default='tcp', help='Filtro de captura')
    parser.add_argument('--model', help='Ruta al modelo .keras')
    
    args = parser.parse_args()
    
    # Crear capturador
    capture = TCPTrafficCapture(args.interface, args.filter, args.model)
    
    # Configurar shutdown graceful
    def signal_handler(signum, frame):
        print(f"\n🛑 Deteniendo captura...")
        capture.stop_capture()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Iniciar captura
        capture.start_capture()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    finally:
        capture.stop_capture()

if __name__ == "__main__":
    main()
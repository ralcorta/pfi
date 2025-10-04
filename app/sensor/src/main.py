#!/usr/bin/env python3
"""
Servidor UDP para recibir tráfico del VPC Mirroring con modelo de IA
"""
import signal
import sys
import argparse

from app.sensor.src.sensor_server import SensorServer


def main():
    parser = argparse.ArgumentParser(description='Servidor UDP para VPC Mirroring con modelo de IA')
    parser.add_argument('--interface', default='eth0', help='Interfaz de red')
    parser.add_argument('--port', type=int, default=4789, help='Puerto UDP para recibir tráfico')
    parser.add_argument('--model', help='Ruta al modelo .keras')
    
    args = parser.parse_args()
    
    server = SensorServer(args.port, args.model)
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Deteniendo servidor UDP...")
        server.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    finally:
        server.stop_server()

if __name__ == "__main__":
    main()
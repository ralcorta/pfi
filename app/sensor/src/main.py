#!/usr/bin/env python3
"""
Servidor híbrido UDP + HTTP para recibir tráfico del VPC Mirroring con modelo de IA
"""
import signal
import sys
import argparse

from app.sensor.src.hybrid_server import HybridServer


def main():
    parser = argparse.ArgumentParser(description='Servidor híbrido UDP + HTTP para VPC Mirroring con modelo de IA')
    parser.add_argument('--udp-port', type=int, default=4789, help='Puerto UDP para recibir tráfico')
    parser.add_argument('--http-port', type=int, default=8080, help='Puerto HTTP para API')
    parser.add_argument('--model', help='Ruta al modelo .keras')
    
    args = parser.parse_args()
    
    # Crear servidor híbrido
    server = HybridServer(args.udp_port, args.http_port, args.model)
    
    # Configurar shutdown graceful
    def signal_handler(signum, frame):
        print(f"\n🛑 Deteniendo servidor híbrido...")
        server.stop_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Iniciar servidores
        server.start_servers()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    finally:
        server.stop_servers()

if __name__ == "__main__":
    main()
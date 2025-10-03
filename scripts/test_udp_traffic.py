#!/usr/bin/env python3
"""
Script para simular tráfico UDP hacia el sensor en puerto 4789
Útil para testear el sensor sin deployar VPC Traffic Mirroring
"""

import socket
import time
import random
import struct

def create_fake_packet():
    """Crea un paquete TCP falso para simular tráfico de red"""
    # Simular un paquete TCP básico
    src_ip = f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"
    dst_ip = f"10.0.{random.randint(1,255)}.{random.randint(1,255)}"
    src_port = random.randint(1024, 65535)
    dst_port = random.randint(80, 443)
    
    # Crear payload simulado
    payload = f"GET / HTTP/1.1\r\nHost: {dst_ip}\r\n\r\n".encode()
    
    return payload

def send_udp_traffic(target_host="localhost", target_port=4789, duration=60):
    """Envía tráfico UDP simulado al sensor"""
    print(f"🎯 Enviando tráfico UDP a {target_host}:{target_port}")
    print(f"⏱️  Duración: {duration} segundos")
    print("🛑 Presiona Ctrl+C para detener")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        start_time = time.time()
        packet_count = 0
        
        while time.time() - start_time < duration:
            # Crear paquete falso
            packet = create_fake_packet()
            
            # Enviar al sensor
            sock.sendto(packet, (target_host, target_port))
            packet_count += 1
            
            if packet_count % 10 == 0:
                print(f"📦 Enviados {packet_count} paquetes...")
            
            # Pausa entre paquetes
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Detenido. Total enviados: {packet_count} paquetes")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Simular tráfico UDP para testear el sensor')
    parser.add_argument('--host', default='localhost', help='Host del sensor')
    parser.add_argument('--port', type=int, default=4789, help='Puerto del sensor')
    parser.add_argument('--duration', type=int, default=60, help='Duración en segundos')
    
    args = parser.parse_args()
    
    send_udp_traffic(args.host, args.port, args.duration)

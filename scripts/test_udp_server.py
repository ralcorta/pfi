#!/usr/bin/env python3
"""
Script de prueba para el servidor UDP del sensor
"""
import socket
import time
import struct
from scapy.all import IP, TCP, Raw

def create_test_packet():
    """Crea un paquete TCP de prueba"""
    # Crear un paquete TCP simple
    packet = IP(src="192.168.1.100", dst="192.168.1.200") / TCP(sport=12345, dport=80) / Raw(b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    return packet

def create_mirrored_packet(original_packet):
    """Simula el encapsulado del VPC Traffic Mirroring"""
    # VPC Traffic Mirroring añade metadatos al inicio
    # Para esta prueba, añadimos 16 bytes de metadatos ficticios
    metadata = b'\x00' * 16  # Metadatos ficticios del mirroring
    
    # Convertir el paquete Scapy a bytes
    packet_bytes = bytes(original_packet)
    
    # Combinar metadatos + paquete original
    mirrored_packet = metadata + packet_bytes
    return mirrored_packet

def test_udp_server():
    """Prueba el servidor UDP enviando paquetes de prueba"""
    server_host = "localhost"
    server_port = 4789
    
    print(f"🧪 Enviando paquetes de prueba al servidor UDP {server_host}:{server_port}")
    
    # Crear socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        for i in range(100):
            test_packet = create_test_packet()
            mirrored_packet = create_mirrored_packet(test_packet)
            
            sock.sendto(mirrored_packet, (server_host, server_port))
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"❌ Error enviando paquetes: {e}")
    finally:
        sock.close()
        print("✅ Prueba completada")

if __name__ == "__main__":
    test_udp_server()

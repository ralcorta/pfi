#!/usr/bin/env python3
"""
Script para enviar tráfico de prueba al sensor local.
Simula paquetes VXLAN para probar el buffer de 20 paquetes.
"""

import socket
import time
import sys
from scapy.all import Ether, IP, UDP, Raw
from scapy.layers.vxlan import VXLAN

def create_vxlan_packet(payload_data: bytes, vni: int = 256) -> bytes:
    """Crea un paquete VXLAN con payload interno."""
    # Crear paquete Ethernet interno
    inner_eth = Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP() / Raw(load=payload_data)
    
    # Envolver en VXLAN
    vxlan = VXLAN(vni=vni, flags=0x08)
    vxlan_packet = inner_eth
    # Nota: Scapy no tiene un constructor directo de VXLAN sobre UDP,
    # así que construimos manualmente
    vxlan_header = bytes([0x08, 0x00, 0x00, 0x00])  # Flags + Reserved
    vxlan_header += vni.to_bytes(3, 'big')  # VNI (24 bits)
    vxlan_header += bytes([0x00])  # Reserved
    
    # UDP payload es VXLAN header + inner packet
    udp_payload = vxlan_header + bytes(inner_eth)
    
    return udp_payload

def send_test_packets(host: str = "localhost", port: int = 4789, count: int = 100):
    """Envía paquetes de prueba al sensor."""
    print(f"🚀 Enviando {count} paquetes UDP a {host}:{port}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        for i in range(count):
            # Crear payload de prueba
            payload = f"TEST-PACKET-{i}-{int(time.time())}".encode()
            
            # Crear paquete VXLAN
            packet = create_vxlan_packet(payload, vni=256)
            
            # Enviar paquete
            sock.sendto(packet, (host, port))
            
            if (i + 1) % 20 == 0:
                print(f"  ✓ {i + 1} paquetes enviados...")
            
            # Pequeña pausa para no saturar
            time.sleep(0.01)
        
        print(f"✅ {count} paquetes enviados correctamente")
        
    except Exception as e:
        print(f"❌ Error enviando paquetes: {e}")
        sys.exit(1)
    finally:
        sock.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Envía tráfico de prueba al sensor local")
    parser.add_argument("--host", default="localhost", help="Host del sensor (default: localhost)")
    parser.add_argument("--port", type=int, default=4789, help="Puerto UDP (default: 4789)")
    parser.add_argument("--count", type=int, default=100, help="Número de paquetes a enviar (default: 100)")
    
    args = parser.parse_args()
    
    send_test_packets(args.host, args.port, args.count)

#!/usr/bin/env python3
import socket
import time
import os
from scapy.all import *
from scapy.layers.vxlan import VXLAN
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP

# Configuración desde variables de entorno
SENSOR_HOST = os.getenv("SENSOR_HOST", "localhost")
SENSOR_PORT = int(os.getenv("SENSOR_PORT", "4789"))
VNI = 1

print(f"🔧 Configuración:")
print(f"   Sensor: {SENSOR_HOST}:{SENSOR_PORT}")
print(f"   VNI: {VNI}")

# Crear paquete Ethernet sintético
eth_packet = Ether(src="00:11:22:33:44:55", dst="00:66:77:88:99:aa") / \
             IP(src="192.168.1.100", dst="192.168.1.200") / \
             UDP(sport=12345, dport=80) / \
             Raw(b"GET / HTTP/1.1\r\nHost: test.com\r\n\r\n")

print(f"📦 Paquete Ethernet creado: {len(bytes(eth_packet))} bytes")

# Crear paquete VXLAN
vxlan_packet = IP(dst=SENSOR_HOST) / UDP(dport=SENSOR_PORT) / \
               VXLAN(vni=VNI, flags=0x08) / \
               Raw(bytes(eth_packet))

print(f"📦 Paquete VXLAN creado: {len(bytes(vxlan_packet))} bytes")


# Enviar paquetes cada 1 segundo
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"📤 Enviando 25 paquetes UDP por lote a {SENSOR_HOST}:{SENSOR_PORT}")

try:
    count = 0
    while True:
        # Enviar 25 paquetes rápidamente
        for i in range(25):
            count += 1
            sock.sendto(bytes(vxlan_packet), (SENSOR_HOST, SENSOR_PORT))
            print(f"✅ [{count}] Enviado paquete VXLAN ({len(bytes(vxlan_packet))} bytes) - VNI: {VNI}")
        
        # Esperar 1 segundo después de 25 paquetes
        print("⏸️  Esperando 1 segundo...")
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Deteniendo envío...")
finally:
    sock.close()

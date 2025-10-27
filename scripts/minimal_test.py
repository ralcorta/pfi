#!/usr/bin/env python3
"""
Generador de paquetes VXLAN (payload = VXLAN header + Ether(original_frame))
Pensado para emular lo que recibe un sensor que escucha UDP/4789 (AWS Traffic Mirroring).
- Envia SOLO el payload VXLAN por socket UDP -> kernel añade IP/UDP externos.
- Si querés enviar IP/UDP externos a mano, usar socket RAW o scapy.send (requiere root).
"""

import socket
import time
import os
from pathlib import Path
from scapy.all import rdpcap, Ether, Raw
from scapy.layers.vxlan import VXLAN

# Config desde env
SENSOR_HOST = os.getenv("SENSOR_HOST", "127.0.0.1")  # ip del sensor receptor
SENSOR_PORT = int(os.getenv("SENSOR_PORT", "4789"))  # puerto UDP que escucha el sensor (4789)
VNI = int(os.getenv("VNI", "1"))                     # VNI a usar
SRC_IP = os.getenv("SRC_IP", None)                   # opcional: bind local a IP origen (ej. 10.0.0.5)
SEND_INTERVAL = float(os.getenv("SEND_INTERVAL", "0.0"))  # pausa entre paquetes (s). 0 -> lo más rápido posible

print("🔧 Configuration:")
print(f"   Sensor: {SENSOR_HOST}:{SENSOR_PORT}")
print(f"   VNI: {VNI}")
if SRC_IP:
    print(f"   Source bind IP: {SRC_IP}")
print(f"   Send interval: {SEND_INTERVAL}s")

# Paquete ethernet sintético de ejemplo (frame interno)
eth_packet = Ether(src="00:11:22:33:44:55", dst="00:66:77:88:99:aa") / \
             ("IP(src=192.168.1.100,dst=192.168.1.200)/UDP(sport=12345,dport=80)/Raw(b'GET / HTTP/1.1\\r\\nHost: test.com\\r\\n\\r\\n')")

print(f"📦 Paquete Ethernet sintético (inner frame): {len(bytes(Ether(bytes(eth_packet))))} bytes")

# Cargar PCAP (opcional)
zeus_pcap_path = Path(__file__).parent / "Zeus.pcap"
zeus_packets = []
if zeus_pcap_path.exists():
    try:
        zeus_packets = rdpcap(str(zeus_pcap_path))
        print(f"✅ Cargados {len(zeus_packets)} paquetes desde {zeus_pcap_path.name}")
    except Exception as e:
        print(f"❌ Error cargando {zeus_pcap_path}: {e}")
        zeus_packets = []
else:
    print("⚠️ No se encontró Zeus.pcap — se usará solo tráfico sintético")

def make_vxlan_payload(inner_bytes: bytes, vni: int) -> bytes:
    """
    Construye el payload UDP que contiene [VXLAN header][Ether(inner_bytes)...]
    Devolvemos solo BYTES: esto es lo que se enviará como payload UDP.
    """
    # Si inner_bytes ya contienen un frame Ether, parseamos para asegurarnos que scapy lo serialice correctamente
    try:
        inner_eth = Ether(inner_bytes)
    except Exception:
        # fallback: envolver como Raw si no es un ether válido
        inner_eth = Raw(inner_bytes)

    vx = VXLAN(vni=vni) / inner_eth
    return bytes(vx)

def send_packet(sock: socket.socket, inner_packet_bytes: bytes):
    """
    Envía por UDP al receptor: payload = VXLAN + inner frame.
    """
    payload = make_vxlan_payload(inner_packet_bytes, VNI)
    # Enviar SOLO payload: el kernel añadirá IP/UDP externos (dst=SENSOR_HOST:SENSOR_PORT)
    sock.sendto(payload, (SENSOR_HOST, SENSOR_PORT))
    return len(payload)

def main_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Opcional: fijar IP de origen si se requiere (ej.: para simulaciones donde el mirror source tiene IP específica)
    if SRC_IP:
        try:
            sock.bind((SRC_IP, 0))
        except Exception as e:
            print(f"⚠️ No se pudo bindear a SRC_IP {SRC_IP}: {e}")

    print(f"📤 Enviando paquetes a {SENSOR_HOST}:{SENSOR_PORT} (payload VXLAN). Presiona Ctrl+C para detener.")
    count = 0
    start_time = time.time()
    try:
        while True:
            elapsed = time.time() - start_time

            # Fase 1: primeros 10s -> tráfico sintético rápido
            # if elapsed < 10:
                # enviar un lote de paquetes sintéticos
            #     for i in range(25):
            #         count += 1
            #        sent = send_packet(sock, bytes(Ether(bytes(eth_packet))))
            #         # pequeño print reducido para no saturar la consola
            #         if count % 50 == 0:
            #             print(f"→ Enviados {count} paquetes (último payload {sent} bytes)")
            #         #if SEND_INTERVAL:
            #         #    time.sleep(SEND_INTERVAL)

            # Fase 2: si hay pcap, enviarlo secuencialmente
            #elif zeus_packets:
            print("🚨 Enviando paquetes Zeus desde pcap...")
            for i, p in enumerate(zeus_packets):
                # rdpcap retorna un objeto scapy Packet; si el pcap incluye capas de enlace, bytes(p) contiene Ethernet frame.
                inner = bytes(p)
                count += 1
                sent = send_packet(sock, inner)
                # progresión simple
                if i % 100 == 0:
                    print(f"→ Zeus {i+1}/{len(zeus_packets)} | total enviados: {count}")
                #if SEND_INTERVAL:
                #    time.sleep(SEND_INTERVAL)

            print("✅ Envío de Zeus completado — reiniciando ciclo de prueba")
            start_time = time.time()

            #else:
            #    # si no hay pcap disponible, volver a fase de prueba
            #    print("⚠️ No hay pcap; volviendo a tráfico sintético")
            #    start_time = time.time()

    except KeyboardInterrupt:
        print("\n🛑 Interrupción por usuario")
    finally:
        sock.close()
        print(f"🧾 Total paquetes enviados: {count}")

if __name__ == "__main__":
    main_loop()

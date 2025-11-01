#!/usr/bin/env python3
"""
Script para enviar paquetes desde un archivo PCAP al sensor local.
Envuelve los paquetes en VXLAN como lo hace Traffic Mirroring.
"""

import socket
import time
import sys
from scapy.all import rdpcap, Ether, IP, UDP, Raw
from scapy.layers.vxlan import VXLAN

def create_vxlan_packet(inner_packet: bytes, vni: int = 256) -> bytes:
    """
    Crea un paquete VXLAN envolviendo el paquete interno.
    
    Formato VXLAN:
    - Flags (1 byte): 0x08 (I bit set)
    - Reserved (3 bytes): 0x000000
    - VNI (3 bytes): Network Identifier
    - Reserved (1 byte): 0x00
    - Inner packet (Ethernet frame)
    """
    # Header VXLAN
    vxlan_header = bytes([0x08, 0x00, 0x00, 0x00])  # Flags + Reserved
    vxlan_header += vni.to_bytes(3, 'big')  # VNI (24 bits)
    vxlan_header += bytes([0x00])  # Reserved
    
    # Payload UDP es VXLAN header + paquete interno
    udp_payload = vxlan_header + inner_packet
    
    return udp_payload

def send_pcap_to_sensor(pcap_file: str, host: str = "localhost", port: int = 4789, 
                        delay: float = 0.0, max_packets: int = None):
    """Lee un PCAP y envía los paquetes al sensor envolviéndolos en VXLAN."""
    
    print(f"📖 Leyendo archivo PCAP: {pcap_file}")
    
    try:
        # Leer PCAP
        packets = rdpcap(pcap_file)
        total_packets = len(packets)
        
        if max_packets:
            packets = packets[:max_packets]
            print(f"📦 Limité a {max_packets} paquetes de {total_packets} totales")
        
        print(f"📦 Encontrados {len(packets)} paquetes para enviar")
        print(f"🚀 Enviando paquetes a {host}:{port}...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sent_count = 0
        skipped_count = 0
        
        for i, packet in enumerate(packets):
            try:
                # Obtener bytes del paquete Ethernet
                if Ether in packet:
                    # Si ya tiene capa Ethernet, usar esos bytes directamente
                    inner_bytes = bytes(packet)
                elif IP in packet:
                    # Si solo tiene IP, agregar Ethernet dummy
                    inner_packet = Ether() / packet
                    inner_bytes = bytes(inner_packet)
                else:
                    # Si no tiene Ethernet ni IP, crear estructura mínima
                    inner_packet = Ether() / Raw(load=bytes(packet))
                    inner_bytes = bytes(inner_packet)
                
                # Crear paquete VXLAN
                vxlan_packet = create_vxlan_packet(inner_bytes, vni=256)
                
                # Enviar paquete
                sock.sendto(vxlan_packet, (host, port))
                sent_count += 1
                
                # Mostrar progreso cada 20 paquetes
                if (sent_count % 20 == 0):
                    print(f"  ✓ {sent_count} paquetes enviados...")
                
                # Delay si se especifica
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                skipped_count += 1
                if skipped_count <= 5:  # Mostrar solo los primeros 5 errores
                    print(f"  ⚠️ Error procesando paquete {i}: {e}")
                continue
        
        sock.close()
        
        print(f"\n✅ Envío completado:")
        print(f"   - Paquetes enviados: {sent_count}")
        if skipped_count > 0:
            print(f"   - Paquetes omitidos: {skipped_count}")
        
    except FileNotFoundError:
        print(f"❌ Error: Archivo no encontrado: {pcap_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error procesando PCAP: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Envía paquetes desde un PCAP al sensor local envolviéndolos en VXLAN"
    )
    parser.add_argument(
        "pcap_file",
        help="Ruta al archivo PCAP"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host del sensor (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4789,
        help="Puerto UDP (default: 4789)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay entre paquetes en segundos (default: 0.0)"
    )
    parser.add_argument(
        "--max-packets",
        type=int,
        default=None,
        help="Máximo número de paquetes a enviar (default: todos)"
    )
    
    args = parser.parse_args()
    
    send_pcap_to_sensor(
        args.pcap_file,
        args.host,
        args.port,
        args.delay,
        args.max_packets
    )

import logging
import threading
import time
import os
import sys
from scapy.all import sniff, TCP, rdpcap, IP

from app.sensor.src.ai_model_processor import AIModelProcessor
from app.sensor.src.utils.dynamo_client import DynamoClient

class TCPTrafficCapture:
    """Capturador de tráfico TCP con procesamiento de IA"""
    
    def __init__(self, interface="eth0", filter_str="tcp", model_path=None):
        self.interface = interface
        self.filter_str = filter_str
        self.running = False
        self.packet_count = 0
        self.demo_packages = []
        
        self.ai_processor = AIModelProcessor(model_path)
        self.dynamo_table = DynamoClient("demo-pcap-control")
        self.demo_mode = False 
        
        # Variables para la consola interactiva
        self.current_packet_info = "Esperando paquetes..."
        self.malware_detections = 0
        self.last_update = time.time()
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def clear_screen(self):
        """Limpia la pantalla de la consola"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def update_console(self):
        """Actualiza la consola con información en tiempo real"""
        self.clear_screen()
        print("=" * 80)
        print("🛡️  SENSOR DE TRÁFICO TCP CON IA")
        print("=" * 80)
        print(f"📡 Interfaz: {self.interface}")
        print(f"🔍 Filtro: {self.filter_str}")
        print(f"🎯 Estado: {'DEMO' if self.demo_mode else 'LIVE'}")
        print("-" * 80)
        print(f"📦 Paquetes procesados: {self.packet_count}")
        print(f"🚨 Detecciones de malware: {self.malware_detections}")
        print("-" * 80)
        print(f"📋 Último paquete: {self.current_packet_info}")
        print("-" * 80)
        print("Presiona Ctrl+C para detener")
        print("=" * 80)
    
    def save_malware_detection(self, malware_type, confidence, source_ip):
        malware_id = f"malware_{malware_type}_{source_ip}"
        
        existing = self.dynamo_table.get({"id": malware_id})
        if existing:
            existing["packet_count"] += 1
            existing["last_seen"] = int(time.time())
            self.dynamo_table.save(existing)
        else:
            self.dynamo_table.save({
                "id": malware_id,
                "malware_type": malware_type,
                "confidence": confidence,
                "source_ip": source_ip,
                "packet_count": 1,
                "first_seen": int(time.time())
            })
    
    def get_malware_detections(self):
        try:
            response = self.dynamo_table.table.scan(
                FilterExpression='begins_with(id, :prefix)',
                ExpressionAttributeValues={':prefix': 'malware_'}
            )
            return response.get('Items', [])
        except Exception as e:
            self.logger.error(f"Error obteniendo malware: {e}")
            return []
    
    def extract_packages_from_pcap(self, file):
        packets = rdpcap(file)
        return packets
    
    def demo_thread(self):
        while self.running:
            data = self.dynamo_table.get({"id": "demo_control"})
            if data and data.get("execute_demo") == "true":
                self.demo_mode = True
                self.current_packet_info = "🎭 Iniciando modo demo..."
                self.update_console()
                
                pcap_file = data.get("pcap_file", "")
                if not pcap_file:
                    pcap_file = "models/data/small/Malware/Zeus.pcap"

                self.demo_packages = self.extract_packages_from_pcap(pcap_file)
                self.dynamo_table.save({"id": "demo_control", "execute_demo": "false"})
                
                self.current_packet_info = f"🎭 Procesando paquetes del demo..."
                self.update_console()
                
                for packet in self.demo_packages:
                    packet = self.demo_packages.pop(0)
                    self.process_packet(packet, demo=True)
                
                self.demo_mode = False
                self.current_packet_info = "✅ Demo completado - Volviendo a modo LIVE"
                self.update_console()
            time.sleep(1)
    
    def packet_handler(self, packet):
        """Manejador de paquetes TCP capturados"""
        if self.demo_mode is True:
            return
        
        self.process_packet(packet, demo=False)

    def process_packet(self, packet, demo=False):
        if not self.running:
            return

        # Solo procesar paquetes TCP
        if not packet.haslayer(TCP):
            return
        
        self.packet_count += 1
        
        # Extraer información TCP
        tcp_layer = packet[TCP]
        src_port = tcp_layer.sport
        dst_port = tcp_layer.dport
        
        # Enviar paquete al procesador de IA
        result = self.ai_processor.process_packet(packet)
        
        if packet.haslayer(IP):
            source_ip = packet[IP].src
        else:
            source_ip = "N/A"
        
        # Actualizar información del paquete actual
        mode = "[DEMO]" if demo else "[LIVE]"
        self.current_packet_info = f"{mode} {source_ip} #{self.packet_count} - {src_port} -> {dst_port}"
        
        # Actualizar consola cada 0.5 segundos para no saturar
        current_time = time.time()
        if current_time - self.last_update > 0.5:
            self.update_console()
            self.last_update = current_time
        
        # Si hay resultado del modelo, mostrarlo
        if result:
            if result['is_malware']:
                self.malware_detections += 1
                self.current_packet_info += f" 🚨 MALWARE DETECTADO! (Confianza: {result['confidence']:.2f})"
                self.update_console()  # Actualizar inmediatamente si hay malware
                
                if packet.haslayer(IP):
                    source_ip = packet[IP].src
                    malware_type = result.get('malware_type', 'unknown')
                    self.save_malware_detection(malware_type, result['confidence'], source_ip)
    
    def start_capture(self):
        self.ai_processor.load_model()
        self.running = True
        
        self.update_console()
        
        threading.Thread(target=self.demo_thread, daemon=True).start()
        
        try:
            self.logger.info(f"🎯 Iniciando captura en interfaz {self.interface}...")
            sniff(
                iface=self.interface,
                filter=self.filter_str,
                prn=self.packet_handler,
                store=False
            )
        except Exception as e:
            self.logger.error(f"❌ Error en captura: {e}")
        finally:
            self.stop_capture()
    
    def stop_capture(self):
        """Detiene la captura"""
        self.running = False
        self.logger.info(f"🛑 Captura detenida. Total de paquetes TCP: {self.packet_count}")
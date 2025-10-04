import logging
import socket
import threading
import time
from scapy.all import IP, TCP

from app.sensor.src.model_service import ModelService
from app.sensor.src.utils.config import Config
from app.sensor.src.utils.dynamo_client import DynamoClient

class SensorServer:
    """Servidor UDP para recibir tráfico del VPC Mirroring en puerto 4789"""
    
    def __init__(self, port=4789, model_path=None):
        self.port = port
        self.running = False
        self.packet_count = 0
        self.demo_packages = []
        self.last_result = 0
        self.model_service = ModelService(model_path)
        self.dynamo_table = DynamoClient("demo-pcap-control")
        self.demo_mode = False
        self.current_packet_info = "Esperando paquetes..."
        self.malware_detections = 0
        self.last_update = time.time()
        self.socket = None
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def clear_screen(self):
        """Limpia la pantalla de la consola"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def update_console(self):
        """Actualiza la consola con información en tiempo real"""
        if Config.ENVIRONMENT == "local":
            self.clear_screen()
            print("=" * 80)
            print("🛡️  SERVIDOR UDP SENSOR DE TRÁFICO CON IA")
            print("=" * 80)
            print(f"📡 Puerto: {self.port}")
            print(f"🎯 Estado: {'DEMO' if self.demo_mode else 'LIVE'}")
            print("-" * 80)
            print(f"📦 Paquetes procesados: {self.packet_count}")
            print(f"🚨 Detecciones de malware: {self.malware_detections}")
            print(f"🔍 Resultado del último batch procesado: {self.last_result:.2f}")
            print("-" * 80)
            print(f"📋 Último paquete: {self.current_packet_info}")
            print("-" * 80)
            print("Presiona Ctrl+C para detener")
            print("=" * 80)
    
    def save_malware_detection(self, source_ip, src_port, dst_port):
        """Guarda detección de malware en DynamoDB"""
        malware_id = f"malware_{source_ip}"
            
        existing = self.dynamo_table.get({"id": malware_id})
        if existing:
            existing["packet_count"] += 1
            existing["last_seen"] = int(time.time())
            port = {
                "src_port": src_port,
                "dst_port": dst_port
            }   

            if "ports" not in existing:
                existing["ports"] = []

            existing_port = any(
                comm.get("src_port") == port["src_port"] and comm.get("dst_port") == port["dst_port"]
                for comm in existing["ports"]
            )
            if not existing_port:
                existing["ports"].append(port)

            self.dynamo_table.save(existing)
        else:
            self.dynamo_table.save({
                "id": malware_id,
                "ports": [
                    {
                        "src_port": src_port,
                        "dst_port": dst_port
                    }
                ],
                "source_ip": source_ip,
                "packet_count": 1,
                "first_seen": int(time.time())
            })
    
    def get_malware_detections(self):
        """Obtiene todas las detecciones de malware de DynamoDB"""
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
        """Extrae paquetes de un archivo PCAP para modo demo"""
        from scapy.all import rdpcap
        packets = rdpcap(file)
        return packets
    
    def demo_thread(self):
        """Thread para manejar el modo demo"""
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
                    if not self.demo_packages:
                        break
                    packet = self.demo_packages.pop(0)
                    self.process_packet(packet)
                
                self.demo_mode = False
                self.current_packet_info = "✅ Demo completado - Volviendo a modo LIVE"
                self.update_console()
            time.sleep(1)
    
    def parse_mirrored_packet(self, data):
        """Parsea un paquete del VPC Traffic Mirroring"""
        try:
            # VPC Traffic Mirroring encapsula el paquete original
            # Los primeros bytes contienen metadatos del mirroring
            if len(data) < 16:
                return None
            
            # Saltar los metadatos del mirroring (primeros 16 bytes)
            # y extraer el paquete IP original
            original_packet = data[16:]
            
            try:
                packet = IP(original_packet)
                if packet.haslayer(IP):
                    return packet
                else:
                    return None
            except Exception as e:
                self.logger.warning(f"Error creando paquete IP: {e}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error parseando paquete mirroring: {e}")
            return None
    
    def process_packet(self, packet):
        """Procesa un paquete con el modelo de IA"""
        if not self.running:
            return

        if not packet.haslayer(TCP):
            return
        
        self.packet_count += 1

        tcp_layer = packet[TCP]
        src_port = tcp_layer.sport
        dst_port = tcp_layer.dport
        
        result = self.model_service.process_packet(packet)
        self.last_result = result['malware_probability'] if result is not None else self.last_result
        
        if packet.haslayer(IP):
            source_ip = packet[IP].src
        else:
            source_ip = "N/A"
        
        self.current_packet_info = f"{source_ip} #{self.packet_count} - {src_port} -> {dst_port}"
        
        current_time = time.time()
        if current_time - self.last_update > 0.5:
            self.update_console()
            self.last_update = current_time
        
        if result:
            if result['is_malware']:
                self.malware_detections += 1
                self.current_packet_info += f" 🚨 MALWARE DETECTADO!"
                self.update_console() 
                
                self.save_malware_detection(source_ip, src_port, dst_port)
    
    def handle_udp_packet(self, data, addr):
        """Maneja un paquete UDP recibido"""
        if self.demo_mode:
            return
        
        packet = self.parse_mirrored_packet(data)
        if packet:
            self.process_packet(packet)
    
    def start_server(self):
        """Inicia el servidor UDP"""
        self.model_service.load_model()
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind(('0.0.0.0', self.port))
            self.logger.info(f"🎯 Servidor UDP iniciado en puerto {self.port}")
            
            self.update_console()
            
            threading.Thread(target=self.demo_thread, daemon=True).start()
            
            while self.running:
                try:
                    self.socket.setblocking(True)
                    data, addr = self.socket.recvfrom(65536)  # Tamaño máximo de paquete
                    
                    threading.Thread(
                        target=self.handle_udp_packet, 
                        args=(data, addr), 
                        daemon=True
                    ).start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error recibiendo paquete UDP: {e}")
                        
        except Exception as e:
            self.logger.error(f"❌ Error iniciando servidor UDP: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Detiene el servidor"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info(f"🛑 Servidor UDP detenido. Total de paquetes procesados: {self.packet_count}")

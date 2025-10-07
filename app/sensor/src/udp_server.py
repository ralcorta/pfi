import logging
import os
import socket
import time
from scapy.all import IP, TCP

from app.sensor.src.model_service import ModelService
from app.sensor.src.utils.config import Config
from app.sensor.src.utils.dynamo_client import DynamoClient

class UdpServer:
    """Servidor UDP para recibir tráfico del VPC Mirroring en puerto 4789"""
    
    def __init__(self, port=4789, model_path=None, default_pcap=None):
        self.port = port
        self.running = False
        self.packet_count = 0
        self.demo_packages = []
        self.preloaded_pcap = None  # PCAP precargado
        self.preloaded_pcap_file = None  # Archivo del PCAP precargado
        self.last_result = 0
        self.model_service = ModelService(model_path)
        self.dynamo_table = DynamoClient("demo-pcap-control")
        self.demo_mode = False
        self.current_packet_info = "Esperando paquetes..."
        self.malware_detections = 0
        self.last_update = time.time()
        self.socket = None
        self.default_pcap = default_pcap or "/app/models/data/small/Malware/Zeus.pcap"
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def clear_screen(self):
        """Limpia la pantalla de la consola"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def update_console(self):
        """Actualiza la consola con información en tiempo real"""

        # if Config.ENVIRONMENT == "local":
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
    
    def preload_pcap(self, file_path=None):
        """Precarga un archivo PCAP al inicio para evitar demoras en demo"""
        if file_path is None:
            file_path = self.default_pcap
            
        if not os.path.exists(file_path):
            self.logger.warning(f"⚠️ Archivo PCAP no encontrado: {file_path}")
            return False
            
        try:
            self.logger.info(f"🔄 Precargando PCAP por defecto: {file_path}")
            self.current_packet_info = "🔄 Precargando PCAP..."
            self.update_console()
            
            self.preloaded_pcap = self.extract_packages_from_pcap(file_path)
            self.preloaded_pcap_file = file_path
            
            self.logger.info(f"✅ PCAP precargado exitosamente: {len(self.preloaded_pcap)} paquetes")
            self.current_packet_info = f"✅ PCAP precargado: {len(self.preloaded_pcap)} paquetes"
            self.update_console()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error precargando PCAP: {e}")
            self.current_packet_info = f"❌ Error precargando PCAP: {str(e)}"
            self.update_console()
            return False

    def reload_pcap(self, file_path=None):
        """Recarga un nuevo PCAP (útil para cambiar el archivo por defecto)"""
        if file_path is None:
            file_path = self.default_pcap
            
        self.logger.info(f"🔄 Recargando PCAP: {file_path}")
        return self.preload_pcap(file_path)

    def extract_packages_from_pcap(self, file):
        """Extrae paquetes de un archivo PCAP para modo demo con optimizaciones"""
        from scapy.all import rdpcap
        import os
        
        # Verificar tamaño del archivo
        file_size = os.path.getsize(file)
        self.logger.info(f"📁 Cargando archivo PCAP: {file} ({file_size / (1024*1024):.1f} MB)")
        
        # Mostrar progreso para archivos grandes
        if file_size > 5 * 1024 * 1024:  # > 5MB
            self.logger.info("⏳ Cargando archivo PCAP grande, esto puede tomar unos segundos...")
            self.current_packet_info = "⏳ Cargando archivo PCAP..."
            self.update_console()
        
        try:
            self.logger.info(f"Leyendo pcap {file} de {file_size} bytes de disco")
            packets = rdpcap(file)
            self.logger.info(f"✅ PCAP cargado: {len(packets)} paquetes extraídos")
            return packets
        except Exception as e:
            self.logger.error(f"❌ Error cargando PCAP: {e}")
            raise
    
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
        """Inicia el servidor en modo demo (solo HTTP, sin UDP)"""
        self.model_service.load_model()
        self.running = True
        
        self.logger.info("🎯 Iniciando servidor en modo demo (solo HTTP, sin UDP)")
        self.update_console()
        
        # Precargar PCAP por defecto al inicio
        self.logger.info("🔄 Precargando PCAP por defecto para demos rápidas...")
        self.preload_pcap()
        
        # Mantener el proceso vivo y verificar demo directamente
        try:
            while self.running:
                # Verificar si hay demo activo (lógica del demo_thread integrada)
                try:
                    data = self.dynamo_table.get({"id": "demo_control"})
                except Exception as e:
                    self.logger.error(f"❌ Error obteniendo demo_control: {e}")
                    time.sleep(1)
                    continue
                
                if data and data.get("execute_demo") == "true":
                    self.demo_mode = True
                    self.current_packet_info = "🎭 Iniciando modo demo..."
                    self.update_console()
                    
                    pcap_file = data.get("pcap_file", "")

                    try:
                        # Usar PCAP precargado si es el mismo archivo o si no se especifica archivo
                        if (not pcap_file or pcap_file == self.preloaded_pcap_file) and self.preloaded_pcap:
                            self.logger.info(f"🚀 Usando PCAP precargado: {self.preloaded_pcap_file}")
                            self.demo_packages = self.preloaded_pcap # .copy()  # Copiar para no modificar el original
                        else:
                            # Cargar PCAP específico si es diferente al precargado
                            self.logger.info(f"📁 Cargando PCAP específico: {pcap_file}")
                            self.demo_packages = self.extract_packages_from_pcap(pcap_file)
                    except Exception as e:
                        self.logger.error(f"❌ Error procesando archivo PCAP {pcap_file}: {e}")
                        self.demo_mode = False
                        self.current_packet_info = f"❌ Error en demo: {str(e)}"
                        self.update_console()
                        # Desactivar el demo en caso de error
                        self.dynamo_table.save({"id": "demo_control", "execute_demo": "false"})
                        time.sleep(1)
                        continue
                    
                    self.current_packet_info = f"🎭 Procesando {len(self.demo_packages)} paquetes del demo..."
                    self.update_console()
                    
                    for packet in self.demo_packages:
                        self.process_packet(packet)
                    
                    self.demo_mode = False
                    self.current_packet_info = "✅ Demo completado - Volviendo a modo LIVE"
                    self.update_console()
                    
                    # Desactivar el demo en DynamoDB cuando termine
                    self.dynamo_table.save({"id": "demo_control", "execute_demo": "false"})
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Deteniendo servidor por interrupción del usuario")
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Detiene el servidor"""
        self.running = False
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        self.logger.info(f"🛑 Servidor detenido. Total de paquetes procesados: {self.packet_count}")

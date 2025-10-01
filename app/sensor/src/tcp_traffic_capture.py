import logging
from scapy.all import sniff, TCP

from app.sensor.src.ai_model_processor import AIModelProcessor

class TCPTrafficCapture:
    """Capturador simple de tráfico TCP con procesamiento de IA"""
    
    def __init__(self, interface="eth0", filter_str="tcp", model_path=None):
        self.interface = interface
        self.filter_str = filter_str
        self.running = False
        self.packet_count = 0
        
        # Inicializar procesador de IA
        self.ai_processor = AIModelProcessor(model_path)
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def packet_handler(self, packet):
        """Manejador de paquetes TCP capturados"""
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
        
        # Mostrar cada 10 paquetes para no saturar
        if self.packet_count % 10 == 0:
            self.logger.info(f"📦 TCP #{self.packet_count} - {src_port} -> {dst_port}")
        
        # Si hay resultado del modelo, mostrarlo
        if result:
            if result['is_malware']:
                self.logger.warning(f"🚨 MALWARE DETECTADO - Confianza: {result['confidence']:.2f}")
    
    def start_capture(self):
        """Inicia la captura de tráfico TCP"""
        self.logger.info(f"🛡️ Iniciando captura de tráfico TCP con IA...")
        self.logger.info(f"📡 Interfaz: {self.interface}")
        self.logger.info(f"🔍 Filtro: {self.filter_str}")
        
        # Cargar modelo de IA
        self.ai_processor.load_model()
        
        self.running = True
        
        try:
            # Iniciar captura solo TCP
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
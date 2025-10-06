#!/usr/bin/env python3
"""
Servidor híbrido que ejecuta tanto UDP como HTTP
"""
import signal
import sys
import threading
import time
import argparse
import logging
import uvicorn

from app.sensor.src.udp_server import UdpServer
from app.sensor.src.http_server import HTTPServer

class HybridServer:
    """Servidor híbrido UDP + HTTP"""
    
    def __init__(self, udp_port=4789, http_port=8080, model_path=None):
        self.udp_port = udp_port
        self.http_port = http_port
        self.model_path = model_path
        self.running = False
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Inicializar servidores
        self.udp_server = UdpServer(udp_port, model_path)
        self.http_server = HTTPServer(http_port)
        
        # Threads
        self.udp_thread = None
        self.http_thread = None
        
        # Configurar manejo de señales para ECS
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales del sistema para shutdown graceful"""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"🛑 Recibida señal {signal_name} ({signum}) - Iniciando shutdown graceful...")
        self.running = False
    
    def start_servers(self):
        """Inicia ambos servidores en threads separados"""
        self.running = True
        
        try:
            # Iniciar servidor UDP en thread separado
            self.logger.info("🚀 Iniciando servidor UDP...")
            self.udp_thread = threading.Thread(target=self._run_udp_server, daemon=True)
            self.udp_thread.start()
            
            # Iniciar servidor HTTP en thread separado
            self.logger.info("🌐 Iniciando servidor HTTP...")
            self.http_thread = threading.Thread(target=self._run_http_server, daemon=True)
            self.http_thread.start()
            
            self.logger.info(f"✅ Servidores iniciados:")
            self.logger.info(f"   📡 UDP: puerto {self.udp_port}")
            self.logger.info(f"   🌐 HTTP: puerto {self.http_port}")
            self.logger.info("   📋 Endpoints HTTP disponibles:")
            self.logger.info("      - GET /health - Health check")
            self.logger.info("      - GET /detections - Lista de detecciones")
            self.logger.info("      - GET /detections/{id} - Detección específica")
            self.logger.info("      - GET /stats - Estadísticas")
            self.logger.info("      - GET /demo/status - Estado del demo")
            
            # Mantener el proceso vivo
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Interrumpido por usuario")
        except Exception as e:
            self.logger.error(f"❌ Error en servidor híbrido: {e}")
        finally:
            self.stop_servers()
    
    def _run_udp_server(self):
        """Ejecuta el servidor UDP"""
        try:
            self.udp_server.start_server()
        except Exception as e:
            self.logger.error(f"❌ Error en servidor UDP: {e}")
    
    def _run_http_server(self):
        """Ejecuta el servidor HTTP"""
        try:
            uvicorn.run(
                self.http_server.app,
                host="0.0.0.0",
                port=self.http_port,
                log_level="info"
            )
        except Exception as e:
            self.logger.error(f"❌ Error en servidor HTTP: {e}")
    
    def stop_servers(self):
        """Detiene ambos servidores"""
        self.logger.info("🛑 Deteniendo servidores...")
        self.running = False
        
        # Detener servidor UDP
        if hasattr(self.udp_server, 'stop_server'):
            self.udp_server.stop_server()
        
        # Los threads HTTP y UDP se detendrán automáticamente
        self.logger.info("✅ Servidores detenidos")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Servidor híbrido UDP + HTTP para Sensor de Tráfico')
    parser.add_argument('--udp-port', type=int, default=4789, help='Puerto UDP')
    parser.add_argument('--http-port', type=int, default=8080, help='Puerto HTTP')
    parser.add_argument('--model', help='Ruta al modelo .keras')
    
    args = parser.parse_args()
    
    # Crear servidor híbrido
    server = HybridServer(args.udp_port, args.http_port, args.model)
    
    # El manejo de señales ya está configurado en el constructor de HybridServer
    
    try:
        # Iniciar servidores
        server.start_servers()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    except Exception as e:
        print(f"❌ Error en servidor híbrido: {e}")
    finally:
        server.stop_servers()

if __name__ == "__main__":
    main()

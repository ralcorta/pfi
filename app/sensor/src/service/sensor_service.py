"""
Servicio del sensor de malware.
Maneja el procesamiento de tráfico UDP y análisis de paquetes.
"""

import asyncio
import socket
from scapy.layers.vxlan import VXLAN
from app.sensor.src.service.malware_detector import MalwareDetector
from app.sensor.src.utils.environment import env


class SensorService:
    """Servicio principal del sensor de malware."""
    
    def __init__(self):
        self.running = False
        self.udp_task = None
        self.malware_detector = None
    
    async def start(self):
        """Inicia el servicio del sensor."""
        print("🚀 Iniciando servicio del sensor...")
        
        try:
            # Inicializar detector de malware
            model_path = "/app/app/sensor/model/model.keras"
            self.malware_detector = MalwareDetector(model_path)
            print("✅ Detector de malware inicializado")
            
            self.udp_task = asyncio.create_task(self._udp_listener())
            self.running = True
            print("✅ Servicio del sensor iniciado correctamente")
        except Exception as e:
            print(f"❌ Error iniciando servicio del sensor: {e}")
    
    async def stop(self):
        """Detiene el servicio del sensor."""
        print("🛑 Deteniendo servicio del sensor...")
        self.running = False
        
        if self.udp_task and not self.udp_task.done():
            self.udp_task.cancel()
            try:
                await asyncio.wait_for(self.udp_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        print("🛑 Servicio del sensor detenido")
    
    async def _udp_listener(self):
        """Escucha tráfico UDP en puerto 4789 en segundo plano."""
        loop = asyncio.get_running_loop()
        sock = None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", env.vxlan_port))
            sock.setblocking(False)
            
            print(f"🔍 Escuchando tráfico UDP en puerto {env.vxlan_port}")
            
            while self.running:
                try:
                    data, _ = await loop.sock_recvfrom(sock, 65535)
                    
                    try:
                        vx = VXLAN(data)
                        inner = bytes(vx.payload)
                        vni = int(vx.vni)
                        
                        asyncio.create_task(self._process_packet(inner, vni))
                        
                    except Exception as e:
                        print(f"❌ Error procesando paquete: {e}")
                        
                except (asyncio.CancelledError, OSError) as e:
                    print(f"🛑 Listener UDP cancelado: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error crítico en listener UDP: {e}")
            print("⚠️  Continuando con servidor HTTP...")
            
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
            print("🛑 Listener UDP detenido")
    
    async def _process_packet(self, inner: bytes, vni: int):
        """Procesa un paquete individual."""
        try:
            # Detectar malware si el detector está disponible
            if self.malware_detector:
                detection_result = self.malware_detector.detect_malware(inner)
                
                # Mostrar resultado
                if detection_result is None:
                    pass
                elif detection_result.error:
                    print(f"⚠️ Error en detección: {detection_result.error}")
                else:
                    malware_prob = detection_result.malware_probability
                    is_malware = detection_result.is_malware
                    confidence = detection_result.confidence
                    packet_info = detection_result.packet_info
                    
                    # Mostrar información del paquete
                    src_ip = packet_info.src_ip or 'N/A'
                    dst_ip = packet_info.dst_ip or 'N/A'
                    src_port = packet_info.src_port or 'N/A'
                    dst_port = packet_info.dst_port or 'N/A'
                    protocol = packet_info.protocol or 'N/A'
                    
                    # Convertir protocolo a nombre
                    protocol_name = {6: 'TCP', 17: 'UDP'}.get(protocol, f'Protocol-{protocol}')
                    
                    if is_malware:
                        print(f"🚨 MALWARE DETECTADO!")
                        print(f"   Probabilidad: {malware_prob:.2%}")
                        print(f"   Confianza: {confidence:.2%}")
                        print(f"   VNI: {vni}")
                        print(f"   Conexión: {src_ip}:{src_port} → {dst_ip}:{dst_port} ({protocol_name})")
                    else:
                        print(f"✅ Tráfico benigno (probabilidad malware: {malware_prob:.2%})")
                        print(f"   Conexión: {src_ip}:{src_port} → {dst_ip}:{dst_port} ({protocol_name})")
            
        except Exception as e:
            print(f"❌ Error procesando paquete: {e}")


# Instancia global del servicio
sensor_service = SensorService()

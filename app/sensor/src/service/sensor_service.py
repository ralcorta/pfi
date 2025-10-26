"""
Servicio del sensor de malware.
Maneja el procesamiento de tráfico UDP y análisis de paquetes.
"""

import asyncio
import socket
from scapy.layers.vxlan import VXLAN
from app.sensor.src.utils.environment import env


class SensorService:
    """Servicio principal del sensor de malware."""
    
    def __init__(self):
        self.running = False
        self.udp_task = None
    
    async def start(self):
        """Inicia el servicio del sensor."""
        print("🚀 Iniciando servicio del sensor...")
        
        try:
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
            print(f"📦 Procesando paquete VNI: {vni}, tamaño: {len(inner)}")
            
        except Exception as e:
            print(f"❌ Error procesando paquete: {e}")


# Instancia global del servicio
sensor_service = SensorService()

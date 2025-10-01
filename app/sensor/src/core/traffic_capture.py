# app/sensor/src/core/traffic_capture.py
"""
Captura de tráfico de red en tiempo real usando Scapy
"""

import asyncio
import time
from typing import AsyncGenerator, List
from scapy.all import sniff, AsyncSniffer
from scapy.packet import Packet
import logging

class TrafficCapture:
    """Captura tráfico de red en tiempo real"""
    
    def __init__(self, interface: str, filter: str = None, buffer_size: int = 100, logger=None):
        self.interface = interface
        self.filter = filter or "udp port 4789"  # Puerto por defecto para VPC Mirroring
        self.buffer_size = buffer_size
        self.logger = logger or logging.getLogger(__name__)
        
        self.sniffer = None
        self.packet_buffer = []
        self.running = False
        self.last_flush = time.time()
        self.flush_interval = 1.0  # Flush cada 1 segundo
    
    async def start(self):
        """Inicia la captura de tráfico"""
        self.logger.info(f"📡 Iniciando captura en interfaz: {self.interface}")
        self.logger.info(f"🔍 Filtro: {self.filter}")
        
        self.running = True
        
        # Crear sniffer asíncrono
        self.sniffer = AsyncSniffer(
            iface=self.interface,
            filter=self.filter,
            prn=self._packet_handler,
            store=False  # No almacenar paquetes, solo procesar
        )
        
        # Iniciar captura en hilo separado
        self.sniffer.start()
        self.logger.info("✅ Captura iniciada")
    
    def _packet_handler(self, packet: Packet):
        """Manejador de paquetes capturados"""
        if not self.running:
            return
        
        try:
            # Agregar paquete al buffer
            self.packet_buffer.append(packet)
            
            # Flush si el buffer está lleno o ha pasado el tiempo
            current_time = time.time()
            if (len(self.packet_buffer) >= self.buffer_size or 
                current_time - self.last_flush >= self.flush_interval):
                self._flush_buffer()
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando paquete: {e}")
    
    def _flush_buffer(self):
        """Envía el buffer de paquetes para procesamiento"""
        if self.packet_buffer:
            # Crear evento para notificar que hay paquetes listos
            asyncio.create_task(self._notify_packets_ready(self.packet_buffer.copy()))
            self.packet_buffer.clear()
            self.last_flush = time.time()
    
    async def _notify_packets_ready(self, packets: List[Packet]):
        """Notifica que hay paquetes listos para procesar"""
        # Este método será sobrescrito por el generador
        pass
    
    async def get_packets(self) -> AsyncGenerator[List[Packet], None]:
        """Generador asíncrono de lotes de paquetes"""
        packet_queue = asyncio.Queue()
        
        # Sobrescribir el método de notificación
        async def notify_packets(packets):
            await packet_queue.put(packets)
        
        self._notify_packets_ready = notify_packets
        
        # Generar lotes de paquetes
        while self.running:
            try:
                # Esperar paquetes con timeout
                packets = await asyncio.wait_for(packet_queue.get(), timeout=5.0)
                yield packets
            except asyncio.TimeoutError:
                # Timeout normal, continuar
                continue
            except Exception as e:
                self.logger.error(f"❌ Error en generador de paquetes: {e}")
                break
    
    async def stop(self):
        """Detiene la captura de tráfico"""
        self.logger.info("🛑 Deteniendo captura de tráfico...")
        self.running = False
        
        if self.sniffer:
            self.sniffer.stop()
        
        # Procesar paquetes restantes
        if self.packet_buffer:
            self._flush_buffer()
        
        self.logger.info("✅ Captura detenida")
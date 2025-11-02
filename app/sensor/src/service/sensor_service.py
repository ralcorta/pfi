"""
Servicio del sensor de malware.
Maneja el procesamiento de tráfico UDP y análisis de paquetes.
"""

import asyncio
import socket
from collections import deque
from scapy.layers.vxlan import VXLAN
from scapy.all import Ether, IP, TCP, UDP, Raw
from app.sensor.src.service.malware_detector import MalwareDetector
from app.sensor.src.utils.environment import env
from app.sensor.src.db.detection_client import detection_db
from app.sensor.src.db.user_client import user_db
from app.sensor.src.utils.email_service import email_service

from decimal import Decimal

class SensorService:
    """Servicio principal del sensor de malware."""
    
    def __init__(self):
        self.running = False
        self.udp_task = None
        self.malware_detector = None
        self.processing_semaphore = None  # Se inicializa en start()
        # Buffer circular de paquetes (últimos 20)
        self.packet_buffer = deque(maxlen=20)
        self.buffer_lock = None  # Se inicializa en start()
        self.processing_pending = False  # Flag para evitar múltiples tareas de procesamiento
    
    async def start(self):
        """Inicia el servicio del sensor."""
        print("🚀 Iniciando servicio del sensor...")
        
        try:
            # Inicializar semáforo para limitar procesamiento concurrente
            self.processing_semaphore = asyncio.Semaphore(1)  # Solo 1 batch procesándose a la vez
            # Inicializar lock para acceso thread-safe al buffer
            self.buffer_lock = asyncio.Lock()
            
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
            print(f"📍 Socket bindeado en: 0.0.0.0:{env.vxlan_port}")
            
            # Task para heartbeat cada 2 minutos (menos frecuente)
            async def heartbeat():
                await asyncio.sleep(10)  # Esperar 10s antes del primer heartbeat
                while self.running:
                    await asyncio.sleep(120)  # Cada 2 minutos
                    if self.running:
                        print(f"Listener UDP activo en puerto {env.vxlan_port}")
            
            asyncio.create_task(heartbeat())
            
            while self.running:
                try:
                    data, addr = await loop.sock_recvfrom(sock, 65535)
                    
                    # Log cuando se recibe tráfico UDP
                    print(f"📥 Tráfico UDP recibido: {len(data)} bytes desde {addr[0]}:{addr[1]} en puerto {env.vxlan_port}")
                    
                    # Intentar parsear como VXLAN (sin logs detallados)
                    try:
                        vx = VXLAN(data)
                        inner = bytes(vx.payload)
                        vni = int(vx.vni)
                        
                        # Agregar paquete directamente al buffer (operación rápida, sin crear tarea)
                        await self._add_packet_to_buffer(inner, vni)
                        
                    except Exception as e:
                        # Solo loggear errores de parsing si son frecuentes (cada 100 paquetes)
                        self._packet_parse_errors = getattr(self, '_packet_parse_errors', 0) + 1
                        if self._packet_parse_errors % 100 == 0:
                            print(f"⚠️  Error parseando VXLAN (total: {self._packet_parse_errors}): {type(e).__name__}")
                        
                except BlockingIOError:
                    # No hay datos disponibles, esperar un poco
                    await asyncio.sleep(0.1)
                    continue
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
    
    async def _add_packet_to_buffer(self, inner: bytes, vni: int):
        """Agrega un paquete al buffer circular (últimos 20). Operación rápida."""
        async with self.buffer_lock:
            # Agregar paquete al buffer (automáticamente descarta el más antiguo si hay más de 20)
            self.packet_buffer.append((inner, vni))
            
            # Si el buffer tiene 20 paquetes y no hay un procesamiento pendiente, procesar el batch
            if len(self.packet_buffer) >= 20 and not self.processing_pending:
                # Copiar los paquetes del buffer antes de procesarlos
                batch = list(self.packet_buffer)
                # Limpiar el buffer para empezar a acumular el siguiente batch
                self.packet_buffer.clear()
                # Marcar que hay procesamiento pendiente
                self.processing_pending = True
                # Procesar el batch en background (sin bloquear el listener)
                asyncio.create_task(self._process_batch_and_reset_flag(batch))
    
    async def _process_batch_and_reset_flag(self, batch: list):
        """Procesa un batch y resetea el flag de procesamiento pendiente."""
        try:
            await self._process_batch_safe(batch)
        finally:
            # Resetear flag después de procesar (incluso si hay error)
            async with self.buffer_lock:
                self.processing_pending = False
            
            # Verificar si el buffer se llenó mientras procesábamos
            async with self.buffer_lock:
                if len(self.packet_buffer) >= 20 and not self.processing_pending:
                    # Hay más paquetes listos para procesar
                    batch = list(self.packet_buffer)
                    self.packet_buffer.clear()
                    self.processing_pending = True
                    asyncio.create_task(self._process_batch_and_reset_flag(batch))
    
    async def _process_batch_safe(self, batch: list):
        """Procesa un batch de 20 paquetes con límite de concurrencia."""
        async with self.processing_semaphore:
            await self._process_batch(batch)
    
    async def _process_batch(self, batch: list):
        """Procesa un batch de 20 paquetes."""
        if not self.malware_detector:
            return
        
        try:
            print(f"🔍 Procesando batch de {len(batch)} paquetes...")
            
            # Procesar cada paquete del batch en el detector
            # El detector tiene su propio buffer interno que se va llenando
            loop = asyncio.get_running_loop()
            
            # Procesar todos los paquetes del batch
            for inner, vni in batch:
                # Ejecutar detección en thread pool para no bloquear
                detection_result = await loop.run_in_executor(
                    None,  # Usar default executor (thread pool)
                    self.malware_detector.detect_malware,
                    inner
                )
                
                # Solo procesar resultados que no sean None (buffer del detector lleno)
                if detection_result is None:
                    continue  # Buffer del detector aún no está lleno
                elif detection_result.error:
                    # Solo loggear errores si ocurren frecuentemente
                    self._detection_errors = getattr(self, '_detection_errors', 0) + 1
                    if self._detection_errors % 10 == 0:
                        print(f"⚠️ Error en detección ({self._detection_errors} errores): {detection_result.error}")
                    continue
                
                # Buffer lleno y resultado válido
                malware_prob = detection_result.malware_probability
                is_malware = detection_result.is_malware
                packet_info = detection_result.packet_info
                
                # Mostrar información del paquete (con validación de None)
                if packet_info is None:
                    print(f"⚠️ PacketInfo es None para detección de malware (prob: {malware_prob:.2%})")
                    continue
                
                # Extraer información con valores por defecto apropiados
                src_ip = packet_info.src_ip if packet_info.src_ip else 'N/A'
                dst_ip = packet_info.dst_ip if packet_info.dst_ip else 'N/A'
                src_port = packet_info.src_port if packet_info.src_port is not None and packet_info.src_port != 0 else 'N/A'
                dst_port = packet_info.dst_port if packet_info.dst_port is not None and packet_info.dst_port != 0 else 'N/A'
                protocol = packet_info.protocol if packet_info.protocol is not None and packet_info.protocol != 0 else 'N/A'
                
                # Convertir protocolo a nombre
                protocol_name = {6: 'TCP', 17: 'UDP'}.get(protocol, f'Protocol-{protocol}' if protocol != 'N/A' else 'N/A')
                
                # Si no tenemos información del paquete, intentar parsearlo manualmente para debug
                if src_ip == 'N/A' and dst_ip == 'N/A':
                    try:
                        parsed = Ether(inner)
                        if IP in parsed:
                            ip_layer = parsed[IP]
                            src_ip = ip_layer.src if ip_layer.src else 'N/A'
                            dst_ip = ip_layer.dst if ip_layer.dst else 'N/A'
                            if TCP in ip_layer:
                                src_port = ip_layer[TCP].sport
                                dst_port = ip_layer[TCP].dport
                                protocol_name = 'TCP'
                            elif UDP in ip_layer:
                                src_port = ip_layer[UDP].sport
                                dst_port = ip_layer[UDP].dport
                                protocol_name = 'UDP'
                    except Exception as e:
                        # Si falla el parsing manual, mantener los valores por defecto
                        pass
                
                # Solo loggear si es malware o probabilidad muy alta (>50%)
                if is_malware or malware_prob > 0.5:
                    print(f"🚨 MALWARE DETECTADO! Probabilidad: {malware_prob:.2%} | VNI: {vni} | {src_ip}:{src_port} → {dst_ip}:{dst_port} ({protocol_name})")
                    
                    # Guardar detección en DynamoDB
                    detection_data = {
                        'malware_probability': Decimal(str(malware_prob)),
                        'is_malware': is_malware,
                        'vni': vni,
                        'src_ip': src_ip,
                        'dst_ip': dst_ip,
                        'src_port': src_port,
                        'dst_port': dst_port,
                        'protocol': protocol_name,
                        'src_mac': packet_info.src_mac,
                        'dst_mac': packet_info.dst_mac
                    }
                    
                    try:
                        # Verificar si ya existe una detección previa para esta IP (ANTES de guardar)
                        is_new_infected_ip = not detection_db.has_detection_for_ip(vni, src_ip)
                        
                        # Guardar detección en DynamoDB (siempre se guarda para historial)
                        detection_db.put_detection(detection_data)
                        print(f"💾 Detección guardada en DynamoDB")
                        
                        # Solo enviar email si es una IP infectada nueva (primera vez que se detecta)
                        if is_new_infected_ip:
                            print(f"🆕 Nueva IP infectada detectada: {src_ip} (VNI: {vni})")
                            try:
                                user = user_db.get_user_by_vni(vni)
                                if user and user.email:
                                    detection_details = {
                                        'malware_probability': malware_prob,
                                        'src_ip': src_ip,
                                        'dst_ip': dst_ip,
                                        'src_port': src_port,
                                        'dst_port': dst_port,
                                        'protocol': protocol_name,
                                        'timestamp': detection_data.get('timestamp')
                                    }
                                    email_service.send_malware_alert_email(
                                        to_email=user.email,
                                        vni=vni,
                                        detection_details=detection_details
                                    )
                                else:
                                    print(f"⚠️  No se encontró usuario para VNI {vni}, no se enviará email de alerta")
                            except Exception as e:
                                print(f"⚠️  Error enviando email de alerta (no crítico): {e}")
                        else:
                            print(f"ℹ️  IP {src_ip} ya tiene detecciones previas, no se enviará email duplicado")
                        
                    except Exception as e:
                        print(f"❌ Error guardando detección: {e}")
            
            print(f"✅ Batch procesado ({len(batch)} paquetes)")
            
        except Exception as e:
            print(f"❌ Error procesando batch: {e}")

# Instancia global del servicio
sensor_service = SensorService()

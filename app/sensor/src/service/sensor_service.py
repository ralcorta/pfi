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
    
    def __init__(self):
        self.running = False
        self.udp_task = None
        self.malware_detector = None
        self.processing_semaphore = None
        self.packet_buffer = deque(maxlen=20)
        self.buffer_lock = None
        self.processing_pending = False
    
    async def start(self):
        print("Starting sensor service...")
        
        try:
            self.processing_semaphore = asyncio.Semaphore(1)
            self.buffer_lock = asyncio.Lock()
            
            model_path = "/app/app/sensor/model/model.keras"
            self.malware_detector = MalwareDetector(model_path)
            print("Malware detector initialized")
            
            self.udp_task = asyncio.create_task(self._udp_listener())
            self.running = True
            print("Sensor service started successfully")
        except Exception as e:
            print(f"Error starting sensor service: {e}")
    
    async def stop(self):
        print("Stopping sensor service...")
        self.running = False
        
        if self.udp_task and not self.udp_task.done():
            self.udp_task.cancel()
            try:
                await asyncio.wait_for(self.udp_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        
        print("Sensor service stopped")
    
    async def _udp_listener(self):
        loop = asyncio.get_running_loop()
        sock = None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", env.vxlan_port))
            sock.setblocking(False)
            
            print(f"Listening for UDP traffic on port {env.vxlan_port}")
            print(f"Socket bound to: 0.0.0.0:{env.vxlan_port}")
            
            async def heartbeat():
                await asyncio.sleep(10)
                while self.running:
                    await asyncio.sleep(120)
                    if self.running:
                        print(f"UDP listener active on port {env.vxlan_port}")
            
            asyncio.create_task(heartbeat())
            
            while self.running:
                try:
                    data, addr = await loop.sock_recvfrom(sock, 65535)
                    
                    print(f"UDP traffic received: {len(data)} bytes from {addr[0]}:{addr[1]} on port {env.vxlan_port}")
                    
                    try:
                        vx = VXLAN(data)
                        inner = bytes(vx.payload)
                        vni = int(vx.vni)                        
                        await self._add_packet_to_buffer(inner, vni)
                        
                except BlockingIOError:
                    await asyncio.sleep(0.1)
                    continue
                except (asyncio.CancelledError, OSError) as e:
                    print(f"UDP listener cancelled: {e}")
                    break
                    
        except Exception as e:
            print(f"Critical error in UDP listener: {e}")
            print("Continuing with HTTP server...")
            
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
            print("UDP listener stopped")
    
    async def _add_packet_to_buffer(self, inner: bytes, vni: int):
        async with self.buffer_lock:
            self.packet_buffer.append((inner, vni))
            
            if len(self.packet_buffer) >= 20 and not self.processing_pending:
                batch = list(self.packet_buffer)
                self.packet_buffer.clear()
                self.processing_pending = True
                asyncio.create_task(self._process_batch_and_reset_flag(batch))
    
    async def _process_batch_and_reset_flag(self, batch: list):
        try:
            await self._process_batch_safe(batch)
        finally:
            async with self.buffer_lock:
                self.processing_pending = False
            
            async with self.buffer_lock:
                if len(self.packet_buffer) >= 20 and not self.processing_pending:
                    batch = list(self.packet_buffer)
                    self.packet_buffer.clear()
                    self.processing_pending = True
                    asyncio.create_task(self._process_batch_and_reset_flag(batch))
    
    async def _process_batch_safe(self, batch: list):
        async with self.processing_semaphore:
            await self._process_batch(batch)
    
    async def _process_batch(self, batch: list):
        if not self.malware_detector:
            return
        
        try:
            print(f"Processing batch of {len(batch)} packets...")
            
            loop = asyncio.get_running_loop()
            
            for inner, vni in batch:
                detection_result = await loop.run_in_executor(
                    None,
                    self.malware_detector.detect_malware,
                    inner
                )
                
                if detection_result is None:
                    continue
                elif detection_result.error:
                    self._detection_errors = getattr(self, '_detection_errors', 0) + 1
                    if self._detection_errors % 10 == 0:
                        print(f"Error in detection ({self._detection_errors} errors): {detection_result.error}")
                    continue
                
                malware_prob = detection_result.malware_probability
                is_malware = detection_result.is_malware
                packet_info = detection_result.packet_info
                
                if packet_info is None:
                    print(f"PacketInfo is None for malware detection (prob: {malware_prob:.2%})")
                    continue
                
                src_ip = packet_info.src_ip if packet_info.src_ip else 'N/A'
                dst_ip = packet_info.dst_ip if packet_info.dst_ip else 'N/A'
                src_port = packet_info.src_port if packet_info.src_port is not None and packet_info.src_port != 0 else 'N/A'
                dst_port = packet_info.dst_port if packet_info.dst_port is not None and packet_info.dst_port != 0 else 'N/A'
                protocol = packet_info.protocol if packet_info.protocol is not None and packet_info.protocol != 0 else 'N/A'
                
                protocol_name = {6: 'TCP', 17: 'UDP'}.get(protocol, f'Protocol-{protocol}' if protocol != 'N/A' else 'N/A')
                
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
                        pass
                
                if is_malware or malware_prob > 0.5:
                    print(f"🚨 MALWARE DETECTED! Probability: {malware_prob:.2%} | VNI: {vni} | {src_ip}:{src_port} → {dst_ip}:{dst_port} ({protocol_name})")
                    
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
                        is_new_infected_ip = not detection_db.has_detection_for_ip(vni, src_ip)
                        
                        detection_db.put_detection(detection_data)
                        print(f"Detection saved in DynamoDB")
                        
                        if is_new_infected_ip:
                            print(f"New infected IP detected: {src_ip} (VNI: {vni})")
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
                                    print(f"No user found for VNI {vni}, no email alert will be sent")
                            except Exception as e:
                                print(f"Error sending email alert (not critical): {e}")
                        else:
                            print(f"IP {src_ip} already has previous detections, no email duplicate will be sent")
                        
                    except Exception as e:
                        print(f"Error saving detection: {e}")
            
            print(f"Batch processed ({len(batch)} packets)")
            
        except Exception as e:
            print(f"Error processing batch: {e}")

sensor_service = SensorService()

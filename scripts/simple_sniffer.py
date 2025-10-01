#!/usr/bin/env python3
"""
Sniffer simple sin curses para detección de ransomware
Versión más conservadora con umbrales ajustados
"""

import sys
import time
import threading
import queue
from pathlib import Path
import numpy as np
from scapy.all import sniff, TCP, UDP, Raw
from tensorflow.keras.models import load_model
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración
PAYLOAD_LEN = 1024
SEQUENCE_LENGTH = 20
PROJECT_ROOT = Path(__file__).parent

class ConservativeRansomwareDetector:
    def __init__(self, model_path=None):
        """Inicializar el detector conservador"""
        self.model_path = model_path or PROJECT_ROOT / "models" / "training" / "detection" / "convlstm_model.keras"
        self.model = None
        self.packet_buffer = []
        self.analysis_queue = queue.Queue()
        self.running = False
        self.stats = {
            'total_packets': 0,
            'analyzed_sequences': 0,
            'ransomware_detections': 0,
            'high_risk_detections': 0,
            'start_time': None
        }
        
        # Umbrales más conservadores
        self.SUSPICIOUS_THRESHOLD = 0.8 
        self.HIGH_RISK_THRESHOLD = 0.9  
        
        self._load_model()
    
    def _load_model(self):
        """Cargar el modelo entrenado"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Modelo no encontrado: {self.model_path}")
            
            self.model = load_model(str(self.model_path))
            print("✅ Modelo cargado exitosamente")
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            sys.exit(1)
    
    def packet_callback(self, packet):
        """Callback para procesar cada paquete capturado"""
        if not self.running:
            return
        
        self.stats['total_packets'] += 1
        
        # Solo procesar paquetes con payload significativo
        if (packet.haslayer(TCP) or packet.haslayer(UDP)) and packet.haslayer(Raw):
            try:
                payload = bytes(packet[Raw].load)
                
                # Filtrar paquetes muy pequeños (probablemente ACKs, etc.)
                if len(payload) < 50:  # Ignorar paquetes muy pequeños
                    return
                
                if len(payload) > PAYLOAD_LEN:
                    payload = payload[:PAYLOAD_LEN]
                else:
                    payload = payload + bytes([0] * (PAYLOAD_LEN - len(payload)))
                
                # Convertir a array de numpy
                payload_array = np.frombuffer(payload, dtype=np.uint8)
                self.packet_buffer.append(payload_array)
                
                # Cuando tengamos suficientes paquetes, analizar
                if len(self.packet_buffer) >= SEQUENCE_LENGTH:
                    sequence = self.packet_buffer[:SEQUENCE_LENGTH]
                    self.packet_buffer = self.packet_buffer[SEQUENCE_LENGTH:]
                    
                    # Enviar a la cola de análisis
                    self.analysis_queue.put(sequence)
                    
            except Exception:
                # Saltar paquetes problemáticos
                pass
    
    def analyze_sequence(self, sequence):
        """Analizar una secuencia de paquetes con umbrales conservadores"""
        try:
            # Crear secuencia para el modelo
            sequence_array = np.array(sequence, dtype=np.uint8).reshape(1, SEQUENCE_LENGTH, 32, 32, 1) / 255.0
            
            # Realizar predicción
            prediction = self.model.predict(sequence_array, verbose=0)
            probability = prediction[0][1]  # Probabilidad de ransomware
            
            self.stats['analyzed_sequences'] += 1
            
            # Clasificación más conservadora
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            if probability >= self.HIGH_RISK_THRESHOLD:
                # Solo alertar si la probabilidad es muy alta
                self.stats['high_risk_detections'] += 1
                print(f"🔴 [{timestamp}] ALTO RIESGO detectado! Probabilidad: {probability:.3f}")
                return True
            elif probability >= self.SUSPICIOUS_THRESHOLD:
                # Solo alertar si la probabilidad es moderadamente alta
                self.stats['ransomware_detections'] += 1
                print(f"🟡 [{timestamp}] Actividad sospechosa detectada. Probabilidad: {probability:.3f}")
                return True
            else:
                # Solo mostrar tráfico benigno ocasionalmente para no saturar
                if self.stats['analyzed_sequences'] % 50 == 0:  # Cada 50 secuencias
                    print(f"✅ [{timestamp}] Tráfico benigno. Probabilidad: {probability:.3f}")
                return False
            
        except Exception as e:
            return False
    
    def analysis_worker(self):
        """Worker thread para análisis de secuencias"""
        while self.running:
            try:
                sequence = self.analysis_queue.get(timeout=1)
                self.analyze_sequence(sequence)
                self.analysis_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                continue
    
    def start_sniffing(self, interface=None):
        """Iniciar el sniffing de red"""
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Iniciar worker thread para análisis
        analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)
        analysis_thread.start()
        
        print(f"🔄 Iniciando captura de tráfico en interfaz: {interface or 'todas'}")
        print("🛑 Presiona Ctrl+C para detener")
        print("=" * 60)
        
        try:
            # Capturar paquetes
            sniff(
                iface=interface,
                prn=self.packet_callback,
                store=0,  # No almacenar paquetes en memoria
                stop_filter=lambda x: not self.running
            )
        except KeyboardInterrupt:
            self.running = False
            print("\n🛑 Deteniendo captura...")
        except Exception as e:
            print(f"❌ Error en captura: {e}")
            self.running = False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sniffer conservador de red para detección de ransomware')
    parser.add_argument('--interface', '-i', help='Interfaz de red a monitorear (ej: eth0, en0)')
    parser.add_argument('--model', help='Ruta al modelo (opcional)')
    parser.add_argument('--threshold', '-t', type=float, default=0.7, help='Umbral para detecciones sospechosas (default: 0.7)')
    parser.add_argument('--high-risk', '-r', type=float, default=0.9, help='Umbral para alto riesgo (default: 0.9)')
    
    args = parser.parse_args()
    
    print("🛡️ DETECTOR CONSERVADOR DE RANSOMWARE EN TIEMPO REAL")
    print("=" * 60)
    
    # Inicializar detector
    detector = ConservativeRansomwareDetector(args.model)
    
    # Aplicar umbrales personalizados si se proporcionan
    if args.threshold:
        detector.SUSPICIOUS_THRESHOLD = args.threshold
    if args.high_risk:
        detector.HIGH_RISK_THRESHOLD = args.high_risk
    
    # Iniciar sniffing
    try:
        detector.start_sniffing(args.interface)
    except KeyboardInterrupt:
        detector.running = False
        print("\n🛑 Deteniendo detector...")
    
    print("\n📊 ESTADÍSTICAS FINALES:")
    print(f"   📦 Paquetes capturados: {detector.stats['total_packets']}")
    print(f"   🔄 Secuencias analizadas: {detector.stats['analyzed_sequences']}")
    print(f"   🚨 Detecciones sospechosas: {detector.stats['ransomware_detections']}")
    print(f"   🔴 Detecciones de alto riesgo: {detector.stats['high_risk_detections']}")
    
    # Calcular tasas
    if detector.stats['analyzed_sequences'] > 0:
        suspicious_rate = (detector.stats['ransomware_detections'] / detector.stats['analyzed_sequences']) * 100
        high_risk_rate = (detector.stats['high_risk_detections'] / detector.stats['analyzed_sequences']) * 100
        print(f"   📈 Tasa de detecciones sospechosas: {suspicious_rate:.1f}%")
        print(f"   📈 Tasa de alto riesgo: {high_risk_rate:.1f}%")

if __name__ == "__main__":
    main()

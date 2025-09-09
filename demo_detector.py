#!/usr/bin/env python3
"""
Script de demostración para mostrar el detector de ransomware
Lee archivos PCAP y simula el análisis en tiempo real con interfaz limpia
"""

import sys
import time
import os
from pathlib import Path
import numpy as np
from scapy.all import rdpcap, TCP, UDP, Raw
from tensorflow.keras.models import load_model
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración
PAYLOAD_LEN = 1024
SEQUENCE_LENGTH = 20
PROJECT_ROOT = Path(__file__).parent

class DemoRansomwareDetector:
    def __init__(self, model_path=None):
        """Inicializar el detector de demostración"""
        self.model_path = model_path or PROJECT_ROOT / "models" / "training" / "detection" / "convlstm_model.keras"
        self.model = None
        self.packet_buffer = []
        self.stats = {
            'total_packets': 0,
            'analyzed_sequences': 0,
            'ransomware_detections': 0,
            'high_risk_detections': 0,
            'start_time': None
        }
        
        # Umbrales para la demo
        self.SUSPICIOUS_THRESHOLD = 0.6
        self.HIGH_RISK_THRESHOLD = 0.8
        
        # Variables para el resumen en tiempo real
        self.last_detection = None
        self.last_detection_time = None
        
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
    
    def clear_screen(self):
        """Limpiar la pantalla"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_dashboard(self, pcap_file, file_type, current_packet, total_packets):
        """Mostrar dashboard en tiempo real"""
        self.clear_screen()
        
        # Header
        print("️ DEMO: DETECTOR DE RANSOMWARE EN TIEMPO REAL")
        print("=" * 70)
        print(f"📁 Archivo: {Path(pcap_file).name}")
        print(f"️  Tipo: {file_type}")
        print(f"⏰ Tiempo: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 70)
        print()
        
        # Progreso
        progress = (current_packet / total_packets) * 100
        bar_length = 50
        filled_length = int(bar_length * current_packet // total_packets)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"📊 Progreso: [{bar}] {progress:.1f}% ({current_packet}/{total_packets})")
        print()
        
        # Estadísticas
        print(" ESTADÍSTICAS EN TIEMPO REAL:")
        print(f"   📦 Paquetes procesados: {self.stats['total_packets']}")
        print(f"   🔄 Secuencias analizadas: {self.stats['analyzed_sequences']}")
        print(f"   🟡 Detecciones sospechosas: {self.stats['ransomware_detections']}")
        print(f"   🔴 Detecciones de alto riesgo: {self.stats['high_risk_detections']}")
        print()
        
        # Última detección
        if self.last_detection:
            print("🔍 ÚLTIMA DETECCIÓN:")
            print(f"   {self.last_detection}")
            print(f"   ⏰ Hora: {self.last_detection_time}")
            print()
        
        # Tasas de detección
        if self.stats['analyzed_sequences'] > 0:
            suspicious_rate = (self.stats['ransomware_detections'] / self.stats['analyzed_sequences']) * 100
            high_risk_rate = (self.stats['high_risk_detections'] / self.stats['analyzed_sequences']) * 100
            print(" TASAS DE DETECCIÓN:")
            print(f"    Tasa sospechosa: {suspicious_rate:.1f}%")
            print(f"   🔴 Tasa alto riesgo: {high_risk_rate:.1f}%")
            print()
        
        # Umbrales
        print("⚙️  CONFIGURACIÓN:")
        print(f"    Umbral sospechoso: {self.SUSPICIOUS_THRESHOLD}")
        print(f"    Umbral alto riesgo: {self.HIGH_RISK_THRESHOLD}")
        print("=" * 70)
    
    def process_packet(self, packet, packet_num, total_packets, pcap_file, file_type):
        """Procesar un paquete individual"""
        try:
            # Extraer payload
            payload = b""
            if packet.haslayer(Raw):
                payload = bytes(packet[Raw].load)
            
            # Filtrar paquetes muy pequeños
            if len(payload) < 50:
                return False
            
            # Normalizar tamaño
            if len(payload) > PAYLOAD_LEN:
                payload = payload[:PAYLOAD_LEN]
            else:
                payload = payload + bytes([0] * (PAYLOAD_LEN - len(payload)))
            
            # Convertir a array numpy
            payload_array = np.frombuffer(payload, dtype=np.uint8)
            
            # Agregar al buffer
            self.packet_buffer.append(payload_array)
            self.stats['total_packets'] += 1
            
            # Analizar cuando tengamos suficientes paquetes
            if len(self.packet_buffer) >= SEQUENCE_LENGTH:
                # Tomar los primeros SEQUENCE_LENGTH paquetes para análisis
                sequence = self.packet_buffer[:SEQUENCE_LENGTH]
                
                # Remover los paquetes analizados del buffer
                self.packet_buffer = self.packet_buffer[SEQUENCE_LENGTH:]
                
                # Analizar la secuencia
                detection = self.analyze_sequence(sequence)
                if detection:
                    self.last_detection = detection
                    self.last_detection_time = datetime.now().strftime('%H:%M:%S')
                
                # Actualizar dashboard cada análisis
                self.show_dashboard(pcap_file, file_type, packet_num, total_packets)
                return detection
            
            return False
            
        except Exception as e:
            return False
    
    def analyze_sequence(self, sequence):
        """Analizar una secuencia de paquetes"""
        try:
            # Convertir a formato del modelo
            sequence_array = np.array(sequence, dtype=np.uint8).reshape(1, SEQUENCE_LENGTH, 32, 32, 1) / 255.0
            
            # Hacer predicción
            prediction = self.model.predict(sequence_array, verbose=0)
            probability = prediction[0][1]  # Probabilidad de ransomware
            
            self.stats['analyzed_sequences'] += 1
            
            # Clasificar y retornar resultado
            if probability >= self.HIGH_RISK_THRESHOLD:
                self.stats['high_risk_detections'] += 1
                return f"🔴 ALTO RIESGO detectado! Probabilidad: {probability:.3f}"
            elif probability >= self.SUSPICIOUS_THRESHOLD:
                self.stats['ransomware_detections'] += 1
                return f"🟡 Actividad sospechosa detectada. Probabilidad: {probability:.3f}"
            else:
                return f"✅ Tráfico benigno. Probabilidad: {probability:.3f}"
                
        except Exception as e:
            return None
    
    def demo_pcap_file(self, pcap_path, file_type, delay=0.1):
        """Demostrar análisis de un archivo PCAP"""
        try:
            # Cargar paquetes
            packets = rdpcap(pcap_path)
            total_packets = len(packets)
            
            # Mostrar dashboard inicial
            self.show_dashboard(pcap_path, file_type, 0, total_packets)
            print("📂 Cargando archivo PCAP...")
            time.sleep(1)
            
            detection_found = False
            
            # Procesar paquetes
            for i, packet in enumerate(packets):
                # Procesar paquete
                if self.process_packet(packet, i + 1, total_packets, pcap_path, file_type):
                    detection_found = True
                
                # Pausa para efecto visual
                # time.sleep(delay)
            
            # Mostrar resultado final
            self.show_dashboard(pcap_path, file_type, total_packets, total_packets)
            print("📊 ANÁLISIS COMPLETADO")
            print("=" * 70)
            
            if detection_found:
                print(" RESUMEN: Se detectaron patrones sospechosos en este archivo")
            else:
                print("✅ RESUMEN: No se detectaron patrones sospechosos en este archivo")
            
            print("=" * 70)
            input("Presiona Enter para continuar...")
            
        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            input("Presiona Enter para continuar...")
    
    def run_demo(self, benign_pcap, malicious_pcap, delay=0.1):
        """Ejecutar demostración completa"""
        self.stats['start_time'] = datetime.now()
        
        print("🎬 INICIANDO DEMOSTRACIÓN DEL DETECTOR DE RANSOMWARE")
        print("=" * 70)
        print("Esta demo mostrará cómo el detector analiza tráfico de red")
        print("y detecta patrones de ransomware en tiempo real.")
        print("=" * 70)
        input("Presiona Enter para comenzar...")
        
        # Demo con archivo benigno
        print("\n🟢 FASE 1: ANÁLISIS DE TRÁFICO BENIGNO")
        print("=" * 70)
        self.demo_pcap_file(benign_pcap, "TRÁFICO BENIGNO", delay)
        
        # Resetear estadísticas
        self.stats = {
            'total_packets': 0,
            'analyzed_sequences': 0,
            'ransomware_detections': 0,
            'high_risk_detections': 0,
            'start_time': datetime.now()
        }
        self.packet_buffer = []
        self.last_detection = None
        self.last_detection_time = None
        
        # Demo con archivo malicioso
        print("\n🔴 FASE 2: ANÁLISIS DE TRÁFICO MALICIOSO")
        print("=" * 70)
        self.demo_pcap_file(malicious_pcap, "TRÁFICO MALICIOSO", delay)
        
        # Resumen final
        print("\n🎯 DEMOSTRACIÓN COMPLETADA")
        print("=" * 70)
        print("El detector ha demostrado su capacidad para:")
        print("✅ Analizar tráfico de red en tiempo real")
        print("✅ Detectar patrones de ransomware")
        print("✅ Clasificar tráfico como benigno o malicioso")
        print("✅ Proporcionar alertas de seguridad")
        print("=" * 70)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Demo del detector de ransomware')
    parser.add_argument('--benign', '-b', required=True, help='Archivo PCAP con tráfico benigno')
    parser.add_argument('--malicious', '-m', required=True, help='Archivo PCAP con tráfico malicioso')
    parser.add_argument('--model', help='Ruta al modelo (opcional)')
    parser.add_argument('--delay', '-d', type=float, default=0.1, help='Delay entre paquetes (segundos)')
    parser.add_argument('--threshold', '-t', type=float, default=0.6, help='Umbral para detecciones sospechosas')
    parser.add_argument('--high-risk', '-r', type=float, default=0.8, help='Umbral para alto riesgo')
    
    args = parser.parse_args()
    
    # Verificar archivos
    if not Path(args.benign).exists():
        print(f"❌ Archivo benigno no encontrado: {args.benign}")
        sys.exit(1)
    
    if not Path(args.malicious).exists():
        print(f"❌ Archivo malicioso no encontrado: {args.malicious}")
        sys.exit(1)
    
    # Crear detector
    detector = DemoRansomwareDetector(args.model)
    
    # Configurar umbrales
    detector.SUSPICIOUS_THRESHOLD = args.threshold
    detector.HIGH_RISK_THRESHOLD = args.high_risk
    
    # Ejecutar demo
    detector.run_demo(args.benign, args.malicious, args.delay)

if __name__ == "__main__":
    main()

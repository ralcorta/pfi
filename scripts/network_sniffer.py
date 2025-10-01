#!/usr/bin/env python3
"""
Sniffer de red en tiempo real para detección de ransomware
Interfaz limpia que actualiza la consola sin hacer scroll
"""

import sys
import time
import threading
import queue
from pathlib import Path
import numpy as np
from scapy.all import sniff, TCP, UDP, Raw, IP
from tensorflow.keras.models import load_model
import curses
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración
PAYLOAD_LEN = 1024
SEQUENCE_LENGTH = 20
PROJECT_ROOT = Path(__file__).parent

class RealTimeRansomwareDetector:
    def __init__(self, model_path=None):
        """Inicializar el detector en tiempo real"""
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
        
        # Lista para almacenar las últimas detecciones
        self.recent_detections = []
        self.max_recent_detections = 10  # Mostrar las últimas 10 detecciones
        
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
        
        # Solo procesar paquetes con payload
        if (packet.haslayer(TCP) or packet.haslayer(UDP)) and packet.haslayer(Raw):
            try:
                payload = bytes(packet[Raw].load)
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
        """Analizar una secuencia de paquetes"""
        try:
            # Crear secuencia para el modelo
            sequence_array = np.array(sequence, dtype=np.uint8).reshape(1, SEQUENCE_LENGTH, 32, 32, 1) / 255.0
            
            # Realizar predicción
            prediction = self.model.predict(sequence_array, verbose=0)
            probability = prediction[0][1]  # Probabilidad de ransomware
            class_pred = np.argmax(prediction[0])
            
            self.stats['analyzed_sequences'] += 1
            
            # Crear registro de detección
            detection = {
                'timestamp': datetime.now(),
                'probability': probability,
                'class': class_pred,
                'is_malware': class_pred == 1,
                'high_risk': probability > 0.8
            }
            
            # Actualizar contadores
            if class_pred == 1:  # Ransomware detectado
                self.stats['ransomware_detections'] += 1
                if probability > 0.8:
                    self.stats['high_risk_detections'] += 1
            
            # Agregar a la lista de detecciones recientes
            self.recent_detections.append(detection)
            if len(self.recent_detections) > self.max_recent_detections:
                self.recent_detections.pop(0)  # Remover la más antigua
            
            return detection
            
        except Exception as e:
            return None
    
    def analysis_worker(self):
        """Worker thread para análisis de secuencias"""
        while self.running:
            try:
                sequence = self.analysis_queue.get(timeout=1)
                result = self.analyze_sequence(sequence)
                if result:
                    # Aquí podrías enviar alertas, logs, etc.
                    pass
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
            print("\n�� Deteniendo captura...")
        except Exception as e:
            print(f"❌ Error en captura: {e}")
            self.running = False

def init_curses():
    """Inicializar curses para interfaz limpia"""
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)  # Ocultar cursor
    return stdscr

def cleanup_curses(stdscr):
    """Limpiar curses"""
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()

def display_dashboard(stdscr, detector):
    """Mostrar dashboard en tiempo real"""
    stdscr.clear()
    
    # Título
    stdscr.addstr(0, 0, "🛡️ DETECTOR DE RANSOMWARE EN TIEMPO REAL", curses.A_BOLD)
    stdscr.addstr(1, 0, "=" * 60, curses.A_BOLD)
    
    # Estadísticas generales
    stdscr.addstr(3, 0, "📊 ESTADÍSTICAS GENERALES:", curses.A_BOLD)
    stdscr.addstr(4, 2, f"⏱️  Tiempo activo: {datetime.now() - detector.stats['start_time']}")
    stdscr.addstr(5, 2, f"📦 Paquetes sniffeados: {detector.stats['total_packets']}")
    stdscr.addstr(6, 2, f"🔄 Secuencias analizadas: {detector.stats['analyzed_sequences']}")
    
    # Contadores de detección
    stdscr.addstr(8, 0, "🎯 CONTADORES DE DETECCIÓN:", curses.A_BOLD)
    benign_count = detector.stats['analyzed_sequences'] - detector.stats['ransomware_detections']
    stdscr.addstr(9, 2, f"✅ Paquetes BENIGNOS: {benign_count}", curses.color_pair(3))
    stdscr.addstr(10, 2, f"🚨 Paquetes MALICIOSOS: {detector.stats['ransomware_detections']}", curses.color_pair(1))
    stdscr.addstr(11, 2, f"🔴 Alto riesgo: {detector.stats['high_risk_detections']}", curses.color_pair(1))
    
    # Porcentajes
    if detector.stats['analyzed_sequences'] > 0:
        benign_percent = (benign_count / detector.stats['analyzed_sequences']) * 100
        malware_percent = (detector.stats['ransomware_detections'] / detector.stats['analyzed_sequences']) * 100
        stdscr.addstr(12, 2, f"📊 Benignos: {benign_percent:.1f}% | Maliciosos: {malware_percent:.1f}%")
    
    # Estado actual
    stdscr.addstr(14, 0, "📡 ESTADO ACTUAL:", curses.A_BOLD)
    if detector.stats['analyzed_sequences'] > 0:
        detection_rate = (detector.stats['ransomware_detections'] / detector.stats['analyzed_sequences']) * 100
        
        if detection_rate > 10:
            stdscr.addstr(15, 2, "🚨 ALERTA: Alta tasa de detección!", curses.A_BOLD | curses.color_pair(1))
        elif detection_rate > 5:
            stdscr.addstr(15, 2, "⚠️  ADVERTENCIA: Tasa de detección moderada", curses.A_BOLD | curses.color_pair(2))
        else:
            stdscr.addstr(15, 2, "✅ Estado normal", curses.A_BOLD | curses.color_pair(3))
    else:
        stdscr.addstr(15, 2, "⏳ Esperando datos...")
    
    # Buffer de paquetes
    stdscr.addstr(17, 0, " BUFFER:", curses.A_BOLD)
    stdscr.addstr(18, 2, f" Paquetes en buffer: {len(detector.packet_buffer)}")
    stdscr.addstr(19, 2, f"🔄 Cola de análisis: {detector.analysis_queue.qsize()}")
    
    # Detecciones recientes
    stdscr.addstr(21, 0, "🔍 DETECCIONES RECIENTES:", curses.A_BOLD)
    if detector.recent_detections:
        for i, detection in enumerate(reversed(detector.recent_detections[-5:])):  # Mostrar las últimas 5
            timestamp = detection['timestamp'].strftime('%H:%M:%S')
            prob = detection['probability']
            
            if detection['is_malware']:
                if detection['high_risk']:
                    status = "🔴 ALTO RIESGO"
                    color = curses.color_pair(1)
                else:
                    status = "🟡 SOSPECHOSO"
                    color = curses.color_pair(2)
            else:
                status = "✅ BENIGNO"
                color = curses.color_pair(3)
            
            stdscr.addstr(22 + i, 2, f"{timestamp} - {status} ({prob:.3f})", color)
    else:
        stdscr.addstr(22, 2, "⏳ No hay detecciones recientes")
    
    # Instrucciones
    start_y = 28 if detector.recent_detections else 24
    stdscr.addstr(start_y, 0, "💡 CONTROLES:", curses.A_BOLD)
    stdscr.addstr(start_y + 1, 2, "• Presiona 'q' para salir")
    stdscr.addstr(start_y + 2, 2, "• Presiona 'r' para resetear estadísticas")
    stdscr.addstr(start_y + 3, 2, "• Presiona 's' para mostrar detalles")
    
    # Timestamp
    stdscr.addstr(start_y + 4, 0, f"🕐 Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    
    stdscr.refresh()

def show_detailed_stats(stdscr, detector):
    """Mostrar estadísticas detalladas"""
    stdscr.clear()
    
    stdscr.addstr(0, 0, "📊 ESTADÍSTICAS DETALLADAS", curses.A_BOLD)
    stdscr.addstr(1, 0, "=" * 40, curses.A_BOLD)
    
    # Estadísticas generales
    stdscr.addstr(3, 0, "📦 PAQUETES:")
    stdscr.addstr(4, 2, f"Total sniffeados: {detector.stats['total_packets']}")
    stdscr.addstr(5, 2, f"Con payload válido: {detector.stats['analyzed_sequences'] * SEQUENCE_LENGTH}")
    
    # Detecciones
    benign_count = detector.stats['analyzed_sequences'] - detector.stats['ransomware_detections']
    stdscr.addstr(7, 0, " DETECCIONES:")
    stdscr.addstr(8, 2, f"Benignos: {benign_count}")
    stdscr.addstr(9, 2, f"Maliciosos: {detector.stats['ransomware_detections']}")
    stdscr.addstr(10, 2, f"Alto riesgo: {detector.stats['high_risk_detections']}")
    
    # Porcentajes
    if detector.stats['analyzed_sequences'] > 0:
        benign_percent = (benign_count / detector.stats['analyzed_sequences']) * 100
        malware_percent = (detector.stats['ransomware_detections'] / detector.stats['analyzed_sequences']) * 100
        stdscr.addstr(12, 0, "📊 PORCENTAJES:")
        stdscr.addstr(13, 2, f"Benignos: {benign_percent:.2f}%")
        stdscr.addstr(14, 2, f"Maliciosos: {malware_percent:.2f}%")
    
    # Tiempo
    if detector.stats['start_time']:
        elapsed = datetime.now() - detector.stats['start_time']
        stdscr.addstr(16, 0, "⏱️  TIEMPO:")
        stdscr.addstr(17, 2, f"Activo: {elapsed}")
        if detector.stats['analyzed_sequences'] > 0:
            packets_per_second = detector.stats['total_packets'] / elapsed.total_seconds()
            stdscr.addstr(18, 2, f"Paquetes/segundo: {packets_per_second:.2f}")
    
    stdscr.addstr(20, 0, "Presiona cualquier tecla para volver...")
    stdscr.refresh()
    stdscr.getch()

def show_alert(stdscr, detection):
    """Mostrar alerta en tiempo real"""
    stdscr.clear()
    
    timestamp = detection['timestamp'].strftime('%H:%M:%S')
    prob = detection['probability']
    
    stdscr.addstr(0, 0, "🚨 ALERTA DE DETECCIÓN", curses.A_BOLD | curses.color_pair(1))
    stdscr.addstr(1, 0, "=" * 30, curses.A_BOLD)
    
    if detection['high_risk']:
        stdscr.addstr(3, 0, "🚨 ALTO RIESGO DETECTADO!", curses.A_BOLD | curses.color_pair(1))
        stdscr.addstr(4, 0, f"Probabilidad: {prob:.3f} ({prob*100:.1f}%)")
        stdscr.addstr(5, 0, f"Timestamp: {timestamp}")
        stdscr.addstr(6, 0, "⚠️  Posible ransomware en tráfico de red")
    elif detection['is_malware']:
        stdscr.addstr(3, 0, "🟡 ACTIVIDAD SOSPECHOSA", curses.A_BOLD | curses.color_pair(2))
        stdscr.addstr(4, 0, f"Probabilidad: {prob:.3f} ({prob*100:.1f}%)")
        stdscr.addstr(5, 0, f"Timestamp: {timestamp}")
        stdscr.addstr(6, 0, "⚠️  Patrones inusuales detectados")
    else:
        stdscr.addstr(3, 0, "✅ TRÁFICO BENIGNO", curses.A_BOLD | curses.color_pair(3))
        stdscr.addstr(4, 0, f"Probabilidad: {prob:.3f} ({prob*100:.1f}%)")
        stdscr.addstr(5, 0, f"Timestamp: {timestamp}")
    
    stdscr.addstr(8, 0, "Presiona cualquier tecla para continuar...")
    stdscr.refresh()
    stdscr.getch()

def main_dashboard(detector):
    """Función principal del dashboard"""
    stdscr = init_curses()
    
    # Configurar colores
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)    # Rojo para alertas
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Amarillo para advertencias
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Verde para normal
    
    try:
        while detector.running:
            display_dashboard(stdscr, detector)
            
            # Verificar input del usuario con timeout más corto
            stdscr.timeout(500)  # Timeout de 0.5 segundos para actualizaciones más frecuentes
            key = stdscr.getch()
            
            if key == ord('q'):
                detector.running = False
                break
            elif key == ord('r'):
                # Resetear estadísticas
                detector.stats = {
                    'total_packets': 0,
                    'analyzed_sequences': 0,
                    'ransomware_detections': 0,
                    'high_risk_detections': 0,
                    'start_time': datetime.now()
                }
                detector.recent_detections = []
            elif key == ord('s'):
                # Mostrar estadísticas detalladas
                show_detailed_stats(stdscr, detector)
            elif key == ord('a'):
                # Mostrar alertas recientes
                if detector.recent_detections:
                    show_alert(stdscr, detector.recent_detections[-1])
                
    except KeyboardInterrupt:
        detector.running = False
    finally:
        cleanup_curses(stdscr)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sniffer de red en tiempo real para detección de ransomware')
    parser.add_argument('--interface', '-i', help='Interfaz de red a monitorear (ej: eth0, en0)')
    parser.add_argument('--model', help='Ruta al modelo (opcional)')
    
    args = parser.parse_args()
    
    print("🛡️ INICIANDO DETECTOR DE RANSOMWARE EN TIEMPO REAL")
    print("=" * 60)
    
    # Inicializar detector
    detector = RealTimeRansomwareDetector(args.model)
    
    # Iniciar dashboard en un thread separado
    dashboard_thread = threading.Thread(target=main_dashboard, args=(detector,), daemon=True)
    dashboard_thread.start()
    
    # Iniciar sniffing
    try:
        detector.start_sniffing(args.interface)
    except KeyboardInterrupt:
        detector.running = False
        print("\n🛑 Deteniendo detector...")
    
    print("\n📊 ESTADÍSTICAS FINALES:")
    print(f"   📦 Paquetes capturados: {detector.stats['total_packets']}")
    print(f"   🔄 Secuencias analizadas: {detector.stats['analyzed_sequences']}")
    print(f"   🚨 Detecciones de ransomware: {detector.stats['ransomware_detections']}")
    print(f"   🔴 Detecciones de alto riesgo: {detector.stats['high_risk_detections']}")

if __name__ == "__main__":
    main()

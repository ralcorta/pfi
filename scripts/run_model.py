#!/usr/bin/env python3
"""
Script simplificado para evaluar archivos PCAP con el modelo de detección de ransomware
"""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
from scapy.all import rdpcap, TCP, UDP, Raw
from tensorflow.keras.models import load_model
import warnings
warnings.filterwarnings('ignore')

# Configuración
PAYLOAD_LEN = 1024
SEQUENCE_LENGTH = 20
PROJECT_ROOT = Path(__file__).parent

class SimpleRansomwareDetector:
    def __init__(self, model_path=None):
        """Inicializar el detector de ransomware"""
        self.model_path = model_path or PROJECT_ROOT / "models" / "training" / "detection" / "convlstm_model.keras"
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Cargar el modelo entrenado"""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Modelo no encontrado: {self.model_path}")
            
            print(f"🔄 Cargando modelo desde: {self.model_path}")
            self.model = load_model(str(self.model_path))
            print("✅ Modelo cargado exitosamente")
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            sys.exit(1)
    
    def process_pcap_file(self, pcap_path):
        """Procesar un archivo PCAP y extraer datos de manera simple"""
        print(f"\n🔍 Procesando: {pcap_path}")
        
        try:
            packets = rdpcap(str(pcap_path))
            print(f"   Total de paquetes: {len(packets)}")
            
            # Extraer solo payloads de manera simple
            payloads = []
            
            for pkt in packets:
                if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
                    try:
                        payload = bytes(pkt[Raw].load)
                        # Asegurar que el payload tenga exactamente PAYLOAD_LEN bytes
                        if len(payload) > PAYLOAD_LEN:
                            payload = payload[:PAYLOAD_LEN]
                        else:
                            payload = payload + bytes([0] * (PAYLOAD_LEN - len(payload)))
                        
                        # Convertir a array de numpy directamente
                        payload_array = np.frombuffer(payload, dtype=np.uint8)
                        payloads.append(payload_array)
                        
                    except Exception as e:
                        # Saltar paquetes problemáticos silenciosamente
                        continue
            
            if len(payloads) < SEQUENCE_LENGTH:
                print(f"   ⚠️ Insuficientes paquetes para análisis (necesarios: {SEQUENCE_LENGTH}, encontrados: {len(payloads)})")
                return None
            
            print(f"   📊 Paquetes con payload válidos: {len(payloads)}")
            
            # Crear secuencias de manera simple
            num_sequences = len(payloads) // SEQUENCE_LENGTH
            sequences = []
            
            for i in range(num_sequences):
                start_idx = i * SEQUENCE_LENGTH
                end_idx = start_idx + SEQUENCE_LENGTH
                
                seq_payloads = payloads[start_idx:end_idx]
                
                # Crear secuencia de imágenes (32x32) - forma más simple
                sequence = np.array(seq_payloads, dtype=np.uint8).reshape(SEQUENCE_LENGTH, 32, 32, 1) / 255.0
                sequences.append(sequence)
            
            print(f"   📊 Secuencias creadas: {len(sequences)}")
            
            return {
                'sequences': np.array(sequences),
                'total_packets': len(payloads),
                'num_sequences': num_sequences
            }
            
        except Exception as e:
            print(f"   ❌ Error procesando archivo: {e}")
            return None
    
    def predict(self, sequences):
        """Realizar predicciones de manera simple"""
        try:
            predictions = self.model.predict(sequences, verbose=0)
            probabilities = predictions[:, 1]  # Probabilidad de ransomware
            classes = np.argmax(predictions, axis=1)
            
            return {
                'probabilities': probabilities,
                'classes': classes,
                'predictions': predictions
            }
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return None
    
    def analyze_results(self, results, pcap_name):
        """Analizar y mostrar resultados de manera simple"""
        if not results:
            return
        
        probabilities = results['probabilities']
        classes = results['classes']
        
        # Estadísticas básicas
        total_sequences = len(classes)
        ransomware_sequences = np.sum(classes)
        benign_sequences = total_sequences - ransomware_sequences
        
        # Análisis de confianza
        high_confidence = np.sum(probabilities > 0.8)
        medium_confidence = np.sum((probabilities > 0.5) & (probabilities <= 0.8))
        low_confidence = np.sum(probabilities <= 0.5)
        
        print(f"\n RESULTADOS PARA: {pcap_name}")
        print("=" * 60)
        print(f"📦 Secuencias analizadas: {total_sequences}")
        print(f"✅ Secuencias benignas: {benign_sequences} ({100*benign_sequences/total_sequences:.1f}%)")
        print(f"🚨 Secuencias de ransomware: {ransomware_sequences} ({100*ransomware_sequences/total_sequences:.1f}%)")
        
        print(f"\n🎯 ANÁLISIS DE CONFIANZA:")
        print(f"   🔴 Alta confianza (>80%): {high_confidence} secuencias")
        print(f"   🟡 Confianza media (50-80%): {medium_confidence} secuencias")
        print(f"   🟢 Baja confianza (<50%): {low_confidence} secuencias")
        
        # Probabilidades promedio
        avg_prob = np.mean(probabilities)
        max_prob = np.max(probabilities)
        
        print(f"\n PROBABILIDADES:")
        print(f"   📊 Probabilidad promedio: {avg_prob:.3f}")
        print(f"   📈 Probabilidad máxima: {max_prob:.3f}")
        
        # Clasificación final
        if avg_prob > 0.7:
            verdict = "🚨 ALTO RIESGO - Posible ransomware detectado"
        elif avg_prob > 0.4:
            verdict = "⚠️ RIESGO MEDIO - Actividad sospechosa"
        else:
            verdict = "✅ BAJO RIESGO - Tráfico aparentemente benigno"
        
        print(f"\n🎯 VEREDICTO: {verdict}")
        print("=" * 60)
        
        return {
            'pcap_name': pcap_name,
            'total_sequences': total_sequences,
            'ransomware_sequences': ransomware_sequences,
            'benign_sequences': benign_sequences,
            'avg_probability': avg_prob,
            'max_probability': max_prob,
            'verdict': verdict
        }

def main():
    parser = argparse.ArgumentParser(description='Detector Simple de Ransomware en archivos PCAP')
    parser.add_argument('pcap_file', help='Archivo PCAP a analizar')
    parser.add_argument('--model', help='Ruta al modelo (opcional)')
    
    args = parser.parse_args()
    
    print("🛡️ DETECTOR SIMPLE DE RANSOMWARE")
    print("=" * 60)
    
    # Inicializar detector
    detector = SimpleRansomwareDetector(args.model)
    
    # Procesar archivo
    pcap_path = Path(args.pcap_file)
    
    if pcap_path.is_file() and pcap_path.suffix == '.pcap':
        # Archivo individual
        data = detector.process_pcap_file(pcap_path)
        if data:
            results = detector.predict(data['sequences'])
            if results:
                detector.analyze_results(results, pcap_path.name)
    
    elif pcap_path.is_dir():
        # Directorio de archivos
        pcap_files = list(pcap_path.glob("*.pcap"))
        if not pcap_files:
            print(f"❌ No se encontraron archivos .pcap en: {pcap_path}")
            return
        
        print(f"📁 Procesando {len(pcap_files)} archivos PCAP...")
        
        all_results = []
        for pcap_file in pcap_files:
            data = detector.process_pcap_file(pcap_file)
            if data:
                results = detector.predict(data['sequences'])
                if results:
                    result = detector.analyze_results(results, pcap_file.name)
                    all_results.append(result)
        
        # Resumen general
        if all_results:
            print(f"\n RESUMEN GENERAL")
            print("=" * 60)
            total_files = len(all_results)
            high_risk_files = sum(1 for r in all_results if r['avg_probability'] > 0.7)
            medium_risk_files = sum(1 for r in all_results if 0.4 < r['avg_probability'] <= 0.7)
            low_risk_files = sum(1 for r in all_results if r['avg_probability'] <= 0.4)
            
            print(f"📁 Archivos analizados: {total_files}")
            print(f" Alto riesgo: {high_risk_files}")
            print(f"⚠️ Riesgo medio: {medium_risk_files}")
            print(f"✅ Bajo riesgo: {low_risk_files}")
    
    else:
        print(f"❌ Archivo o directorio no encontrado: {pcap_path}")

if __name__ == "__main__":
    main()

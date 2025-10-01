#!/usr/bin/env python3
"""
Script simple para analizar archivos .pcap con el modelo de detección de ransomware
Autor: Rodrigo Alcorta
"""

import os
import sys
import numpy as np
import tensorflow as tf
from pathlib import Path
from scapy.all import rdpcap, TCP, UDP, Raw
import argparse

# Obtener la ruta root del proyecto (donde está pyproject.toml)
PROJECT_ROOT = Path(__file__).parent.parent.parent
print(f"📁 Proyecto root: {PROJECT_ROOT}")

# Configuración
PAYLOAD_LEN = 1024  # Tamaño fijo del payload (32x32 = 1024 bytes)
SEQUENCE_LENGTH = 20  # Número de paquetes por secuencia
GRID_SIZE = 32  # Tamaño de la grilla (32x32)

# Rutas por defecto basadas en PROJECT_ROOT
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "training" / "detection" / "convlstm_model.keras"

def extract_packets_from_pcap(pcap_path):
    """
    Extrae paquetes TCP/UDP con payload del archivo .pcap
    
    Args:
        pcap_path (str): Ruta al archivo .pcap
        
    Returns:
        list: Lista de payloads extraídos
    """
    print(f"📦 Extrayendo paquetes de: {pcap_path}")
    
    try:
        # Cargar el archivo .pcap
        packets = rdpcap(pcap_path)
        print(f"   📊 Total de paquetes: {len(packets)}")
        
        payloads = []
        discarded = 0
        
        # Procesar cada paquete
        for i, pkt in enumerate(packets):
            # Solo procesar paquetes TCP/UDP con payload
            if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
                try:
                    # Extraer el payload
                    payload = bytes(pkt[Raw].load)
                    
                    # Completar con 0s si es muy corto (en lugar de descartar)
                    # Truncar o rellenar a PAYLOAD_LEN bytes
                    if len(payload) > PAYLOAD_LEN:
                        payload = payload[:PAYLOAD_LEN]
                    else:
                        payload = payload + bytes([0] * (PAYLOAD_LEN - len(payload)))
                    
                    payloads.append(payload)
                    
                except Exception as e:
                    print(f"   ⚠️ Error procesando paquete {i}: {e}")
                    discarded += 1
        
        print(f"   ✅ Paquetes válidos: {len(payloads)}")
        print(f"   ❌ Paquetes con errores: {discarded}")
        
        return payloads
        
    except Exception as e:
        print(f"❌ Error leyendo archivo .pcap: {e}")
        return []

def payloads_to_sequences(payloads, max_sequences=None):
    """
    Convierte lista de payloads en secuencias para el modelo
    
    Args:
        payloads (list): Lista de payloads
        max_sequences (int): Máximo número de secuencias a generar
        
    Returns:
        np.array: Array de secuencias (N, 20, 32, 32, 1)
    """
    print(f"🔄 Convirtiendo {len(payloads)} payloads a secuencias...")
    
    if len(payloads) < SEQUENCE_LENGTH:
        print(f"   ⚠️ No hay suficientes paquetes ({len(payloads)} < {SEQUENCE_LENGTH})")
        return np.array([])
    
    sequences = []
    num_sequences = min(len(payloads) - SEQUENCE_LENGTH + 1, max_sequences or len(payloads))
    
    for i in range(num_sequences):
        # Tomar una ventana deslizante de SEQUENCE_LENGTH paquetes
        sequence_payloads = payloads[i:i + SEQUENCE_LENGTH]
        
        # Convertir cada payload a matriz 32x32
        sequence_matrix = []
        for payload in sequence_payloads:
            # Convertir bytes a matriz 32x32
            matrix = np.frombuffer(payload, dtype=np.uint8).reshape(GRID_SIZE, GRID_SIZE)
            # Normalizar a [0, 1]
            matrix = matrix.astype(np.float32) / 255.0
            sequence_matrix.append(matrix)
        
        # Agregar dimensión de canal
        sequence_array = np.array(sequence_matrix).reshape(SEQUENCE_LENGTH, GRID_SIZE, GRID_SIZE, 1)
        sequences.append(sequence_array)
    
    print(f"   ✅ Generadas {len(sequences)} secuencias")
    return np.array(sequences)

def load_model(model_path):
    """
    Carga el modelo entrenado
    
    Args:
        model_path (str): Ruta al modelo .keras
        
    Returns:
        tf.keras.Model: Modelo cargado
    """
    print(f"🤖 Cargando modelo: {model_path}")
    
    try:
        model = tf.keras.models.load_model(model_path)
        print(f"   ✅ Modelo cargado exitosamente")
        print(f"   📊 Arquitectura: {model.input_shape} -> {model.output_shape}")
        return model
    except Exception as e:
        print(f"   ❌ Error cargando modelo: {e}")
        return None

def analyze_sequences(model, sequences):
    """
    Analiza las secuencias con el modelo
    
    Args:
        model: Modelo entrenado
        sequences: Array de secuencias
        
    Returns:
        dict: Resultados del análisis
    """
    print(f"🔍 Analizando {len(sequences)} secuencias...")
    
    if len(sequences) == 0:
        return {"error": "No hay secuencias para analizar"}
    
    try:
        # Hacer predicciones
        predictions = model.predict(sequences, verbose=0)
        
        # Interpretar resultados
        results = {
            "total_sequences": len(sequences),
            "malware_probabilities": predictions[:, 1],  # Probabilidad de malware
            "benign_probabilities": predictions[:, 0],   # Probabilidad de benigno
            "malware_detections": np.sum(predictions[:, 1] > 0.5),  # Cuántas secuencias son malware
            "max_malware_prob": float(np.max(predictions[:, 1])),
            "avg_malware_prob": float(np.mean(predictions[:, 1])),
            "is_ransomware": np.mean(predictions[:, 1]) > 0.5  # Decisión final
        }
        
        print(f"   📊 Secuencias analizadas: {results['total_sequences']}")
        print(f"   🦠 Detecciones de malware: {results['malware_detections']}")
        print(f"   📈 Probabilidad máxima de malware: {results['max_malware_prob']:.3f}")
        print(f"   📊 Probabilidad promedio de malware: {results['avg_malware_prob']:.3f}")
        
        return results
        
    except Exception as e:
        print(f"   ❌ Error en análisis: {e}")
        return {"error": str(e)}

def main():
    """
    Función principal del script
    """
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Analizar archivos .pcap para detectar ransomware')
    parser.add_argument('pcap_file', help='Ruta al archivo .pcap a analizar')
    parser.add_argument('--model', default=str(DEFAULT_MODEL_PATH), 
                       help=f'Ruta al modelo entrenado (default: {DEFAULT_MODEL_PATH})')
    parser.add_argument('--max-sequences', type=int, default=100,
                       help='Máximo número de secuencias a analizar')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Umbral para clasificación (default: 0.5)')
    
    args = parser.parse_args()
    
    print("🛡️ ANALIZADOR DE RANSOMWARE EN ARCHIVOS .PCAP")
    print("=" * 50)
    
    # Convertir rutas relativas a absolutas basadas en PROJECT_ROOT
    pcap_path = args.pcap_file
    if not os.path.isabs(pcap_path):
        # Si es relativa, asumir que es relativa al directorio actual
        pcap_path = os.path.abspath(pcap_path)
    
    model_path = args.model
    if not os.path.isabs(model_path):
        # Si es relativa, asumir que es relativa a PROJECT_ROOT
        model_path = str(PROJECT_ROOT / model_path)
    
    print(f"📁 Archivo .pcap: {pcap_path}")
    print(f"🤖 Modelo: {model_path}")
    
    # Verificar que el archivo .pcap existe
    if not os.path.exists(pcap_path):
        print(f"❌ Error: El archivo {pcap_path} no existe")
        sys.exit(1)
    
    # Verificar que el modelo existe
    if not os.path.exists(model_path):
        print(f"❌ Error: El modelo {model_path} no existe")
        print(f"💡 Sugerencia: Verifica que el modelo esté en: {DEFAULT_MODEL_PATH}")
        sys.exit(1)
    
    # Paso 1: Cargar el modelo
    model = load_model(model_path)
    if model is None:
        sys.exit(1)
    
    # Paso 2: Extraer paquetes del .pcap
    payloads = extract_packets_from_pcap(pcap_path)
    if not payloads:
        print("❌ No se pudieron extraer paquetes válidos")
        sys.exit(1)
    
    # Paso 3: Convertir a secuencias
    sequences = payloads_to_sequences(payloads, args.max_sequences)
    if len(sequences) == 0:
        print("❌ No se pudieron generar secuencias válidas")
        sys.exit(1)
    
    # Paso 4: Analizar con el modelo
    results = analyze_sequences(model, sequences)
    
    # Paso 5: Mostrar resultados finales
    print("\n" + "=" * 50)
    print("📋 RESULTADOS DEL ANÁLISIS")
    print("=" * 50)
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
    else:
        # Decisión final
        if results["is_ransomware"]:
            print("🚨 RESULTADO: RANSOMWARE DETECTADO")
            print(f"   📊 Confianza: {results['avg_malware_prob']:.1%}")
        else:
            print("✅ RESULTADO: TRÁFICO BENIGNO")
            print(f"   📊 Confianza: {results['avg_malware_prob']:.1%}")
        
        print(f"\n📈 Detalles:")
        print(f"   • Secuencias analizadas: {results['total_sequences']}")
        print(f"   • Detecciones de malware: {results['malware_detections']}")
        print(f"   • Probabilidad máxima: {results['max_malware_prob']:.3f}")
        print(f"   • Probabilidad promedio: {results['avg_malware_prob']:.3f}")

if __name__ == "__main__":
    main()
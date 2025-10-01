# app/sensor/src/ai_model_processor.py
import time
import logging
from typing import Optional, Dict, Any
from scapy.all import Raw, Packet
import numpy as np
import tensorflow as tf


class AIModelProcessor:
    """Procesador de paquetes con modelo de IA"""
    
    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path or "models/training/detection/convlstm_model.keras"
        self.model: Optional[tf.keras.Model] = None
        self.packet_buffer: list[bytes] = []
        self.buffer_size: int = 20  # Tamaño de secuencia para el modelo
        self.package_size: int = 1024  # Tamaño de secuencia para el modelo
        
        # Configurar logging
        self.logger: logging.Logger = logging.getLogger(__name__)
    
    def load_model(self) -> None:
        """Carga el modelo de IA"""
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            self.logger.info(f"✅ Modelo de IA cargado: {self.model_path}")
        except Exception as e:
            self.logger.error(f"❌ Error cargando modelo: {e}")
            raise
    
    def extract_payload(self, packet: Packet) -> Optional[bytes]:
        """Extrae payload del paquete TCP"""
        if packet.haslayer(Raw):
            payload = bytes(packet[Raw].load)
            # Normalizar tamaño a 1024 bytes
            if len(payload) < self.package_size:
                payload += b'\x00' * (self.package_size - len(payload))
            if len(payload) > self.package_size:
                payload = payload[:self.package_size]
            return payload
        return None
    
    def process_packet(self, packet: Packet) -> Optional[Dict[str, Any]]:
        """Procesa un paquete TCP individual"""
        # Extraer payload
        payload = self.extract_payload(packet)
        if payload is None:
            return None
        
        # Agregar al buffer
        self.packet_buffer.append(payload)
        
        # Si el buffer está lleno, procesar con el modelo
        if len(self.packet_buffer) >= self.buffer_size:
            result = self.analyze_with_model()
            # Mantener solo los últimos paquetes para continuidad
            self.packet_buffer = self.packet_buffer[-10:]  # Mantener 10 para solapamiento
            return result
        
        return None
    
    def analyze_with_model(self) -> Optional[Dict[str, Any]]:
        """Analiza el buffer de paquetes con el modelo de IA"""
        if self.model is None:
            self.logger.warning("⚠️ Modelo no cargado")
            return None
        
        try:
            # Convertir buffer a secuencia para el modelo
            sequence = self.create_sequence()
            
            # Hacer predicción
            prediction = self.model.predict(sequence, verbose=0)
            
            # Interpretar resultado
            malware_prob: float = float(prediction[0][1])
            benign_prob: float = float(prediction[0][0])
            
            result: Dict[str, Any] = {
                'timestamp': time.time(),
                'malware_probability': malware_prob,
                'benign_probability': benign_prob,
                'is_malware': malware_prob > 0.9,
                'confidence': max(malware_prob, benign_prob)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error en análisis con modelo: {e}")
            return None
    
    def create_sequence(self) -> np.ndarray:
        """Crea secuencia para el modelo a partir del buffer"""
        sequence_matrix: list[np.ndarray] = []
        
        for payload in self.packet_buffer:
            # Convertir bytes a matriz 32x32
            matrix: np.ndarray = np.frombuffer(payload, dtype=np.uint8).reshape(32, 32)
            # Normalizar a [0, 1]
            matrix = matrix.astype(np.float32) / 255.0
            sequence_matrix.append(matrix)
        
        # Reshape para el modelo: (1, 20, 32, 32, 1)
        sequence_array: np.ndarray = np.array(sequence_matrix).reshape(1, self.buffer_size, 32, 32, 1)
        return sequence_array
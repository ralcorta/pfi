# app/sensor/src/core/inference_engine.py
"""
Motor de inferencia para análisis de malware en tiempo real
"""

import asyncio
import time
import numpy as np
import tensorflow as tf
from typing import List, Dict, Any
import logging

class InferenceEngine:
    """Motor de inferencia para detección de malware"""
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5, logger=None):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.logger = logger or logging.getLogger(__name__)
        
        self.model = None
        self.stats = {
            'inferences': 0,
            'avg_inference_time': 0.0,
            'malware_detections': 0
        }
    
    async def load_model(self):
        """Carga el modelo de ML"""
        self.logger.info(f"🤖 Cargando modelo: {self.model_path}")
        
        try:
            # Cargar modelo en hilo separado para no bloquear
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                tf.keras.models.load_model, 
                self.model_path
            )
            
            self.logger.info("✅ Modelo cargado exitosamente")
            self.logger.info(f"📊 Arquitectura: {self.model.input_shape} -> {self.model.output_shape}")
            
        except Exception as e:
            self.logger.error(f"❌ Error cargando modelo: {e}")
            raise
    
    async def analyze_sequences(self, sequences: np.ndarray) -> List[Dict[str, Any]]:
        """Analiza secuencias de paquetes"""
        if self.model is None:
            raise RuntimeError("Modelo no cargado")
        
        start_time = time.time()
        
        try:
            # Ejecutar inferencia en hilo separado
            loop = asyncio.get_event_loop()
            predictions = await loop.run_in_executor(
                None,
                self.model.predict,
                sequences,
                {'verbose': 0}
            )
            
            inference_time = time.time() - start_time
            
            # Procesar resultados
            results = []
            for i, pred in enumerate(predictions):
                malware_prob = float(pred[1])
                benign_prob = float(pred[0])
                is_malware = malware_prob > self.confidence_threshold
                
                result = {
                    'sequence_id': i,
                    'timestamp': time.time(),
                    'malware_probability': malware_prob,
                    'benign_probability': benign_prob,
                    'confidence': max(malware_prob, benign_prob),
                    'is_malware': is_malware,
                    'sequence_count': len(sequences)
                }
                
                results.append(result)
            
            # Actualizar estadísticas
            self._update_stats(inference_time, results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error en inferencia: {e}")
            raise
    
    def _update_stats(self, inference_time: float, results: List[Dict]):
        """Actualiza estadísticas del motor"""
        self.stats['inferences'] += 1
        
        # Actualizar tiempo promedio de inferencia
        total_time = self.stats['avg_inference_time'] * (self.stats['inferences'] - 1)
        self.stats['avg_inference_time'] = (total_time + inference_time) / self.stats['inferences']
        
        # Contar detecciones de malware
        malware_count = sum(1 for r in results if r['is_malware'])
        self.stats['malware_detections'] += malware_count
        
        # Log cada 100 inferencias
        if self.stats['inferences'] % 100 == 0:
            self.logger.info(
                f"🤖 Stats - Inferencias: {self.stats['inferences']}, "
                f"Tiempo promedio: {self.stats['avg_inference_time']:.3f}s, "
                f"Detecciones malware: {self.stats['malware_detections']}"
            )
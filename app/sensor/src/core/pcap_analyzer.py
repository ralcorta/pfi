# app/sensor/src/core/pcap_analyzer.py
"""
Analizador de archivos .pcap para modo demo
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from scapy.all import rdpcap, TCP, UDP, Raw
import logging

class PCAPAnalyzer:
    """Analizador de archivos .pcap para demostración"""
    
    def __init__(self, packet_processor, inference_engine, logger=None):
        self.packet_processor = packet_processor
        self.inference_engine = inference_engine
        self.logger = logger or logging.getLogger(__name__)
    
    async def analyze_pcap_file(self, pcap_path: str) -> List[Dict[str, Any]]:
        """Analiza un archivo .pcap completo"""
        self.logger.info(f"📦 Analizando archivo: {Path(pcap_path).name}")
        
        try:
            # Cargar archivo .pcap
            packets = rdpcap(pcap_path)
            self.logger.info(f"   📊 Total de paquetes: {len(packets)}")
            
            # Extraer payloads
            payloads = self._extract_payloads_from_packets(packets)
            self.logger.info(f"   ✅ Payloads extraídos: {len(payloads)}")
            
            if not payloads:
                self.logger.warning("   ⚠️ No se encontraron payloads válidos")
                return []
            
            # Convertir a secuencias
            sequences = self.packet_processor.payloads_to_sequences(payloads, max_sequences=50)
            self.logger.info(f"   🔄 Secuencias generadas: {len(sequences)}")
            
            if len(sequences) == 0:
                self.logger.warning("   ⚠️ No se pudieron generar secuencias")
                return []
            
            # Analizar con el modelo
            results = await self.inference_engine.analyze_sequences(sequences)
            
            # Enriquecer resultados con información del archivo
            enriched_results = []
            for result in results:
                enriched_result = {
                    **result,
                    'file_name': Path(pcap_path).name,
                    'total_packets': len(packets),
                    'total_payloads': len(payloads),
                    'total_sequences': len(sequences)
                }
                enriched_results.append(enriched_result)
            
            # Mostrar resumen
            malware_count = sum(1 for r in enriched_results if r['is_malware'])
            self.logger.info(f"   🦠 Detecciones de malware: {malware_count}/{len(enriched_results)}")
            
            return enriched_results
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando archivo {pcap_path}: {e}")
            return []
    
    def _extract_payloads_from_packets(self, packets) -> List[bytes]:
        """Extrae payloads de una lista de paquetes"""
        payloads = []
        
        for pkt in packets:
            if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
                try:
                    payload = bytes(pkt[Raw].load)
                    
                    # Completar con 0s si es muy corto
                    if len(payload) < 100:
                        payload = payload + bytes([0] * (100 - len(payload)))
                    
                    # Truncar o rellenar a tamaño estándar
                    if len(payload) > 1024:
                        payload = payload[:1024]
                    else:
                        payload = payload + bytes([0] * (1024 - len(payload)))
                    
                    payloads.append(payload)
                    
                except Exception as e:
                    continue
        
        return payloads
#!/usr/bin/env python3
"""
Servidor HTTP con FastAPI para health check y consultas DynamoDB
"""
import logging
import time
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from app.sensor.src.utils.dynamo_client import DynamoClient
from app.sensor.src.utils.config import Config
from app.sensor.src.docs_setup import setup_docs_endpoints, enhance_openapi_schema

class HTTPServer:
    """Servidor HTTP con FastAPI"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = FastAPI(
            title="Sensor de Tráfico API",
            description="API para health check y consultas de detecciones de malware",
            version="1.0.0"
        )
        self.dynamo_table = DynamoClient("demo-pcap-control")
        self.config = Config()
        self.start_time = time.time()
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Configurar rutas
        self._setup_routes()
        
        # Configurar documentación web automática
        enhance_openapi_schema(self.app)
        setup_docs_endpoints(self.app)
    
    def _setup_routes(self):
        """Configura las rutas de la API"""
        
        @self.app.get("/")
        async def root():
            """Endpoint raíz"""
            return {
                "message": "Sensor de Tráfico API",
                "version": "1.0.0",
                "status": "running"
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                # Verificar conexión a DynamoDB
                dynamo_status = "healthy"
                try:
                    # Intentar leer un item de DynamoDB
                    self.dynamo_table.get({"id": "health_check"})
                except Exception as e:
                    dynamo_status = f"unhealthy: {str(e)}"
                
                uptime = time.time() - self.start_time
                
                return {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "uptime_seconds": uptime,
                    "dynamodb": dynamo_status,
                    "environment": self.config.ENVIRONMENT
                }
            except Exception as e:
                self.logger.error(f"Error en health check: {e}")
                raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
        
        @self.app.get("/detections")
        async def get_detections(limit: int = 100):
            """Obtener todas las detecciones de malware"""
            try:
                detections = self._get_malware_detections(limit)
                return {
                    "detections": detections,
                    "count": len(detections),
                    "timestamp": time.time()
                }
            except Exception as e:
                self.logger.error(f"Error obteniendo detecciones: {e}")
                raise HTTPException(status_code=500, detail=f"Error obteniendo detecciones: {str(e)}")
        
        @self.app.get("/detections/{malware_id}")
        async def get_detection(malware_id: str):
            """Obtener una detección específica por ID"""
            try:
                detection = self.dynamo_table.get({"id": malware_id})
                if not detection:
                    raise HTTPException(status_code=404, detail="Detección no encontrada")
                
                return {
                    "detection": detection,
                    "timestamp": time.time()
                }
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error obteniendo detección {malware_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Error obteniendo detección: {str(e)}")
        
        @self.app.get("/stats")
        async def get_stats():
            """Obtener estadísticas de detecciones"""
            try:
                detections = self._get_malware_detections()
                
                # Calcular estadísticas
                total_detections = len(detections)
                unique_ips = len(set(d.get('source_ip', '') for d in detections))
                
                # Agrupar por IP
                ip_stats = {}
                for detection in detections:
                    ip = detection.get('source_ip', 'unknown')
                    if ip not in ip_stats:
                        ip_stats[ip] = {
                            'ip': ip,
                            'detection_count': 0,
                            'packet_count': 0,
                            'first_seen': detection.get('first_seen', 0),
                            'last_seen': detection.get('last_seen', 0)
                        }
                    ip_stats[ip]['detection_count'] += 1
                    ip_stats[ip]['packet_count'] += detection.get('packet_count', 0)
                    ip_stats[ip]['last_seen'] = max(ip_stats[ip]['last_seen'], detection.get('last_seen', 0))
                
                return {
                    "total_detections": total_detections,
                    "unique_ips": unique_ips,
                    "ip_statistics": list(ip_stats.values()),
                    "timestamp": time.time()
                }
            except Exception as e:
                self.logger.error(f"Error obteniendo estadísticas: {e}")
                raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
        
        @self.app.get("/demo/status")
        async def get_demo_status():
            """Obtener estado del modo demo"""
            try:
                demo_config = self.dynamo_table.get({"id": "demo_control"})
                return {
                    "demo_status": demo_config or {"execute_demo": "false"},
                    "timestamp": time.time()
                }
            except Exception as e:
                self.logger.error(f"Error obteniendo estado demo: {e}")
                raise HTTPException(status_code=500, detail=f"Error obteniendo estado demo: {str(e)}")
        
        @self.app.get("/debug/files")
        async def list_files():
            """Listar archivos en el directorio de modelos para debugging"""
            import os
            try:
                models_dir = "/app/models"
                if os.path.exists(models_dir):
                    files = []
                    for root, dirs, filenames in os.walk(models_dir):
                        for filename in filenames:
                            filepath = os.path.join(root, filename)
                            files.append({
                                "path": filepath,
                                "size": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                                "exists": os.path.exists(filepath)
                            })
                    return {"files": files, "models_dir": models_dir}
                else:
                    return {"error": f"Directorio {models_dir} no existe"}
            except Exception as e:
                return {"error": str(e)}

        @self.app.get("/demo/start")
        async def start_demo():
            """Iniciar modo demo con archivo PCAP (Zeus.pcap - 13MB)"""
            pcap_file = '/app/models/data/small/Malware/Zeus.pcap'
            try:
                demo_config = {
                    'id': 'demo_control',
                    'execute_demo': 'true',
                    'pcap_file': pcap_file,
                    'started_at': int(time.time()),
                    'description': f'Demo simulado iniciado: {pcap_file}'
                }
                
                success = self.dynamo_table.save(demo_config)
                
                if success:
                    self.logger.info(f"🎭 Demo simulado iniciado: {pcap_file}")
                    return {
                        "status": "success",
                        "message": f"Demo simulado iniciado: {pcap_file}",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
                else:
                    self.logger.error("❌ Error al iniciar demo")
                    raise HTTPException(status_code=500, detail="Error al iniciar demo")
                    
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"❌ Error iniciando demo: {error_msg}")
                
                # Proporcionar información más específica sobre el error
                if "UnrecognizedClientException" in error_msg:
                    return {
                        "status": "error",
                        "message": "Error de credenciales AWS - El contenedor no puede acceder a DynamoDB",
                        "error_type": "AWS_CREDENTIALS_ERROR",
                        "suggestion": "Verificar permisos IAM del task role para DynamoDB",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
                elif "AccessDenied" in error_msg:
                    return {
                        "status": "error", 
                        "message": "Acceso denegado a DynamoDB",
                        "error_type": "ACCESS_DENIED",
                        "suggestion": "Verificar permisos IAM del task role",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Error iniciando demo: {error_msg}",
                        "error_type": "UNKNOWN_ERROR",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
        
        @self.app.post("/demo/stop")
        async def stop_demo():
            """Detener modo demo"""
            try:
                demo_config = {
                    'id': 'demo_control',
                    'execute_demo': 'false',
                    'pcap_file': '',
                    'stopped_at': int(time.time()),
                    'description': 'Demo detenida - volviendo a captura en vivo'
                }
                
                success = self.dynamo_table.save(demo_config)
                
                if success:
                    self.logger.info("🛡️ Demo detenida - volviendo a captura en vivo")
                    return {
                        "status": "success",
                        "message": "Demo detenida - volviendo a captura en vivo",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
                else:
                    self.logger.error("❌ Error al detener demo")
                    raise HTTPException(status_code=500, detail="Error al detener demo")
                    
            except Exception as e:
                self.logger.error(f"❌ Error deteniendo demo: {e}")
                raise HTTPException(status_code=500, detail=f"Error deteniendo demo: {str(e)}")

        @self.app.get("/demo/start-fast")
        async def start_fast_demo():
            """Iniciar modo demo rápido con archivo PCAP más pequeño (Miuref.pcap - ~1MB)"""
            pcap_file = '/app/models/data/small/Malware/Zeus.pcap'
            try:
                demo_config = {
                    'id': 'demo_control',
                    'execute_demo': 'true',
                    'pcap_file': pcap_file,
                    'started_at': int(time.time()),
                    'description': f'Demo rápido iniciado: {pcap_file}'
                }
                
                success = self.dynamo_table.save(demo_config)
                
                if success:
                    self.logger.info(f"🚀 Demo rápido iniciado: {pcap_file}")
                    return {
                        "status": "success",
                        "message": f"Demo rápido iniciado: {pcap_file}",
                        "demo_config": demo_config,
                        "timestamp": time.time()
                    }
                else:
                    self.logger.error("❌ Error al iniciar demo rápido")
                    raise HTTPException(status_code=500, detail="Error al iniciar demo rápido")
                    
            except Exception as e:
                self.logger.error(f"❌ Error iniciando demo rápido: {e}")
                raise HTTPException(status_code=500, detail="Error al iniciar demo rápido")
        
        @self.app.post("/demo/toggle")
        async def toggle_demo(pcap_file: str = "models/data/small/Malware/Zeus.pcap"):
            """Alternar entre modo demo y captura en vivo"""
            try:
                # Obtener estado actual
                current_config = self.dynamo_table.get({"id": "demo_control"})
                current_demo_status = current_config.get('execute_demo', 'false') if current_config else 'false'
                
                if current_demo_status == 'true':
                    # Si está en demo, detenerlo
                    return await stop_demo()
                else:
                    # Si no está en demo, iniciarlo
                    return await start_demo(pcap_file)
                    
            except Exception as e:
                self.logger.error(f"❌ Error alternando demo: {e}")
                raise HTTPException(status_code=500, detail=f"Error alternando demo: {str(e)}")
    
    def _get_malware_detections(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener detecciones de malware de DynamoDB"""
        try:
            response = self.dynamo_table.table.scan(
                FilterExpression='begins_with(id, :prefix)',
                ExpressionAttributeValues={':prefix': 'malware_'},
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            self.logger.error(f"Error obteniendo malware: {e}")
            return []
    
    def start_server(self):
        """Inicia el servidor HTTP"""
        try:
            self.logger.info(f"🌐 Iniciando servidor HTTP en puerto {self.port}")
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info"
            )
        except Exception as e:
            self.logger.error(f"❌ Error iniciando servidor HTTP: {e}")
            raise

def main():
    """Función principal para ejecutar el servidor HTTP"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Servidor HTTP para Sensor de Tráfico')
    parser.add_argument('--port', type=int, default=8080, help='Puerto HTTP')
    
    args = parser.parse_args()
    
    server = HTTPServer(args.port)
    server.start_server()

if __name__ == "__main__":
    main()

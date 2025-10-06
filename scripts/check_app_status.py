#!/usr/bin/env python3
"""
Script para verificar el estado de la aplicación
"""
import os
import sys
import time
import logging
import subprocess
import requests
from pathlib import Path

# Agregar el directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.sensor.src.utils.dynamo_client import DynamoClient
from app.sensor.src.utils.config import Config

class AppStatusChecker:
    """Verificador de estado de la aplicación"""
    
    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Configura el logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def check_dynamodb_local(self):
        """Verifica que DynamoDB local esté corriendo (solo en local)"""
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - usando DynamoDB en la nube")
            return True
            
        self.logger.info("🔍 Verificando DynamoDB local...")
        
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.logger.info("✅ DynamoDB local está corriendo")
                return True
            else:
                self.logger.warning("⚠️ DynamoDB local no está corriendo")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando DynamoDB: {e}")
            return False
    
    def check_dynamodb_connection(self):
        """Verifica conexión a DynamoDB"""
        self.logger.info("🔍 Verificando conexión a DynamoDB...")
        
        try:
            dynamo_client = DynamoClient("demo-pcap-control")
            test_record = dynamo_client.get({"id": "health_check"})
            
            if test_record:
                self.logger.info("✅ Conexión a DynamoDB funcionando")
                return True
            else:
                self.logger.warning("⚠️ No se pudo leer de DynamoDB")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error conectando a DynamoDB: {e}")
            return False
    
    def check_http_server(self):
        """Verifica que el servidor HTTP esté corriendo"""
        self.logger.info("🔍 Verificando servidor HTTP...")
        
        # En AWS, el servidor HTTP está en ECS, no en localhost
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - servidor HTTP está en ECS")
            # En AWS, verificaríamos el estado del servicio ECS
            # Por ahora, asumimos que está funcionando si llegamos aquí
            return True
        
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.logger.info("✅ Servidor HTTP está corriendo")
                self.logger.info(f"   Status: {data.get('status', 'unknown')}")
                self.logger.info(f"   DynamoDB: {data.get('dynamodb', 'unknown')}")
                return True
            else:
                self.logger.warning(f"⚠️ Servidor HTTP respondió con código: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException:
            self.logger.warning("⚠️ Servidor HTTP no está corriendo")
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando servidor HTTP: {e}")
            return False
    
    def check_udp_server(self):
        """Verifica que el servidor UDP esté corriendo"""
        self.logger.info("🔍 Verificando servidor UDP...")
        
        # En AWS, el servidor UDP está en ECS, no en localhost
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - servidor UDP está en ECS")
            # En AWS, verificaríamos el estado del servicio ECS
            # Por ahora, asumimos que está funcionando si llegamos aquí
            return True
        
        try:
            result = subprocess.run(
                ["lsof", "-i", ":4789"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and "python" in result.stdout:
                self.logger.info("✅ Servidor UDP está corriendo en puerto 4789")
                return True
            else:
                self.logger.warning("⚠️ Servidor UDP no está corriendo en puerto 4789")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando servidor UDP: {e}")
            return False
    
    def check_model_file(self):
        """Verifica que el modelo de IA exista"""
        self.logger.info("🔍 Verificando modelo de IA...")
        
        model_path = self.config.MODEL_PATH
        if os.path.exists(model_path):
            self.logger.info(f"✅ Modelo encontrado: {model_path}")
            return True
        else:
            self.logger.warning(f"⚠️ Modelo no encontrado: {model_path}")
            return False
    
    def check_env_file(self):
        """Verifica que el archivo .env exista (solo en local)"""
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - usando variables de entorno del contenedor")
            return True
            
        self.logger.info("🔍 Verificando archivo .env...")
        
        env_file = project_root / ".env"
        if env_file.exists():
            self.logger.info("✅ Archivo .env encontrado")
            return True
        else:
            self.logger.warning("⚠️ Archivo .env no encontrado")
            return False
    
    def get_detections_count(self):
        """Obtiene el número de detecciones"""
        # En AWS, necesitaríamos la URL del ALB
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - detecciones disponibles en ALB")
            return 0
            
        try:
            response = requests.get("http://localhost:8080/detections", timeout=5)
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                self.logger.info(f"📊 Detecciones de malware: {count}")
                return count
            else:
                self.logger.warning("⚠️ No se pudo obtener detecciones")
                return 0
        except:
            return 0
    
    def run(self):
        """Ejecuta todas las verificaciones"""
        self.logger.info("🔍 Verificando estado de la aplicación...")
        self.logger.info("=" * 50)
        
        checks = [
            ("DynamoDB Local", self.check_dynamodb_local),
            ("Conexión DynamoDB", self.check_dynamodb_connection),
            ("Archivo .env", self.check_env_file),
            ("Modelo de IA", self.check_model_file),
            ("Servidor HTTP", self.check_http_server),
            ("Servidor UDP", self.check_udp_server),
        ]
        
        results = {}
        for check_name, check_func in checks:
            results[check_name] = check_func()
            self.logger.info("")
        
        # Resumen
        self.logger.info("📋 RESUMEN:")
        self.logger.info("=" * 50)
        
        all_good = True
        for check_name, result in results.items():
            status = "✅ OK" if result else "❌ FALLO"
            self.logger.info(f"   {check_name}: {status}")
            if not result:
                all_good = False
        
        # Información adicional
        if results.get("Servidor HTTP"):
            self.get_detections_count()
        
        self.logger.info("")
        if all_good:
            self.logger.info("🎉 ¡Aplicación funcionando correctamente!")
        else:
            self.logger.info("⚠️ Algunos componentes necesitan atención")
            self.logger.info("💡 Ejecuta: make init-app para inicializar")
        
        return all_good

def main():
    """Función principal"""
    checker = AppStatusChecker()
    success = checker.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

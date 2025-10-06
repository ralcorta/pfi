#!/usr/bin/env python3
"""
Script de inicialización completa de la aplicación
Configura DynamoDB y prepara todo lo necesario para que funcione
"""
import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Agregar el directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.sensor.src.utils.dynamo_client import DynamoClient
from app.sensor.src.utils.config import Config

class AppInitializer:
    """Inicializador completo de la aplicación"""
    
    def __init__(self):
        self.config = Config()
        self.logger = self._setup_logging()
        self.dynamo_client = None
        
    def _setup_logging(self):
        """Configura el logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def check_dependencies(self):
        """Verifica que las dependencias estén instaladas"""
        self.logger.info("🔍 Verificando dependencias...")
        
        try:
            import fastapi
            import uvicorn
            import boto3
            import tensorflow
            import scapy
            self.logger.info("✅ Todas las dependencias están instaladas")
            return True
        except ImportError as e:
            self.logger.error(f"❌ Dependencia faltante: {e}")
            self.logger.info("💡 Ejecuta: poetry install")
            return False
    
    def start_dynamodb_local(self):
        """Inicia DynamoDB local (solo en entorno local)"""
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS detectado - usando DynamoDB en la nube")
            return True
            
        self.logger.info("🚀 Iniciando DynamoDB local...")
        
        try:
            # Verificar si DynamoDB ya está corriendo
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8000"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.logger.info("✅ DynamoDB local ya está corriendo")
                return True
            
            # Iniciar DynamoDB con docker-compose
            result = subprocess.run(
                ["docker-compose", "up", "-d", "dynamodb-local"],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("✅ DynamoDB local iniciado")
                # Esperar a que esté listo
                time.sleep(3)
                return True
            else:
                self.logger.error(f"❌ Error iniciando DynamoDB: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error verificando DynamoDB: {e}")
            return False
    
    def init_dynamodb_tables(self):
        """Inicializa las tablas de DynamoDB"""
        if self.config.ENVIRONMENT != "local":
            self.logger.info("🌐 Entorno AWS - las tablas ya están creadas por Terraform")
            return True
            
        self.logger.info("📊 Inicializando tablas de DynamoDB...")
        
        try:
            # Ejecutar script de inicialización
            result = subprocess.run(
                ["poetry", "run", "python", "scripts/init_local_dynamo.py"],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Tablas de DynamoDB inicializadas")
                return True
            else:
                self.logger.error(f"❌ Error inicializando tablas: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando script de inicialización: {e}")
            return False
    
    def setup_base_records(self):
        """Configura registros base en DynamoDB"""
        self.logger.info("📝 Configurando registros base...")
        
        try:
            # Usar el nombre de tabla correcto según el entorno
            table_name = "demo-pcap-control"
            if self.config.ENVIRONMENT != "local":
                # En AWS, la tabla se llama igual pero puede tener prefijo
                table_name = "demo-pcap-control"
            
            self.dynamo_client = DynamoClient(table_name)
            
            # Configurar modo demo por defecto
            demo_config = {
                "id": "demo_control",
                "execute_demo": "false",
                "pcap_file": "models/data/small/Malware/Zeus.pcap",
                "created_at": int(time.time()),
                "description": "Configuración del modo demo",
                "environment": self.config.ENVIRONMENT
            }
            
            self.dynamo_client.save(demo_config)
            self.logger.info("✅ Configuración de demo establecida")
            
            # Crear registro de health check
            health_check = {
                "id": "health_check",
                "status": "healthy",
                "last_check": int(time.time()),
                "description": "Registro para health check",
                "environment": self.config.ENVIRONMENT
            }
            
            self.dynamo_client.save(health_check)
            self.logger.info("✅ Registro de health check creado")
            
            # Crear configuración de la aplicación
            app_config = {
                "id": "app_config",
                "version": "1.0.0",
                "environment": self.config.ENVIRONMENT,
                "model_path": self.config.MODEL_PATH,
                "created_at": int(time.time()),
                "description": "Configuración de la aplicación",
                "aws_region": self.config.AWS_REGION,
                "sagemaker_endpoint": self.config.SAGEMAKER_ENDPOINT
            }
            
            self.dynamo_client.save(app_config)
            self.logger.info("✅ Configuración de aplicación guardada")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error configurando registros base: {e}")
            return False
    
    def verify_model_exists(self):
        """Verifica que el modelo de IA exista"""
        self.logger.info("🤖 Verificando modelo de IA...")
        
        model_path = self.config.MODEL_PATH
        if not os.path.exists(model_path):
            self.logger.warning(f"⚠️ Modelo no encontrado en: {model_path}")
            self.logger.info("💡 Asegúrate de que el modelo esté en la ruta correcta")
            return False
        
        self.logger.info("✅ Modelo de IA encontrado")
        return True
    
    def test_application(self):
        """Prueba que la aplicación funcione correctamente"""
        self.logger.info("🧪 Probando aplicación...")
        
        try:
            # Probar conexión a DynamoDB
            test_record = self.dynamo_client.get({"id": "health_check"})
            if test_record:
                self.logger.info("✅ Conexión a DynamoDB funcionando")
            else:
                self.logger.warning("⚠️ No se pudo leer de DynamoDB")
            
            # Probar importación de módulos principales
            from app.sensor.src.hybrid_server import HybridServer
            from app.sensor.src.http_server import HTTPServer
            self.logger.info("✅ Módulos principales importados correctamente")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error probando aplicación: {e}")
            return False
    
    def show_next_steps(self):
        """Muestra los próximos pasos para el usuario"""
        self.logger.info("🎉 ¡Inicialización completada!")
        self.logger.info("")
        
        if self.config.ENVIRONMENT == "local":
            self.logger.info("📋 Próximos pasos (LOCAL):")
            self.logger.info("   1. Ejecutar servidor híbrido:")
            self.logger.info("      make run-hybrid-server-local")
            self.logger.info("")
            self.logger.info("   2. Probar API HTTP:")
            self.logger.info("      make test-api")
            self.logger.info("")
            self.logger.info("   3. Probar servidor UDP:")
            self.logger.info("      make test-udp-server")
            self.logger.info("")
            self.logger.info("   4. Habilitar modo demo:")
            self.logger.info("      make demo-on")
            self.logger.info("")
            self.logger.info("🌐 Endpoints disponibles:")
            self.logger.info("   - http://localhost:8080/health")
            self.logger.info("   - http://localhost:8080/detections")
            self.logger.info("   - http://localhost:8080/stats")
            self.logger.info("   - http://localhost:8080/demo/status")
        else:
            self.logger.info("📋 Próximos pasos (AWS):")
            self.logger.info("   1. La aplicación está desplegada en ECS")
            self.logger.info("   2. Verificar logs en CloudWatch:")
            self.logger.info("      aws logs tail /aws/ecs/net-mirror-sensor --follow")
            self.logger.info("")
            self.logger.info("   3. Probar API HTTP (usar ALB DNS):")
            self.logger.info("      curl http://<ALB-DNS>/health")
            self.logger.info("")
            self.logger.info("   4. Verificar estado del servicio:")
            self.logger.info("      aws ecs describe-services --cluster mirror-cluster --services mirror-sensor")
            self.logger.info("")
            self.logger.info("🌐 Endpoints disponibles (usar ALB DNS):")
            self.logger.info("   - http://<ALB-DNS>/health")
            self.logger.info("   - http://<ALB-DNS>/detections")
            self.logger.info("   - http://<ALB-DNS>/stats")
            self.logger.info("   - http://<ALB-DNS>/demo/status")
    
    def run(self):
        """Ejecuta la inicialización completa"""
        self.logger.info("🚀 Iniciando configuración completa de la aplicación...")
        self.logger.info("=" * 60)
        
        steps = [
            ("Verificando dependencias", self.check_dependencies),
            ("Iniciando DynamoDB local", self.start_dynamodb_local),
            ("Inicializando tablas DynamoDB", self.init_dynamodb_tables),
            ("Configurando registros base", self.setup_base_records),
            ("Verificando modelo de IA", self.verify_model_exists),
            ("Probando aplicación", self.test_application),
        ]
        
        for step_name, step_func in steps:
            self.logger.info(f"📋 {step_name}...")
            if not step_func():
                self.logger.error(f"❌ Falló: {step_name}")
                self.logger.info("💡 Revisa los errores anteriores y vuelve a intentar")
                return False
            self.logger.info("")
        
        self.show_next_steps()
        return True

def main():
    """Función principal"""
    initializer = AppInitializer()
    success = initializer.run()
    
    if success:
        print("\n✅ ¡Aplicación lista para usar!")
        sys.exit(0)
    else:
        print("\n❌ Inicialización falló. Revisa los errores anteriores.")
        sys.exit(1)

if __name__ == "__main__":
    main()

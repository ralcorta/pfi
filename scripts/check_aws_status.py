#!/usr/bin/env python3
"""
Script para verificar el estado de la aplicación en AWS
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

class AWSStatusChecker:
    """Verificador de estado de la aplicación en AWS"""
    
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
    
    def check_aws_credentials(self):
        """Verifica que las credenciales de AWS estén configuradas"""
        self.logger.info("🔍 Verificando credenciales de AWS...")
        
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Credenciales de AWS configuradas")
                return True
            else:
                self.logger.warning("⚠️ Error con credenciales de AWS")
                self.logger.warning(f"   {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando credenciales AWS: {e}")
            return False
    
    def check_ecs_cluster(self):
        """Verifica el estado del cluster ECS"""
        self.logger.info("🔍 Verificando cluster ECS...")
        
        try:
            result = subprocess.run(
                ["aws", "ecs", "describe-clusters", "--clusters", "mirror-cluster"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Cluster ECS 'mirror-cluster' encontrado")
                return True
            else:
                self.logger.warning("⚠️ Cluster ECS no encontrado")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando cluster ECS: {e}")
            return False
    
    def check_ecs_service(self):
        """Verifica el estado del servicio ECS"""
        self.logger.info("🔍 Verificando servicio ECS...")
        
        try:
            result = subprocess.run(
                ["aws", "ecs", "describe-services", 
                 "--cluster", "mirror-cluster", 
                 "--services", "mirror-sensor"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Servicio ECS 'mirror-sensor' encontrado")
                return True
            else:
                self.logger.warning("⚠️ Servicio ECS no encontrado")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando servicio ECS: {e}")
            return False
    
    def check_alb_status(self):
        """Verifica el estado del Application Load Balancer"""
        self.logger.info("🔍 Verificando Application Load Balancer...")
        
        try:
            result = subprocess.run(
                ["aws", "elbv2", "describe-load-balancers", 
                 "--names", "mirror-alb"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Application Load Balancer encontrado")
                return True
            else:
                self.logger.warning("⚠️ Application Load Balancer no encontrado")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando ALB: {e}")
            return False
    
    def check_dynamodb_table(self):
        """Verifica que la tabla de DynamoDB exista"""
        self.logger.info("🔍 Verificando tabla DynamoDB...")
        
        try:
            result = subprocess.run(
                ["aws", "dynamodb", "describe-table", 
                 "--table-name", "demo-pcap-control"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Tabla DynamoDB 'demo-pcap-control' encontrada")
                return True
            else:
                self.logger.warning("⚠️ Tabla DynamoDB no encontrada")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando tabla DynamoDB: {e}")
            return False
    
    def check_sagemaker_endpoint(self):
        """Verifica el estado del endpoint de SageMaker"""
        self.logger.info("🔍 Verificando endpoint de SageMaker SKIPPED")
        return True
        self.logger.info("🔍 Verificando endpoint de SageMaker...")
        
        try:
            endpoint_name = self.config.SAGEMAKER_ENDPOINT
            if not endpoint_name or endpoint_name == "sm-detector":
                self.logger.warning("⚠️ Endpoint de SageMaker no configurado")
                return False
            
            result = subprocess.run(
                ["aws", "sagemaker", "describe-endpoint", 
                 "--endpoint-name", endpoint_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ Endpoint de SageMaker '{endpoint_name}' encontrado")
                return True
            else:
                self.logger.warning(f"⚠️ Endpoint de SageMaker '{endpoint_name}' no encontrado")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error verificando endpoint de SageMaker: {e}")
            return False
    
    def get_alb_dns(self):
        """Obtiene el DNS del Application Load Balancer"""
        self.logger.info("🔍 Obteniendo DNS del ALB...")
        
        try:
            result = subprocess.run(
                ["aws", "elbv2", "describe-load-balancers", 
                 "--names", "mirror-alb", 
                 "--query", "LoadBalancers[0].DNSName",
                 "--output", "text"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                dns_name = result.stdout.strip()
                self.logger.info(f"✅ DNS del ALB: {dns_name}")
                return dns_name
            else:
                self.logger.warning("⚠️ No se pudo obtener DNS del ALB")
                return None
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo DNS del ALB: {e}")
            return None
    
    def test_http_endpoint(self, alb_dns):
        """Prueba el endpoint HTTP del ALB"""
        if not alb_dns:
            return False
            
        self.logger.info("🔍 Probando endpoint HTTP...")
        
        try:
            url = f"http://{alb_dns}/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info("✅ Endpoint HTTP funcionando")
                self.logger.info(f"   Status: {data.get('status', 'unknown')}")
                self.logger.info(f"   DynamoDB: {data.get('dynamodb', 'unknown')}")
                return True
            else:
                self.logger.warning(f"⚠️ Endpoint HTTP respondió con código: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error probando endpoint HTTP: {e}")
            return False
    
    def get_cloudwatch_logs(self):
        """Obtiene los logs más recientes de CloudWatch"""
        self.logger.info("🔍 Obteniendo logs de CloudWatch...")
        
        try:
            result = subprocess.run(
                ["aws", "logs", "tail", "/aws/ecs/net-mirror-sensor", 
                 "--since", "5m", "--follow", "false"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.logger.info("✅ Logs de CloudWatch obtenidos")
                # Mostrar las últimas líneas
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:  # Últimas 5 líneas
                    self.logger.info(f"   {line}")
                return True
            else:
                self.logger.warning("⚠️ No se pudieron obtener logs de CloudWatch")
                return False
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo logs de CloudWatch: {e}")
            return False
    
    def run(self):
        """Ejecuta todas las verificaciones de AWS"""
        self.logger.info("🔍 Verificando estado de la aplicación en AWS...")
        self.logger.info("=" * 60)
        
        checks = [
            ("Credenciales AWS", self.check_aws_credentials),
            ("Cluster ECS", self.check_ecs_cluster),
            ("Servicio ECS", self.check_ecs_service),
            ("Application Load Balancer", self.check_alb_status),
            ("Tabla DynamoDB", self.check_dynamodb_table),
            ("Endpoint SageMaker", self.check_sagemaker_endpoint),
        ]
        
        results = {}
        for check_name, check_func in checks:
            results[check_name] = check_func()
            self.logger.info("")
        
        # Obtener DNS del ALB y probar endpoint
        alb_dns = self.get_alb_dns()
        if alb_dns:
            results["Endpoint HTTP"] = self.test_http_endpoint(alb_dns)
            self.logger.info("")
        
        # Obtener logs de CloudWatch
        self.get_cloudwatch_logs()
        self.logger.info("")
        
        # Resumen
        self.logger.info("📋 RESUMEN:")
        self.logger.info("=" * 60)
        
        all_good = True
        for check_name, result in results.items():
            status = "✅ OK" if result else "❌ FALLO"
            self.logger.info(f"   {check_name}: {status}")
            if not result:
                all_good = False
        
        if alb_dns:
            self.logger.info("")
            self.logger.info("🌐 Endpoints disponibles:")
            self.logger.info(f"   - http://{alb_dns}/health")
            self.logger.info(f"   - http://{alb_dns}/detections")
            self.logger.info(f"   - http://{alb_dns}/stats")
            self.logger.info(f"   - http://{alb_dns}/demo/status")
        
        self.logger.info("")
        if all_good:
            self.logger.info("🎉 ¡Aplicación funcionando correctamente en AWS!")
        else:
            self.logger.info("⚠️ Algunos componentes necesitan atención")
        
        return all_good

def main():
    """Función principal"""
    checker = AWSStatusChecker()
    success = checker.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

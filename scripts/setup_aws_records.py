#!/usr/bin/env python3
"""
Script simple para configurar registros base en DynamoDB de AWS
"""
import os
import sys
import time
import logging
import boto3
from pathlib import Path

# Agregar el directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_logging():
    """Configura el logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def setup_base_records():
    """Configura registros base en DynamoDB de AWS"""
    logger = setup_logging()
    logger.info("🚀 Configurando registros base en DynamoDB de AWS...")
    
    try:
        # Crear cliente de DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('demo-pcap-control')
        
        # Configurar modo demo por defecto
        demo_config = {
            "id": "demo_control",
            "execute_demo": "false",
            "pcap_file": "/app/models/data/small/Malware/Zeus.pcap",
            "created_at": int(time.time()),
            "description": "Configuración del modo demo",
            "environment": "aws",
            "aws_region": "us-east-1"
        }
        
        table.put_item(Item=demo_config)
        logger.info("✅ Configuración de demo establecida")
        
        # Crear registro de health check
        health_check = {
            "id": "health_check",
            "status": "healthy",
            "last_check": int(time.time()),
            "description": "Registro para health check",
            "environment": "aws",
            "aws_region": "us-east-1"
        }
        
        table.put_item(Item=health_check)
        logger.info("✅ Registro de health check creado")
        
        # Crear configuración de la aplicación
        app_config = {
            "id": "app_config",
            "version": "1.0.0",
            "environment": "aws",
            "model_path": "/app/models/training/detection/convlstm_model_ransomware_final.keras",
            "created_at": int(time.time()),
            "description": "Configuración de la aplicación",
            "aws_region": "us-east-1",
            "sagemaker_endpoint": "sm-detector",
            "ecs_cluster": "mirror-cluster",
            "ecs_service": "mirror-sensor"
        }
        
        table.put_item(Item=app_config)
        logger.info("✅ Configuración de aplicación guardada")
        
        logger.info("🎉 ¡Registros base configurados exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error configurando registros base: {e}")
        return False

def main():
    """Función principal"""
    success = setup_base_records()
    
    if success:
        print("\n✅ ¡Registros base configurados en AWS!")
        print("🌐 La aplicación está lista para usar")
        print("📋 Próximos pasos:")
        print("   1. Verificar estado: make check-aws-status")
        print("   2. Probar API HTTP usando el DNS del ALB")
        sys.exit(0)
    else:
        print("\n❌ Error configurando registros base")
        sys.exit(1)

if __name__ == "__main__":
    main()

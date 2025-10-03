#!/usr/bin/env python3
"""
Script para verificar detecciones de malware en DynamoDB
"""
import os
import sys
from app.sensor.src.utils.dynamo_client import DynamoClient

def check_malware_detections():
    """Verifica y muestra las detecciones de malware en DynamoDB"""
    
    # Configurar DynamoDB local
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        client = DynamoClient('demo-pcap-control')
        
        # mostrar todos los items de la tabla
        print(f'✅ Items: {client.table.scan()["Items"]}')
            
    except Exception as e:
        print(f'❌ Error verificando detecciones: {e}')
        sys.exit(1)

if __name__ == "__main__":
    check_malware_detections()

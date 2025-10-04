#!/usr/bin/env python3
"""
Explorador de DynamoDB Local
"""

import os
import boto3
import json
from app.sensor.src.utils.dynamo_client import DynamoClient

# Configurar DynamoDB local
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def list_tables():
    """Lista todas las tablas"""
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
    tables = list(dynamodb.tables.all())
    print("📋 Tablas disponibles:")
    for table in tables:
        print(f"  - {table.name}")
    return tables

def scan_table(table_name):
    """Escanea toda la tabla"""
    client = DynamoClient(table_name)
    try:
        response = client.table.scan()
        items = response.get('Items', [])
        print(f"\n📊 Tabla: {table_name}")
        print(f"📦 Total de items: {len(items)}")
        print("-" * 60)
        
        for item in items:
            print(f"🔑 ID: {item.get('id', 'N/A')}")
            for key, value in item.items():
                if key != 'id':
                    print(f"   {key}: {value}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Error escaneando tabla {table_name}: {e}")

def query_by_id(table_name, item_id):
    """Consulta un item específico por ID"""
    client = DynamoClient(table_name)
    item = client.get({"id": item_id})
    if item:
        print(f"\n🔍 Item encontrado:")
        for key, value in item.items():
            print(f"   {key}: {value}")
    else:
        print(f"❌ No se encontró item con ID: {item_id}")

def main():
    print("🔍 EXPLORADOR DE DYNAMODB LOCAL")
    print("=" * 50)
    
    # Listar tablas
    tables = list_tables()
    
    if not tables:
        print("❌ No hay tablas disponibles")
        return
    
    # Escanear cada tabla
    for table in tables:
        scan_table(table.name)
    
    # Mostrar estadísticas
    print("\n📈 ESTADÍSTICAS:")
    for table in tables:
        client = DynamoClient(table.name)
        try:
            response = client.table.scan()
            items = response.get('Items', [])
            
            # Contar tipos de items
            demo_items = [item for item in items if item.get('id') == 'demo_control']
            malware_items = [item for item in items if item.get('id', '').startswith('malware_')]
            
            print(f"  📋 {table.name}:")
            print(f"     - Total: {len(items)}")
            print(f"     - Demo control: {len(demo_items)}")
            print(f"     - Malware detections: {len(malware_items)}")
            
        except Exception as e:
            print(f"     ❌ Error: {e}")

if __name__ == "__main__":
    main()

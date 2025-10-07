#!/usr/bin/env python3
"""
Script para inicializar DynamoDB Local
"""
import os
import boto3
import time

# Configurar endpoint local
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def clear_table_data():
    """Borra todos los datos de la tabla si existe"""
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
    
    try:
        table = dynamodb.Table('demo-pcap-control')
        
        # Verificar si la tabla existe
        table.load()
        
        # Escanear todos los items
        response = table.scan()
        items = response.get('Items', [])
        
        if items:
            print(f"🗑️ Borrando {len(items)} items existentes...")
            
            # Borrar cada item
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={'id': item['id']})
            
            print("✅ Todos los datos borrados")
        else:
            print("ℹ️ No hay datos para borrar")
            
    except Exception as e:
        print(f"ℹ️ Tabla no existe o error al borrar: {e}")

def create_table():
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
    
    try:
        table = dynamodb.create_table(
            TableName='demo-pcap-control',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("✅ Tabla creada")
        return table
    except Exception as e:
        print(f"Tabla ya existe o error: {e}")
        return dynamodb.Table('demo-pcap-control')

def init_demo_record():
    table = boto3.resource('dynamodb', endpoint_url='http://localhost:8000').Table('demo-pcap-control')
    
    table.put_item(Item={
        'id': 'demo_control',
        'execute_demo': 'false',
        'pcap_file': ''
    })
    print("✅ Registro demo inicializado")

def show_table():
    table = boto3.resource('dynamodb', endpoint_url='http://localhost:8000').Table('demo-pcap-control')
    # print with format
    print(f"✅ Tabla: {table.name}")
    print(f"✅ Items: {table.scan()['Items']}")

if __name__ == "__main__":
    print("🚀 Inicializando DynamoDB Local...")
    
    # Primero borrar todos los datos existentes
    clear_table_data()
    
    # Luego crear/verificar la tabla
    create_table()
    time.sleep(2)
    
    # Inicializar el registro demo
    init_demo_record()
    
    # Mostrar el estado final
    show_table()
    print("🎉 Listo!")

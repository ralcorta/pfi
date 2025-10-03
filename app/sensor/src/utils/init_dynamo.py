#!/usr/bin/env python3
"""
Script para inicializar la tabla DynamoDB con el registro de control de demo
"""
import boto3
from dynamo_client import DynamoClient


def create_table_if_not_exists(table_name):
    """Crea la tabla si no existe"""
    dynamodb = boto3.resource('dynamodb')
    
    try:
        # Verificar si la tabla ya existe
        table = dynamodb.Table(table_name)
        table.load()
        print(f"✅ Tabla {table_name} ya existe")
        return True
    except Exception:
        # La tabla no existe, crearla
        try:
            table = dynamodb.create_table(
                TableName=table_name,
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
            
            # Esperar a que la tabla esté activa
            print(f"⏳ Creando tabla {table_name}...")
            table.wait_until_exists()
            print(f"✅ Tabla {table_name} creada exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error creando tabla: {e}")
            return False


def initialize_demo_control():
    """Inicializa la tabla con el registro de control de demo"""
    table_name = "demo-pcap-control"
    
    # Crear tabla si no existe
    if not create_table_if_not_exists(table_name):
        return False
    
    # Crear cliente
    client = DynamoClient(table_name)
    
    # Verificar si ya existe el registro
    existing = client.get({"id": "demo_control"})
    if existing:
        print("📋 Registro de control ya existe:")
        print(f"   - execute_demo: {existing.get('execute_demo', 'N/A')}")
        print(f"   - pcap_file: {existing.get('pcap_file', 'N/A')}")
        return True
    
    # Crear el registro inicial
    initial_record = {
        "id": "demo_control",
        "execute_demo": "false",
        "pcap_file": ""
    }
    
    # Guardar el registro
    success = client.save(initial_record)
    if success:
        print("✅ Registro de control inicializado:")
        print(f"   - id: demo_control")
        print(f"   - execute_demo: false")
        print(f"   - pcap_file: (vacío)")
        return True
    else:
        print("❌ Error inicializando registro")
        return False


def init_dynamo():
    print("🚀 Inicializando tabla DynamoDB para control de demo...")
    print("=" * 50)
    
    success = initialize_demo_control()
    
    if success:
        print("\n🎉 Inicialización completada exitosamente!")
    else:
        print("\n❌ Error en la inicialización")
        exit(1)

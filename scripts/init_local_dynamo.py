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
    create_table()
    time.sleep(2)
    init_demo_record()
    show_table()
    print("🎉 Listo!")

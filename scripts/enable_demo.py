#!/usr/bin/env python3
"""
Script para habilitar el modo demo en DynamoDB
Permite al sensor procesar archivos .pcap en lugar de captura en vivo
"""
import os
import sys
import argparse
from app.sensor.src.utils.dynamo_client import DynamoClient

def enable_demo(pcap_file="/app/models/data/small/Malware/Zeus.pcap"):
    """Habilita el modo demo con un archivo .pcap específico"""
    
    # Configurar DynamoDB local
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        client = DynamoClient('demo-pcap-control')
        
        # Habilitar demo
        demo_config = {
            'id': 'demo_control',
            'execute_demo': 'true',
            'pcap_file': pcap_file
        }
        
        success = client.save(demo_config)
        
        if success:
            print(f'✅ Demo habilitado con archivo: {pcap_file}')
            print('🎭 El sensor ahora procesará el archivo .pcap en lugar de captura en vivo')
        else:
            print('❌ Error al habilitar demo')
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Error habilitando demo: {e}')
        sys.exit(1)

def disable_demo():
    """Deshabilita el modo demo"""
    
    # Configurar DynamoDB local
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        client = DynamoClient('demo-pcap-control')
        
        # Deshabilitar demo
        demo_config = {
            'id': 'demo_control',
            'execute_demo': 'false',
            'pcap_file': ''
        }
        
        success = client.save(demo_config)
        
        if success:
            print('✅ Demo deshabilitado')
            print('🛡️ El sensor ahora capturará tráfico en vivo')
        else:
            print('❌ Error al deshabilitar demo')
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Error deshabilitando demo: {e}')
        sys.exit(1)

def check_demo_status():
    """Verifica el estado actual del modo demo"""
    
    # Configurar DynamoDB local
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    try:
        client = DynamoClient('demo-pcap-control')
        
        # Obtener configuración actual
        config = client.get({'id': 'demo_control'})
        
        if config:
            execute_demo = config.get('execute_demo', 'false')
            pcap_file = config.get('pcap_file', '')
            
            print(f'📊 Estado del modo demo:')
            print(f'  - Ejecutar demo: {execute_demo}')
            print(f'  - Archivo .pcap: {pcap_file if pcap_file else "Ninguno"}')
            
            if execute_demo == 'true':
                print('🎭 Modo demo ACTIVO')
            else:
                print('🛡️ Modo captura en vivo ACTIVO')
        else:
            print('❌ No se encontró configuración de demo')
            sys.exit(1)
            
    except Exception as e:
        print(f'❌ Error verificando estado: {e}')
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Controlar modo demo del sensor')
    parser.add_argument('action', choices=['enable', 'disable', 'status'], 
                       help='Acción a realizar')
    parser.add_argument('--pcap', default='/app/models/data/small/Malware/Zeus.pcap',
                       help='Archivo .pcap a usar en modo demo')
    
    args = parser.parse_args()
    
    if args.action == 'enable':
        enable_demo(args.pcap)
    elif args.action == 'disable':
        disable_demo()
    elif args.action == 'status':
        check_demo_status()

if __name__ == "__main__":
    main()

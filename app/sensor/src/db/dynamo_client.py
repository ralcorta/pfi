"""
Cliente simple para DynamoDB.
Maneja operaciones básicas de la tabla de detecciones.
"""

import boto3
from decimal import Decimal
from typing import Any, Dict
import time

from app.sensor.src.utils.environment import env


class DynamoClient:
    """Cliente simple para operaciones de DynamoDB."""
    
    def __init__(self):
        # Configurar DynamoDB (local o AWS)
        dynamo_config = {
            "region_name": env.aws_region
        }
        
        # Si hay endpoint local configurado, usarlo
        if env.dynamodb_endpoint:
            dynamo_config["endpoint_url"] = env.dynamodb_endpoint
            print(f"🔗 Usando DynamoDB local en: {env.dynamodb_endpoint}")
        else:
            print(f"☁️  Usando DynamoDB en AWS región: {env.aws_region}")
        
        self.dynamo = boto3.resource("dynamodb", **dynamo_config)
        self.client = boto3.client("dynamodb", **dynamo_config)
        
        # Crear tabla si no existe
        self._ensure_table_exists()
        
        self.table = self.dynamo.Table(env.dynamodb_table_name)

    def _ensure_table_exists(self):
        """Crea la tabla si no existe."""
        table_name = env.dynamodb_table_name
        
        try:
            # Verificar si la tabla existe
            self.client.describe_table(TableName=table_name)
            print(f"✅ Tabla '{table_name}' ya existe")
        except self.client.exceptions.ResourceNotFoundException:
            print(f"📋 Creando tabla '{table_name}'...")
            self._create_table()
        except Exception as e:
            print(f"❌ Error verificando tabla: {e}")
            raise

    def _create_table(self):
        """Crea la tabla de detecciones."""
        table_name = env.dynamodb_table_name
        
        table_schema = {
            'TableName': table_name,
            'KeySchema': [
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'N'  # Number
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'  # On-demand pricing
        }
        
        try:
            # Crear tabla
            response = self.client.create_table(**table_schema)
            print(f"🔄 Tabla '{table_name}' creada, esperando activación...")
            
            # Esperar a que la tabla esté activa
            waiter = self.client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            
            print(f"✅ Tabla '{table_name}' activa y lista para usar")
            
        except Exception as e:
            print(f"❌ Error creando tabla: {e}")
            raise

    def to_native(self, obj: Any) -> Any:
        """Convierte objetos DynamoDB a tipos nativos de Python."""
        if isinstance(obj, list):
            return [self.to_native(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.to_native(v) for k, v in obj.items()}
        if isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    def get_all_detections(self) -> Dict[str, Any]:
        """Trae todas las detecciones de la tabla."""
        all_items = []
        last_evaluated_key = None
        
        while True:
            scan_kwargs = {}
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
            
            resp = self.table.scan(**scan_kwargs)
            
            items = resp.get('Items', [])
            all_items.extend(items)
            
            last_evaluated_key = resp.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        all_items = self.to_native(all_items)
        return {
            "detections": all_items,
            "total_count": len(all_items),
            "message": "Toda la base de datos cargada"
        }
    
    def put_detection(self, item: Dict[str, Any]) -> None:
        """Guarda una detección en la tabla."""
        # Agregar ID único y timestamp si no existen
        if 'id' not in item:
            import uuid
            item['id'] = str(uuid.uuid4())
        
        if 'timestamp' not in item:
            item['timestamp'] = int(time.time() * 1000)  # Timestamp en milisegundos
        
        self.table.put_item(Item=item)
        print(f"💾 Detección guardada: {item['id']}")
    
    def clear_table(self) -> None:
        """Elimina todos los elementos de la tabla."""
        print(f"🗑️  Limpiando tabla '{env.dynamodb_table_name}'...")
        deleted_count = 0
        
        # Escanear todos los elementos
        while True:
            scan_kwargs = {}
            resp = self.table.scan(**scan_kwargs)
            items = resp.get('Items', [])
            
            if not items:
                break
            
            # Eliminar cada item
            for item in items:
                self.table.delete_item(
                    Key={
                        'id': item['id'],
                        'timestamp': item['timestamp']
                    }
                )
                deleted_count += 1
            
            # Verificar si hay más items
            last_evaluated_key = resp.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
        
        print(f"✅ Tabla limpiada: {deleted_count} elementos eliminados")


# Instancia global
db = DynamoClient()

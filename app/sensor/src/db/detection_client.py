"""
Cliente para gestionar detecciones en DynamoDB.
Maneja la tabla de detecciones de malware.
"""

import boto3
import uuid
import time
from decimal import Decimal
from typing import Any

from app.sensor.src.utils.environment import env
from app.sensor.src.db.models import Detection, DetectionResponse


class DetectionClient:
    """Cliente para operaciones de detecciones en DynamoDB."""
    
    def __init__(self):
        self.table_name = env.dynamodb_table_name
        self.dynamo, self.client = self._init_dynamodb()
        self._ensure_table_exists()
        self.table = self.dynamo.Table(self.table_name)

    def _init_dynamodb(self):
        """Inicializa la conexión a DynamoDB (local o AWS)."""
        config = {"region_name": env.aws_region}
        
        if env.dynamodb_endpoint:
            config["endpoint_url"] = env.dynamodb_endpoint
            print(f"🔗 Usando DynamoDB local en: {env.dynamodb_endpoint}")
        else:
            print(f"☁️  Usando DynamoDB en AWS región: {env.aws_region}")
        
        return boto3.resource("dynamodb", **config), boto3.client("dynamodb", **config)

    def _ensure_table_exists(self):
        """Crea la tabla de detecciones si no existe."""
        try:
            self.client.describe_table(TableName=self.table_name)
            print(f"✅ Tabla de detecciones '{self.table_name}' ya existe")
        except self.client.exceptions.ResourceNotFoundException:
            print(f"📋 Creando tabla de detecciones '{self.table_name}'...")
            self._create_table()
        except Exception as e:
            print(f"❌ Error verificando tabla de detecciones: {e}")
            raise

    def _create_table(self):
        """Crea la tabla de detecciones."""
        schema = {
            'TableName': self.table_name,
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
        
        try:
            self.client.create_table(**schema)
            print(f"🔄 Tabla '{self.table_name}' creada, esperando activación...")
            
            waiter = self.client.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            
            print(f"✅ Tabla '{self.table_name}' activa y lista para usar")
        except Exception as e:
            print(f"❌ Error creando tabla de detecciones: {e}")
            raise

    def _to_native(self, obj: Any) -> Any:
        """Convierte objetos DynamoDB (Decimal) a tipos nativos de Python."""
        if isinstance(obj, list):
            return [self._to_native(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self._to_native(v) for k, v in obj.items()}
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    def get_all_detections(self) -> DetectionResponse:
        """Obtiene todas las detecciones de la tabla."""
        all_items = []
        last_key = None
        
        while True:
            scan_kwargs = {} if not last_key else {'ExclusiveStartKey': last_key}
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
            
            all_items.extend(items)
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        # Convertir a modelos tipados
        all_items = self._to_native(all_items)
        detections = [Detection(**item) for item in all_items]
        
        return DetectionResponse(
            detections=detections,
            total_count=len(detections),
            message="Toda la base de datos cargada"
        )
    
    def put_detection(self, item: dict) -> None:
        """Guarda una detección en la tabla."""
        # Agregar ID único y timestamp si no existen
        if 'id' not in item:
            item['id'] = str(uuid.uuid4())
        
        if 'timestamp' not in item:
            item['timestamp'] = int(time.time() * 1000)
        
        self.table.put_item(Item=item)
        print(f"💾 Detección guardada: {item['id']}")
    
    def has_detection_for_ip(self, vni: int, src_ip: str) -> bool:
        """
        Verifica si ya existe una detección previa para esta IP origen y VNI.
        
        Args:
            vni: VNI del cliente
            src_ip: IP de origen a verificar
            
        Returns:
            True si ya existe una detección previa, False si es nueva
        """
        try:
            # Escanear la tabla buscando detecciones de esta IP para este VNI
            response = self.table.scan(
                FilterExpression="vni = :vni AND src_ip = :src_ip",
                ExpressionAttributeValues={
                    ":vni": Decimal(vni),
                    ":src_ip": src_ip
                },
                Limit=1  # Solo necesitamos saber si existe al menos una
            )
            
            items = response.get('Items', [])
            return len(items) > 0
            
        except Exception as e:
            print(f"⚠️  Error verificando detecciones previas para IP {src_ip} y VNI {vni}: {e}")
            # En caso de error, retornar False para permitir el envío (mejor prevenir que bloquear)
            return False
    
    def clear_table(self) -> None:
        """Elimina todos los elementos de la tabla de detecciones."""
        print(f"🗑️  Limpiando tabla de detecciones '{self.table_name}'...")
        deleted_count = 0
        
        last_key = None
        while True:
            scan_kwargs = {} if not last_key else {'ExclusiveStartKey': last_key}
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
            
            for item in items:
                self.table.delete_item(
                    Key={'id': item['id'], 'timestamp': item['timestamp']}
                )
                deleted_count += 1
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        print(f"✅ Tabla de detecciones limpiada: {deleted_count} elementos eliminados")


# Instancia global
detection_db = DetectionClient()


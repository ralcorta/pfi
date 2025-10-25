"""
Cliente simple para DynamoDB.
Maneja operaciones básicas de la tabla de detecciones.
"""

import boto3
from decimal import Decimal
from typing import Any, Dict, List

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
        self.table = self.dynamo.Table(env.dynamodb_table_name)

    
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
        self.table.put_item(Item=item)


# Instancia global
db = DynamoClient()

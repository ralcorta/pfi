#!/usr/bin/env python3
"""
Cliente simple para DynamoDB con nombres genéricos
"""
import os
import boto3
from typing import Dict, Any, Optional

from app.sensor.src.utils.config import Config


class DynamoClient:
    """Cliente simple para leer y escribir en cualquier tabla DynamoDB"""
    
    def __init__(self, table_name: str):
        """
        Inicializa el cliente
        
        Args:
            table_name: Nombre de la tabla DynamoDB
        """
        self.config = Config()
        self.table_name = table_name
        
        # Usar endpoint local si está configurado
        endpoint_url = os.getenv('AWS_ENDPOINT_URL')
        if endpoint_url:
            self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
        else:
            self.dynamodb = boto3.resource('dynamodb')
        
        self.table = self.dynamodb.Table(table_name)
    
    def get(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Obtiene un item de la tabla
        
        Args:
            key: Clave primaria del item
            
        Returns:
            Dict con los datos del item o None si no existe
        """
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except Exception as e:
            print(f"Error obteniendo item: {e}")
            return None
    
    def save(self, item: Dict[str, Any]) -> bool:
        """
        Guarda un item en la tabla
        
        Args:
            item: Datos a guardar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            print(f"Error guardando item: {e}")
            return False

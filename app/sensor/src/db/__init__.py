"""
Módulo de base de datos del sensor.
Contiene clientes para gestionar usuarios y detecciones en DynamoDB.
"""

from app.sensor.src.db.user_client import user_db
from app.sensor.src.db.detection_client import detection_db

__all__ = ['user_db', 'detection_db']

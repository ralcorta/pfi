#!/usr/bin/env python3
"""
Script para limpiar la tabla de DynamoDB.
Elimina todos los elementos de la tabla de detecciones.
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.sensor.src.db.detection_client import detection_db

if __name__ == "__main__":
    try:
        print("🗑️  Limpiando tabla de detecciones...")
        detection_db.clear_table()
        print("✅ Tabla de detecciones limpiada exitosamente")
    except Exception as e:
        print(f"❌ Error limpiando tabla: {e}")
        sys.exit(1)


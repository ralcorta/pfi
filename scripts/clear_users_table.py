#!/usr/bin/env python3
"""
Script para limpiar la tabla de usuarios en DynamoDB.
Elimina todos los usuarios de la tabla.
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.sensor.src.db.user_client import user_db

if __name__ == "__main__":
    try:
        print("🗑️  Limpiando tabla de usuarios en DynamoDB...")
        user_db.clear_table()
        print("✅ Tabla de usuarios limpiada exitosamente")
    except Exception as e:
        print(f"❌ Error limpiando tabla de usuarios: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


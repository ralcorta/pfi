"""
Router para la API de control del sensor de malware.
Maneja endpoints de salud, estadísticas y detecciones.
"""

from fastapi import APIRouter, HTTPException
from app.sensor.src.db.dynamo_client import db


router = APIRouter()

@router.get("/")
def root():
    """Endpoint raíz del sistema."""
    return {
        "endpoints": [
            "/",
            "/healthz",
            "/stats",
            "/detections"
        ]
    }

@router.get("/healthz")
def healthz():
    """Endpoint de salud del sistema."""
    return {
        "status": "ok",
        "system": "simplified",
        "http_server": "running"
    }


@router.get("/stats")
def get_stats():
    """Estadísticas básicas del sistema."""
    return {
        "status": "running",
        "system": "simplified",
    }


@router.get("/detections")
def get_all_database():
    """
    Trae toda la base de datos de detecciones.
    """
    try:
        return db.get_all_detections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

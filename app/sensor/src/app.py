"""
app.py — Sensor multi-tenant (VXLAN/UDP 4789) + API de control (FastAPI)

Aplicación principal que combina:
- Servicio de sensor UDP para análisis de tráfico
- API HTTP para control y consultas
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.sensor.src.router.router import router
from app.sensor.src.service.sensor_service import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    print("🚀 Iniciando aplicación del sensor...")
    
    # Iniciar servicio del sensor
    await sensor_service.start()
    
    yield
    
    # Detener servicio del sensor
    await sensor_service.stop()
    print("🛑 Aplicación del sensor detenida")


# Crear aplicación FastAPI
app = FastAPI(
    title="Malware Detection Sensor",
    version="1.0.0",
    description="Sensor de detección de malware con análisis de tráfico UDP",
    lifespan=lifespan
)

# Incluir router con endpoints
app.include_router(router)
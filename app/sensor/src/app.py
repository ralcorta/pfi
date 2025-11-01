"""
app.py — Sensor multi-tenant (VXLAN/UDP 4789) + API de control (FastAPI)

Aplicación principal que combina:
- Servicio de sensor UDP para análisis de tráfico
- API HTTP para control y consultas
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.sensor.src.router.router import router
from app.sensor.src.service.sensor_service import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    print("🚀 Iniciando aplicación del sensor...")
    
    try:
        # Iniciar servicio del sensor
        await sensor_service.start()
        print("✅ Lifespan: Servicio del sensor iniciado correctamente")
    except Exception as e:
        print(f"❌ Error crítico iniciando servicio del sensor en lifespan: {e}")
        import traceback
        print(traceback.format_exc())
    
    yield
    
    try:
        # Detener servicio del sensor
        await sensor_service.stop()
        print("🛑 Aplicación del sensor detenida")
    except Exception as e:
        print(f"⚠️ Error deteniendo servicio del sensor: {e}")


# Crear aplicación FastAPI
app = FastAPI(
    title="Malware Detection Sensor",
    version="1.0.0",
    description="Sensor de detección de malware con análisis de tráfico UDP",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # No puede ser True con allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir router con endpoints
app.include_router(router)
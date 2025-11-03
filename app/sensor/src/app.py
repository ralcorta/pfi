from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.sensor.src.router.router import router
from app.sensor.src.service.sensor_service import sensor_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting application...")
    
    try:
        await sensor_service.start()
        print("Lifespan: Sensor service started successfully")
    except Exception as e:
        print(f"Error critical starting sensor service in lifespan: {e}")
        import traceback
        print(traceback.format_exc())
    
    yield
    
    try:
        await sensor_service.stop()
        print("Application stopped")
    except Exception as e:
        print(f"Error stopping sensor service: {e}")


app = FastAPI(
    title="Malware Detection Sensor",
    version="1.0.0",
    description="Sensor de detección de malware con análisis de tráfico UDP",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
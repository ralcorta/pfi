import os
from typing import Optional
from dotenv import load_dotenv


class Environment:
    """Simple environment configuration class."""
    
    def __init__(self):
        # Cargar variables de entorno desde .env
        self._load_env_file()
        
        # AWS Configuration
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        # No usar endpoint local por defecto; solo si está definido explícitamente
        self.dynamodb_endpoint = os.getenv("AWS_DYNAMO_DB_ENDPOINT") or None
        self.dynamodb_table_name = os.getenv("AWS_DYNAMO_DB_TABLE_NAME", "detections")
        self.users_table_name = os.getenv("AWS_USERS_TABLE_NAME", "users")
        
        # Traffic Mirror Configuration
        self.traffic_mirror_target_id = os.getenv("TRAFFIC_MIRROR_TARGET_ID", "")
        
        # Network Configuration
        self.vxlan_port = int(os.getenv("VXLAN_PORT", "4789"))
        self.http_port = int(os.getenv("HTTP_PORT", "8080"))
        
        # Processing Configuration
        self.workers = int(os.getenv("WORKERS", "4"))
        self.queue_max = int(os.getenv("QUEUE_MAX", "20000"))
        
        # Temporal Configuration
        self.window_seconds = float(os.getenv("WINDOW_SECONDS", "3.0"))
        self.max_pkts_per_window = int(os.getenv("MAX_PKTS_PER_WINDOW", "256"))

        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "info")
        
        # Email Configuration (Resend.com)
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.email_from_address = os.getenv("EMAIL_FROM_ADDRESS", "")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080")
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:5173")
    
    def _load_env_file(self):
        """Carga variables de entorno desde archivo .env"""
        # Por defecto NO cargar .env en contenedores. Solo si se habilita explícitamente.
        if os.getenv("ENABLE_DOTENV") != "1":
            print("🚫 Saltando carga de .env (habilitar con ENABLE_DOTENV=1)")
            return
        # Buscar archivo .env en el directorio del sensor
        sensor_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        env_file = os.path.join(sensor_dir, ".env")
        
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"📄 Cargando variables de entorno desde: {env_file}")
        else:
            print(f"⚠️  Archivo .env no encontrado en: {env_file}")
            print("💡 Crear archivo .env con las variables necesarias")
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """Get environment variable with optional default."""
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        return int(os.getenv(key, str(default)))
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get environment variable as float."""
        return float(os.getenv(key, str(default)))


# Global instance
env = Environment()

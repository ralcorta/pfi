import os
from typing import Optional
from dotenv import load_dotenv


class Environment:
    
    def __init__(self):
        self._load_env_file()
        
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.dynamodb_endpoint = os.getenv("AWS_DYNAMO_DB_ENDPOINT") or None
        self.dynamodb_table_name = os.getenv("AWS_DYNAMO_DB_TABLE_NAME", "detections")
        self.users_table_name = os.getenv("AWS_USERS_TABLE_NAME", "users")
        
        self.traffic_mirror_target_id = os.getenv("TRAFFIC_MIRROR_TARGET_ID", "")
        
        self.vxlan_port = int(os.getenv("VXLAN_PORT", "4789"))
        self.http_port = int(os.getenv("HTTP_PORT", "8080"))
        
        self.workers = int(os.getenv("WORKERS", "4"))
        self.queue_max = int(os.getenv("QUEUE_MAX", "20000"))
        
        self.window_seconds = float(os.getenv("WINDOW_SECONDS", "3.0"))
        self.max_pkts_per_window = int(os.getenv("MAX_PKTS_PER_WINDOW", "256"))

        self.log_level = os.getenv("LOG_LEVEL", "info")
        
        self.email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.email_from_address = os.getenv("EMAIL_FROM_ADDRESS", "")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080")
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:5173")
    
    def _load_env_file(self):
        if os.getenv("ENABLE_DOTENV") != "1":
            print("Skipping .env loading (enable with ENABLE_DOTENV=1)")
            return
        sensor_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        env_file = os.path.join(sensor_dir, ".env")
        
        if os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"Loading environment variables from: {env_file}")
        else:
            print(f".env file not found in: {env_file}")
            print("Create .env file with the necessary variables")
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        return os.getenv(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        return int(os.getenv(key, str(default)))
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        return float(os.getenv(key, str(default)))


env = Environment()

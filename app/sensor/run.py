"""
Script to run the sensor application.

This is the main entry point for the sensor application.
It handles configuration, logging, and starts the FastAPI server.
"""
import os
import sys
import signal
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main entry point for the sensor application"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("HTTP_PORT", "8080"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print(f"🚀 Starting sensor application...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   VXLAN Port: {os.getenv('VXLAN_PORT', '4789')}")
    print(f"   DynamoDB Table: {os.getenv('DDB_TABLE', 'detections')}")
    print(f"   Workers: {os.getenv('WORKERS', '4')}")
    print(f"   Log Level: {log_level}")
    
    try:
        import uvicorn
        uvicorn.run(
            "app.sensor.app:app",
            host=host,
            port=port,
            log_level=log_level,
            access_log=True,
            reload=False  # Disable reload in production
        )
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

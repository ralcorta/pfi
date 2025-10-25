"""
Script to run the sensor application.

This is the main entry point for the sensor application.
It handles configuration, logging, and starts the FastAPI server.
"""
import sys
import signal
import uvicorn

from app.sensor.src.utils.environment import env


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main entry point for the sensor application"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"🚀 Starting sensor application...")
    print(f"   VXLAN Port: {env.vxlan_port}")
    print(f"   DynamoDB Table: {env.dynamodb_table_name}")
    print(f"   Workers: {env.workers}")
    
    try:
        uvicorn.run(
            "app.sensor.src.app:app",
            host="0.0.0.0",
            port=env.http_port,
            log_level=env.log_level,
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

"""
Setup script for the sensor application.
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import boto3
        import scapy
        import pydantic
        print("✅ All dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: poetry install")
        return False

def setup_environment():
    """Setup environment configuration"""
    print("\n🔧 Setting up environment...")
    
    env_file = Path("env.example")
    if env_file.exists():
        print("✅ Environment template found")
        print("💡 Copy env.example to .env and customize as needed")
    else:
        print("❌ Environment template not found")

def create_dynamodb_table():
    """Create DynamoDB table for local development or AWS"""
    print("\n🗄️ Setting up DynamoDB table...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        import os
        
        # Detect environment
        endpoint_url = os.getenv('AWS_ENDPOINT_URL')
        region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        table_name = os.getenv('DDB_TABLE', 'detections')
        
        if endpoint_url:
            print(f"🔧 Using local DynamoDB: {endpoint_url}")
            # Local development
            dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
        else:
            print(f"☁️ Using AWS DynamoDB in region: {region}")
            # AWS production
            dynamodb = boto3.resource('dynamodb', region_name=region)
        
        try:
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'PK',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"✅ Created table: {table_name}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"✅ Table {table_name} already exists")
                return True
            else:
                print(f"❌ Error creating table: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error setting up DynamoDB: {e}")
        print("💡 Make sure DynamoDB Local is running on port 8000")
        return False

def test_application():
    """Test the application"""
    print("\n🧪 Testing application...")
    
    try:
        # Test import
        from app.sensor.app import app
        print("✅ Application imports successfully")
        
        # Test configuration
        print(f"   VXLAN Port: {os.getenv('VXLAN_PORT', '4789')}")
        print(f"   HTTP Port: {os.getenv('HTTP_PORT', '8080')}")
        print(f"   DynamoDB Table: {os.getenv('DDB_TABLE', 'detections')}")
        print(f"   Workers: {os.getenv('WORKERS', '4')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing application: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Sensor Application")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Setup environment
    setup_environment()
    
    # Create DynamoDB table
    create_dynamodb_table()
    
    # Test application
    if not test_application():
        return False
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Copy env.example to .env and customize")
    print("2. Start DynamoDB Local: docker-compose up -d dynamodb-local")
    print("3. Run the application: python -m app.sensor.run")
    print("4. Test the API: python app/sensor/test_client.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

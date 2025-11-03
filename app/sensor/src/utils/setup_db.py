import os
import sys
import boto3
from botocore.exceptions import ClientError
from app.sensor.src.utils.environment import env

def create_dynamodb_table():
    print("\nSetting up DynamoDB table...")
    
    try:
        endpoint_url = env.dynamodb_endpoint
        region = env.aws_region
        table_name = env.dynamodb_table_name
        
        if endpoint_url:
            print(f"Using local DynamoDB: {endpoint_url}")
            dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'dummy'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'dummy')
            )
        else:
            print(f"Using AWS DynamoDB in region: {region}")
            dynamodb = boto3.resource('dynamodb', region_name=region)
        
        try:
            dynamodb.create_table(
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
            print(f"Created table: {table_name}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"Table {table_name} already exists")
                return True
            else:
                print(f"Error creating table: {e}")
                return False
                
    except Exception as e:
        print(f"Error setting up DynamoDB: {e}")
        print("Make sure DynamoDB Local is running on port 8000")
        return False

def main():
    print("Setting up DynamoDB Table")
    print("=" * 40)
    
    if create_dynamodb_table():
        print("\nDynamoDB setup completed successfully!")
        return True
    else:
        print("\nDynamoDB setup failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

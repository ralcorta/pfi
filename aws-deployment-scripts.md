# AWS Deployment Scripts

Este documento contiene scripts prácticos para implementar la arquitectura de detección de ransomware en AWS.

## Scripts de Infraestructura

### 1. Crear Infraestructura Base (CloudFormation)

```yaml
# infrastructure/ransomware-detection-infrastructure.yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: "Infrastructure for Ransomware Detection System"

Parameters:
  Environment:
    Type: String
    Default: "dev"
    AllowedValues: ["dev", "staging", "prod"]

  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: "VPC ID where the system will be deployed"

Resources:
  # S3 Bucket for data storage
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::AccountId}-ransomware-detection-data-${Environment}"
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref KMSKey
      LifecycleConfiguration:
        Rules:
          - Id: DeleteOldVersions
            Status: Enabled
            NoncurrentVersionExpirationInDays: 30
          - Id: TransitionToIA
            Status: Enabled
            Transitions:
              - StorageClass: STANDARD_IA
                TransitionInDays: 30

  # KMS Key for encryption
  KMSKey:
    Type: AWS::KMS::Key
    Properties:
      Description: "KMS key for ransomware detection data encryption"
      KeyPolicy:
        Version: "2012-10-17"
        Statement:
          - Sid: Enable IAM User Permissions
            Effect: Allow
            Principal:
              AWS: !Sub "arn:aws:iam::${AWS::AccountId}:root"
            Action: "kms:*"
            Resource: "*"

  # Kinesis Data Stream
  VpcFlowLogsStream:
    Type: AWS::Kinesis::Stream
    Properties:
      Name: !Sub "vpc-flow-logs-stream-${Environment}"
      ShardCount: 2
      RetentionPeriodHours: 24
      StreamEncryption:
        EncryptionType: KMS
        KeyId: !Ref KMSKey

  # SNS Topic for alerts
  SecurityAlertsTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub "security-alerts-${Environment}"
      DisplayName: "Security Alerts"
      KmsMasterKeyId: !Ref KMSKey

  # IAM Role for Lambda functions
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: KinesisAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - kinesis:GetRecords
                  - kinesis:GetShardIterator
                  - kinesis:DescribeStream
                Resource: !GetAtt VpcFlowLogsStream.Arn
        - PolicyName: S3Access
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                Resource: !Sub "${DataBucket}/*"

  # Security Group for detection sensor
  DetectionSensorSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: "Security group for ransomware detection sensor"
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 22
          ToPort: 22
          CidrIp: 10.0.0.0/8
          Description: "SSH access from VPC"
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
          Description: "HTTPS for SageMaker endpoint"
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0
          Description: "All outbound traffic"

Outputs:
  DataBucketName:
    Description: "S3 bucket for data storage"
    Value: !Ref DataBucket
    Export:
      Name: !Sub "${AWS::StackName}-DataBucket"

  VpcFlowLogsStreamName:
    Description: "Kinesis stream for VPC flow logs"
    Value: !Ref VpcFlowLogsStream
    Export:
      Name: !Sub "${AWS::StackName}-VpcFlowLogsStream"

  SecurityAlertsTopicArn:
    Description: "SNS topic for security alerts"
    Value: !Ref SecurityAlertsTopic
    Export:
      Name: !Sub "${AWS::StackName}-SecurityAlertsTopic"
```

### 2. Script de Despliegue

```bash
#!/bin/bash
# deploy-infrastructure.sh

set -e

ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}
STACK_NAME="ransomware-detection-${ENVIRONMENT}"

echo "Deploying infrastructure for environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Stack name: ${STACK_NAME}"

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file infrastructure/ransomware-detection-infrastructure.yaml \
  --stack-name ${STACK_NAME} \
  --parameter-overrides Environment=${ENVIRONMENT} \
  --capabilities CAPABILITY_IAM \
  --region ${REGION}

# Get outputs
DATA_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' \
  --output text)

KINESIS_STREAM=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`VpcFlowLogsStreamName`].OutputValue' \
  --output text)

SNS_TOPIC=$(aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --region ${REGION} \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityAlertsTopicArn`].OutputValue' \
  --output text)

echo "Infrastructure deployed successfully!"
echo "Data Bucket: ${DATA_BUCKET}"
echo "Kinesis Stream: ${KINESIS_STREAM}"
echo "SNS Topic: ${SNS_TOPIC}"

# Save outputs to file for other scripts
cat > deployment-outputs.json << EOF
{
  "environment": "${ENVIRONMENT}",
  "region": "${REGION}",
  "dataBucket": "${DATA_BUCKET}",
  "kinesisStream": "${KINESIS_STREAM}",
  "snsTopic": "${SNS_TOPIC}"
}
EOF
```

## Scripts de Machine Learning

### 3. Desplegar Modelo en SageMaker

```python
# ml/deploy_model.py
import boto3
import sagemaker
import tarfile
import os
from pathlib import Path

def create_model_package():
    """Create a SageMaker model package from the trained model."""

    # Create model directory
    model_dir = Path("model_package")
    model_dir.mkdir(exist_ok=True)

    # Copy model file
    model_file = Path("models/convlstm_model.keras")
    if not model_file.exists():
        raise FileNotFoundError(f"Model file not found: {model_file}")

    # Create inference script
    inference_script = model_dir / "inference.py"
    inference_script.write_text("""
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

def model_fn(model_dir):
    \"\"\"Load the model from the model directory.\"\"\"
    model_path = os.path.join(model_dir, 'convlstm_model.keras')
    model = load_model(model_path)
    return model

def input_fn(request_body, request_content_type):
    \"\"\"Parse input data from request body.\"\"\"
    if request_content_type == 'application/json':
        input_data = json.loads(request_body)
        # Convert to numpy array and reshape
        data = np.array(input_data, dtype=np.float32)
        # Ensure correct shape: (batch_size, 10, 32, 32, 1)
        if len(data.shape) == 4:
            data = np.expand_dims(data, axis=-1)
        return data
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model):
    \"\"\"Make predictions using the loaded model.\"\"\"
    predictions = model.predict(input_data)
    return predictions

def output_fn(prediction, content_type):
    \"\"\"Format prediction output.\"\"\"
    if content_type == 'application/json':
        # Convert numpy array to list
        result = prediction.tolist()
        return json.dumps(result)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
""")

    # Copy model file
    import shutil
    shutil.copy2(model_file, model_dir / "convlstm_model.keras")

    # Create requirements.txt
    requirements = model_dir / "requirements.txt"
    requirements.write_text("""
tensorflow==2.15.0
numpy==1.24.0
""")

    # Create tar.gz package
    with tarfile.open("model.tar.gz", "w:gz") as tar:
        tar.add(model_dir, arcname=".")

    return "model.tar.gz"

def deploy_to_sagemaker():
    """Deploy the model to SageMaker endpoint."""

    # Create model package
    model_package = create_model_package()

    # Initialize SageMaker
    sagemaker_session = sagemaker.Session()
    role = 'arn:aws:iam::123456789012:role/SageMakerExecutionRole'

    # Upload model to S3
    model_s3_path = sagemaker_session.upload_data(
        path=model_package,
        bucket='your-sagemaker-bucket',
        key_prefix='models/ransomware-detection'
    )

    # Create TensorFlow model
    from sagemaker.tensorflow import TensorFlowModel

    model = TensorFlowModel(
        model_data=model_s3_path,
        role=role,
        framework_version='2.15.0',
        py_version='py311',
        entry_point='inference.py'
    )

    # Deploy endpoint
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type='ml.m5.xlarge',
        endpoint_name='ransomware-detection-endpoint'
    )

    print(f"Model deployed to endpoint: {predictor.endpoint_name}")
    return predictor

if __name__ == "__main__":
    deploy_to_sagemaker()
```

### 4. Lambda Function para Preprocesamiento

```python
# lambda/vpc_flow_logs_processor.py
import json
import base64
import boto3
from datetime import datetime
import os

s3_client = boto3.client('s3')
kinesis_client = boto3.client('kinesis')

def lambda_handler(event, context):
    """Process VPC Flow Logs from Kinesis and store in S3."""

    bucket_name = os.environ['DATA_BUCKET']
    processed_count = 0

    for record in event['Records']:
        try:
            # Decode Kinesis data
            payload = base64.b64decode(record['kinesis']['data'])
            flow_log = json.loads(payload)

            # Process flow log
            processed_data = process_flow_log(flow_log)

            if processed_data:
                # Store in S3
                store_in_s3(processed_data, bucket_name)
                processed_count += 1

        except Exception as e:
            print(f"Error processing record: {e}")
            continue

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed_records': processed_count,
            'timestamp': datetime.utcnow().isoformat()
        })
    }

def process_flow_log(flow_log):
    """Process and filter VPC flow log data."""

    # Filter relevant traffic
    if not is_relevant_traffic(flow_log):
        return None

    # Extract relevant fields
    processed_data = {
        'timestamp': flow_log.get('windowstart'),
        'srcaddr': flow_log.get('srcaddr'),
        'dstaddr': flow_log.get('dstaddr'),
        'srcport': flow_log.get('srcport'),
        'dstport': flow_log.get('dstport'),
        'protocol': flow_log.get('protocol'),
        'packets': flow_log.get('packets'),
        'bytes': flow_log.get('bytes'),
        'action': flow_log.get('action')
    }

    return processed_data

def is_relevant_traffic(flow_log):
    """Determine if traffic is relevant for ransomware detection."""

    # Filter criteria
    protocol = flow_log.get('protocol')
    action = flow_log.get('action')
    bytes_count = flow_log.get('bytes', 0)

    # Only process TCP/UDP traffic that was accepted
    if protocol not in [6, 17] or action != 'ACCEPT':
        return False

    # Filter out very small packets (likely keep-alives)
    if bytes_count < 100:
        return False

    return True

def store_in_s3(data, bucket_name):
    """Store processed data in S3 with partitioning."""

    timestamp = datetime.fromtimestamp(data['timestamp'])
    year = timestamp.year
    month = timestamp.month
    day = timestamp.day
    hour = timestamp.hour

    # Create S3 key with partitioning
    s3_key = f"raw-traffic/year={year}/month={month:02d}/day={day:02d}/hour={hour:02d}/data_{timestamp.isoformat()}.json"

    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(data),
        ContentType='application/json'
    )
```

## Scripts de Configuración

### 5. Configurar VPC Flow Logs

```bash
#!/bin/bash
# setup-vpc-flow-logs.sh

VPC_ID=$1
KINESIS_STREAM_ARN=$2

if [ -z "$VPC_ID" ] || [ -z "$KINESIS_STREAM_ARN" ]; then
    echo "Usage: $0 <VPC_ID> <KINESIS_STREAM_ARN>"
    exit 1
fi

echo "Setting up VPC Flow Logs for VPC: $VPC_ID"
echo "Kinesis Stream: $KINESIS_STREAM_ARN"

# Create IAM role for VPC Flow Logs
aws iam create-role \
    --role-name VpcFlowLogsRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "vpc-flow-logs.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach policy to role
aws iam put-role-policy \
    --role-name VpcFlowLogsRole \
    --policy-name VpcFlowLogsPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "kinesis:PutRecord",
                    "kinesis:PutRecords"
                ],
                "Resource": "'$KINESIS_STREAM_ARN'"
            }
        ]
    }'

# Create VPC Flow Logs
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids $VPC_ID \
    --traffic-type ALL \
    --log-destination-type kinesis-data-streams \
    --log-destination $KINESIS_STREAM_ARN \
    --deliver-logs-permission-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/VpcFlowLogsRole

echo "VPC Flow Logs configured successfully!"
```

### 6. Configurar Traffic Mirroring

```bash
#!/bin/bash
# setup-traffic-mirroring.sh

VPC_ID=$1
SUBNET_ID=$2
SECURITY_GROUP_ID=$3

if [ -z "$VPC_ID" ] || [ -z "$SUBNET_ID" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo "Usage: $0 <VPC_ID> <SUBNET_ID> <SECURITY_GROUP_ID>"
    exit 1
fi

echo "Setting up Traffic Mirroring for VPC: $VPC_ID"

# Create traffic mirror target
TARGET_ID=$(aws ec2 create-traffic-mirror-target \
    --network-interface-id $ENI_ID \
    --query 'TrafficMirrorTarget.TrafficMirrorTargetId' \
    --output text)

echo "Traffic Mirror Target created: $TARGET_ID"

# Create traffic mirror filter
FILTER_ID=$(aws ec2 create-traffic-mirror-filter \
    --description "Ransomware detection filter" \
    --query 'TrafficMirrorFilter.TrafficMirrorFilterId' \
    --output text)

echo "Traffic Mirror Filter created: $FILTER_ID"

# Create filter rules
aws ec2 create-traffic-mirror-filter-rule \
    --traffic-mirror-filter-id $FILTER_ID \
    --traffic-direction ingress \
    --rule-number 1 \
    --rule-action accept \
    --protocol 6 \
    --destination-port-range From=80,To=443

aws ec2 create-traffic-mirror-filter-rule \
    --traffic-mirror-filter-id $FILTER_ID \
    --traffic-direction ingress \
    --rule-number 2 \
    --rule-action accept \
    --protocol 17 \
    --destination-port-range From=53,To=53

echo "Traffic Mirroring configured successfully!"
echo "Target ID: $TARGET_ID"
echo "Filter ID: $FILTER_ID"
```

## Scripts de Monitoreo

### 7. Dashboard de CloudWatch

```python
# monitoring/create_dashboard.py
import boto3
import json

def create_cloudwatch_dashboard():
    """Create CloudWatch dashboard for ransomware detection."""

    cloudwatch = boto3.client('cloudwatch')

    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["Custom/RansomwareDetection", "DetectionsPerMinute"],
                        ["Custom/RansomwareDetection", "ThreatScore"]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "Ransomware Detection Metrics",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/SageMaker", "ModelLatency", "EndpointName", "ransomware-detection-endpoint"],
                        ["AWS/SageMaker", "Invocations", "EndpointName", "ransomware-detection-endpoint"]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": "us-east-1",
                    "title": "SageMaker Endpoint Metrics",
                    "period": 300
                }
            },
            {
                "type": "log",
                "x": 0,
                "y": 6,
                "width": 24,
                "height": 6,
                "properties": {
                    "query": "SOURCE '/aws/ransomware-detection' | fields @timestamp, @message\n| filter @message like /RANSOMWARE DETECTED/\n| sort @timestamp desc\n| limit 20",
                    "region": "us-east-1",
                    "title": "Recent Ransomware Detections",
                    "view": "table"
                }
            }
        ]
    }

    cloudwatch.put_dashboard(
        DashboardName='RansomwareDetection',
        DashboardBody=json.dumps(dashboard_body)
    )

    print("CloudWatch dashboard created successfully!")

if __name__ == "__main__":
    create_cloudwatch_dashboard()
```

### 8. Script de Pruebas

```python
# testing/test_endpoint.py
import boto3
import json
import numpy as np
import time

def test_sagemaker_endpoint():
    """Test the SageMaker endpoint with sample data."""

    sagemaker_runtime = boto3.client('sagemaker-runtime')
    endpoint_name = 'ransomware-detection-endpoint'

    # Generate sample data (10 packets, 32x32 images)
    sample_data = np.random.rand(1, 10, 32, 32, 1).tolist()

    print("Testing SageMaker endpoint...")
    print(f"Sample data shape: {np.array(sample_data).shape}")

    start_time = time.time()

    try:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(sample_data)
        )

        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds

        # Parse response
        result = json.loads(response['Body'].read())

        print(f"✅ Endpoint test successful!")
        print(f"Latency: {latency:.2f}ms")
        print(f"Prediction: {result}")

        return True

    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        return False

def test_vpc_flow_logs():
    """Test VPC Flow Logs processing."""

    kinesis = boto3.client('kinesis')
    stream_name = 'vpc-flow-logs-stream'

    try:
        # Get shard iterator
        response = kinesis.get_shard_iterator(
            StreamName=stream_name,
            ShardId='shardId-000000000000',
            ShardIteratorType='LATEST'
        )

        shard_iterator = response['ShardIterator']

        # Get records
        response = kinesis.get_records(
            ShardIterator=shard_iterator,
            Limit=10
        )

        print(f"✅ VPC Flow Logs test successful!")
        print(f"Retrieved {len(response['Records'])} records")

        return True

    except Exception as e:
        print(f"❌ VPC Flow Logs test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running AWS infrastructure tests...")

    # Test SageMaker endpoint
    sagemaker_success = test_sagemaker_endpoint()

    # Test VPC Flow Logs
    flow_logs_success = test_vpc_flow_logs()

    if sagemaker_success and flow_logs_success:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed!")
```

## Scripts de Mantenimiento

### 9. Backup y Recuperación

```bash
#!/bin/bash
# backup/backup_model.sh

MODEL_BUCKET=$1
BACKUP_BUCKET=$2
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "$MODEL_BUCKET" ] || [ -z "$BACKUP_BUCKET" ]; then
    echo "Usage: $0 <MODEL_BUCKET> <BACKUP_BUCKET>"
    exit 1
fi

echo "Starting model backup..."
echo "Source bucket: $MODEL_BUCKET"
echo "Backup bucket: $BACKUP_BUCKET"
echo "Backup date: $DATE"

# Create backup directory
BACKUP_DIR="backup_${DATE}"
mkdir -p $BACKUP_DIR

# Download model files
aws s3 sync s3://$MODEL_BUCKET/ $BACKUP_DIR/

# Upload to backup bucket
aws s3 sync $BACKUP_DIR/ s3://$BACKUP_BUCKET/backups/$DATE/

# Clean up local files
rm -rf $BACKUP_DIR

echo "✅ Model backup completed successfully!"
echo "Backup location: s3://$BACKUP_BUCKET/backups/$DATE/"
```

### 10. Limpieza de Recursos

```bash
#!/bin/bash
# cleanup/cleanup_resources.sh

ENVIRONMENT=$1
REGION=${2:-us-east-1}

if [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 <ENVIRONMENT> [REGION]"
    exit 1
fi

echo "⚠️ WARNING: This will delete all resources for environment: $ENVIRONMENT"
echo "Region: $REGION"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 1
fi

STACK_NAME="ransomware-detection-${ENVIRONMENT}"

echo "Deleting CloudFormation stack: $STACK_NAME"

# Delete CloudFormation stack
aws cloudformation delete-stack \
    --stack-name $STACK_NAME \
    --region $REGION

# Wait for stack deletion
echo "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete \
    --stack-name $STACK_NAME \
    --region $REGION

echo "✅ Resources cleaned up successfully!"
```

## Uso de los Scripts

### Orden de Ejecución

1. **Infraestructura Base**:

   ```bash
   ./deploy-infrastructure.sh dev us-east-1
   ```

2. **Configurar VPC Flow Logs**:

   ```bash
   ./setup-vpc-flow-logs.sh vpc-12345678 arn:aws:kinesis:us-east-1:123456789012:stream/vpc-flow-logs-stream
   ```

3. **Desplegar Modelo**:

   ```bash
   python ml/deploy_model.py
   ```

4. **Configurar Monitoreo**:

   ```bash
   python monitoring/create_dashboard.py
   ```

5. **Ejecutar Pruebas**:
   ```bash
   python testing/test_endpoint.py
   ```

### Variables de Entorno

```bash
# .env file
AWS_REGION=us-east-1
ENVIRONMENT=dev
DATA_BUCKET=123456789012-ransomware-detection-data-dev
KINESIS_STREAM=vpc-flow-logs-stream-dev
SNS_TOPIC=arn:aws:sns:us-east-1:123456789012:security-alerts-dev
SAGEMAKER_ENDPOINT=ransomware-detection-endpoint
```

Estos scripts proporcionan una base sólida para implementar y mantener la arquitectura de detección de ransomware en AWS de manera automatizada y reproducible.

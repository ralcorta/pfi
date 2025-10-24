# Sensor Multi-Tenant Application

FastAPI application for multi-tenant ransomware detection using VXLAN traffic mirroring and DynamoDB storage.

## Overview

This application provides:

- **Data-plane**: UDP server listening on port 4789 for VXLAN traffic mirroring
- **Control-plane**: FastAPI REST API for health monitoring and detection queries
- **Multi-tenant support**: Tenant identification via VXLAN VNI
- **Flow analysis**: Packet windowing and feature extraction
- **ML inference**: Configurable model inference hooks
- **DynamoDB storage**: Persistent detection storage with pagination

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AWS Traffic   │    │   Sensor App    │    │   DynamoDB      │
│   Mirroring     │───▶│   (VXLAN/UDP)   │───▶│   Storage       │
│   (VXLAN 4789)  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   FastAPI       │
                       │   Control API   │
                       │   (HTTP 8080)   │
                       └─────────────────┘
```

## Features

### Data Plane

- **VXLAN Decapsulation**: Receives VXLAN packets on UDP port 4789
- **Tenant Identification**: Maps VXLAN VNI to tenant IDs
- **Flow Sessionization**: Groups packets by 5-tuple (src, dst, proto, sport, dport)
- **Temporal Windowing**: Configurable time and packet count windows
- **Feature Extraction**: Calculates packet/byte rates, durations, etc.
- **ML Inference**: Configurable model inference hooks
- **Async Processing**: Multi-worker packet processing

### Control Plane

- **Health Monitoring**: `/healthz` endpoint with queue and flow statistics
- **Statistics**: `/stats` endpoint for runtime metrics
- **Detection Queries**: `/detections/{tenant_id}` with time range filtering
- **Pagination**: Cursor-based pagination for large result sets

## Configuration

### Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
DDB_TABLE=detections

# Network Configuration
VXLAN_PORT=4789
HTTP_PORT=8080

# Performance Configuration
WORKERS=4
QUEUE_MAX=20000

# Window Configuration
WINDOW_SECONDS=3.0
MAX_PKTS_PER_WINDOW=256

# Logging
LOG_LEVEL=info
```

### DynamoDB Schema

```
Table: detections
Primary Key: PK (String), SK (String)

Item Structure:
{
  "PK": "TENANT#<vni>",
  "SK": "FLOW#<src>-<dst>-<proto>-<sport>-<dport>#TS#<timestamp_ms>",
  "srcIp": "192.168.1.100",
  "dstIp": "10.0.0.1",
  "proto": "TCP",
  "srcPort": 80,
  "dstPort": 443,
  "ts": 1640995200000,
  "features": {
    "pkts": 150,
    "bytes": 102400,
    "pps": 50.0,
    "bps": 409600.0,
    "duration": 3.0
  },
  "verdict": "malicious",
  "score": 0.85
}
```

## API Endpoints

### Health Endpoints

#### `GET /healthz`

Returns application health status and configuration.

**Response:**

```json
{
  "status": "ok",
  "udp_port": 4789,
  "http_port": 8080,
  "queue_size": 0,
  "stats": {
    "rx_packets": 1000,
    "rx_errors": 0,
    "enqueued": 1000,
    "dropped_full_queue": 0,
    "handled_packets": 1000,
    "flushed_windows": 50
  },
  "window_params": {
    "WINDOW_SECONDS": 3.0,
    "MAX_PKTS_PER_WINDOW": 256
  }
}
```

#### `GET /stats`

Returns runtime statistics and active flows.

**Response:**

```json
{
  "queue_size": 0,
  "stats": {
    "rx_packets": 1000,
    "rx_errors": 0,
    "enqueued": 1000,
    "dropped_full_queue": 0,
    "handled_packets": 1000,
    "flushed_windows": 50
  },
  "active_flows": 5
}
```

### Detection Endpoints

#### `GET /detections/{tenant_id}`

Query detections for a specific tenant within a time range.

**Parameters:**

- `tenant_id` (path): Tenant identifier (e.g., "TENANT#100")
- `start_ts` (query): Start timestamp in milliseconds
- `end_ts` (query): End timestamp in milliseconds
- `limit` (query): Maximum number of results (1-1000, default: 50)
- `cursor` (query): Pagination cursor (JSON string)

**Response:**

```json
{
  "items": [
    {
      "PK": "TENANT#100",
      "SK": "FLOW#192.168.1.100-10.0.0.1-TCP-80-443#TS#1640995200000",
      "srcIp": "192.168.1.100",
      "dstIp": "10.0.0.1",
      "proto": "TCP",
      "srcPort": 80,
      "dstPort": 443,
      "ts": 1640995200000,
      "verdict": "malicious",
      "score": 0.85
    }
  ],
  "next_cursor": "eyJQSyI6IlRFTkFOVCMxMDAiLCJTSyI6IkZMT1cjMTkyLjE2OC4xLjEwMC0xMC4wLjAuMS1UQ1AtODAtNDQzI1RTIzMTY0MDk5NTIwMDAwMCJ9",
  "count": 1,
  "consumed_capacity": {
    "TableName": "detections",
    "CapacityUnits": 0.5
  }
}
```

## Running the Application

### Using Poetry

```bash
# Install dependencies
poetry install

# Run the application
poetry run sensor-app
```

### Using Python directly

```bash
# From the project root
python -m app.sensor.run
```

### Using uvicorn directly

```bash
uvicorn app.sensor.app:app --host 0.0.0.0 --port 8080
```

### Environment Setup

```bash
# Copy environment template
cp app/sensor/env.example app/sensor/.env

# Edit configuration
nano app/sensor/.env
```

## Development

### Local DynamoDB Setup

```bash
# Start local DynamoDB
docker-compose up -d dynamodb-local

# Initialize tables (local)
python app/sensor/setup.py
```

### AWS DynamoDB Setup

```bash
# Set AWS environment variables
export AWS_DEFAULT_REGION=us-east-1
export DDB_TABLE=detections
# Don't set AWS_ENDPOINT_URL for AWS

# Initialize tables (AWS)
python app/sensor/setup.py

# Alternative: Using Terraform
cd terraform/
terraform init
terraform plan
terraform apply
```

### Testing

```bash
# Test the API
python app/sensor/test_client.py

# Test with curl
curl http://localhost:8080/healthz
curl http://localhost:8080/stats
curl "http://localhost:8080/detections/TENANT%23100?start_ts=1640995200000&end_ts=1640998800000&limit=10"
```

## Customization

### Model Inference Hook

Replace the `model_infer()` function with your ML model:

```python
async def model_infer(tenant: str, fkey: FlowKey, features: Dict[str, float]) -> Dict[str, float]:
    # Your model inference logic here
    # Return: {"score": float, "verdict": str}
    pass
```

### Feature Extraction

Modify `extract_features_from_window()` to extract your specific features:

```python
def extract_features_from_window(win: deque):
    # Your feature extraction logic here
    # Return: Dict[str, float]
    pass
```

### Tenant Mapping

Update `tenant_id_from_vni()` to map VXLAN VNI to tenant IDs:

```python
def tenant_id_from_vni(vni: int) -> str:
    # Your tenant mapping logic here
    # Return: tenant identifier string
    pass
```

## Deployment

### ECS/Fargate

- **NLB**: UDP 4789 → Container
- **ALB**: HTTP 8080 → Container
- **DynamoDB**: Table with appropriate IAM permissions

### Docker

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "-m", "app.sensor.run"]
```

## Monitoring

### Health Checks

- **Liveness**: `GET /healthz` - Application status
- **Readiness**: `GET /stats` - Queue and flow status

### Metrics

- Packet reception rate
- Queue depth
- Processing latency
- Detection accuracy
- DynamoDB consumption

### Alerts

- Queue overflow
- High error rates
- DynamoDB throttling
- Worker failures

## Troubleshooting

### Common Issues

1. **Queue Full**: Increase `QUEUE_MAX` or `WORKERS`
2. **DynamoDB Throttling**: Check table capacity and retry logic
3. **VXLAN Decapsulation Errors**: Verify packet format and VNI
4. **Memory Leaks**: Check window cleanup in janitor task

### Debug Mode

```bash
LOG_LEVEL=debug python -m app.sensor.run
```

### Performance Tuning

- Adjust `WORKERS` based on CPU cores
- Tune `WINDOW_SECONDS` and `MAX_PKTS_PER_WINDOW`
- Monitor DynamoDB capacity consumption
- Use DynamoDB auto-scaling for production

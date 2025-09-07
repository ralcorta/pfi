# Ransomware Detection Sensor - Usage Examples

## Basic Usage

### 1. Live Network Monitoring

```bash
# Monitor all traffic on default interface (en0)
cd app/sensor
poetry run python src/main.py --mode live

# Monitor specific interface
poetry run python src/main.py --mode live --interface eth0

# Monitor with BPF filter (HTTPS traffic only)
poetry run python src/main.py --mode live --interface en0 --filter "tcp port 443"

# Custom detection threshold
poetry run python src/main.py --mode live --threshold 0.85
```

### 2. Offline PCAP Analysis

```bash
# Analyze PCAP file
poetry run python src/main.py --mode pcap --input /path/to/traffic.pcap

# Analyze with custom threshold
poetry run python src/main.py --mode pcap --input /path/to/traffic.pcap --threshold 0.75
```

### 3. Using Makefile Commands

```bash
# From project root
make sensor-install    # Install sensor dependencies
make sensor-live       # Start live monitoring
make sensor-test       # Run test suite
make sensor-config     # Show help/configuration
```

## Advanced Configuration

### 1. Custom Configuration File

Create `configs/custom.yaml`:

```yaml
model:
  path: "../../convlstm_model.keras"
  input_shape: [10, 32, 32, 1]

detection:
  threshold: 0.85
  window_size: 10
  packet_size: 1024

capture:
  interface: "eth0"
  filter: "tcp port 443 or tcp port 80"
  timeout: 2.0
  buffer_size: 2000

alerts:
  stdout: true
  sqs:
    enabled: true
    queue_url: "https://sqs.us-east-1.amazonaws.com/123456789012/ransomware-alerts"
    region: "us-east-1"
  sns:
    enabled: true
    topic_arn: "arn:aws:sns:us-east-1:123456789012:ransomware-alerts"
    region: "us-east-1"

logging:
  level: "DEBUG"
  file: "logs/sensor.log"
  format: "json"
```

Run with custom config:

```bash
poetry run python src/main.py --config configs/custom.yaml --mode live
```

### 2. AWS Integration

#### SQS Setup

```bash
# Create SQS queue
aws sqs create-queue --queue-name ransomware-alerts --region us-east-1

# Get queue URL
aws sqs get-queue-url --queue-name ransomware-alerts --region us-east-1
```

#### SNS Setup

```bash
# Create SNS topic
aws sns create-topic --name ransomware-alerts --region us-east-1

# Subscribe to topic (email example)
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:123456789012:ransomware-alerts --protocol email --notification-endpoint admin@company.com
```

## Performance Tuning

### 1. Memory Optimization

```yaml
performance:
  max_memory_mb: 1000
  gc_interval: 500
  batch_timeout: 3.0
```

### 2. High-Throughput Monitoring

```yaml
capture:
  buffer_size: 5000
  timeout: 0.5

detection:
  window_size: 5 # Smaller windows for faster processing
```

## Troubleshooting

### 1. Permission Issues

```bash
# Run with sudo for live capture
sudo poetry run python src/main.py --mode live --interface eth0

# Or use Docker with privileged mode
docker run --privileged -v $(pwd):/app ransomware-sensor
```

### 2. Model Loading Issues

```bash
# Check model path
ls -la ../../convlstm_model.keras

# Test model loading
poetry run python -c "import tensorflow as tf; tf.keras.models.load_model('../../convlstm_model.keras')"
```

### 3. Network Interface Issues

```bash
# List available interfaces
ip link show

# Test interface access
sudo tcpdump -i eth0 -c 1
```

## Monitoring and Logging

### 1. Log Analysis

```bash
# View real-time logs
tail -f logs/sensor.log

# Filter for detections only
grep "MALICIOUS" logs/sensor.log

# Count detections
grep -c "MALICIOUS" logs/sensor.log
```

### 2. Performance Monitoring

```bash
# Monitor memory usage
ps aux | grep python

# Monitor network traffic
iftop -i eth0
```

## Integration Examples

### 1. Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install poetry && poetry install

CMD ["poetry", "run", "python", "src/main.py", "--mode", "live"]
```

### 2. Systemd Service

```ini
[Unit]
Description=Ransomware Detection Sensor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ransomware-sensor
ExecStart=/usr/bin/poetry run python src/main.py --mode live --interface eth0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ransomware-sensor
spec:
  selector:
    matchLabels:
      app: ransomware-sensor
  template:
    metadata:
      labels:
        app: ransomware-sensor
    spec:
      hostNetwork: true
      containers:
        - name: sensor
          image: ransomware-sensor:latest
          securityContext:
            privileged: true
          command: ["poetry", "run", "python", "src/main.py", "--mode", "live"]
```

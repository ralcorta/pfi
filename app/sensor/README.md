# Ransomware Detection Sensor

Real-time network traffic analysis sensor for ransomware detection using ConvLSTM models.

## Features

- **Real-time packet capture** with BPF filters
- **Offline PCAP analysis** for testing
- **Packet-to-image conversion** (32×32 grayscale)
- **Temporal window processing** (10 packets per inference)
- **Configurable detection thresholds**
- **Multiple alert outputs** (stdout, SQS, SNS)
- **Robust error handling** and signal management
- **Comprehensive logging**

## Installation

```bash
cd app/sensor
poetry install
```

## Usage

### Live Network Monitoring

```bash
# Monitor all traffic on eth0
poetry run python src/main.py --mode live --interface eth0

# Monitor specific traffic with BPF filter
poetry run python src/main.py --mode live --interface eth0 --filter "tcp port 443"

# Custom threshold
poetry run python src/main.py --mode live --interface eth0 --threshold 0.85
```

### Offline PCAP Analysis

```bash
# Analyze PCAP file
poetry run python src/main.py --mode pcap --input /path/to/traffic.pcap

# Batch processing
poetry run python src/main.py --mode pcap --input /path/to/traffic.pcap --batch-size 100
```

### Configuration

Create `configs/sensor.yaml`:

```yaml
model:
  path: "../../models/convlstm_model.keras"
  input_shape: [10, 32, 32, 1]

detection:
  threshold: 0.80
  window_size: 10
  packet_size: 1024

capture:
  interface: "eth0"
  filter: ""
  timeout: 1.0

alerts:
  stdout: true
  sqs:
    enabled: false
    queue_url: ""
  sns:
    enabled: false
    topic_arn: ""

logging:
  level: "INFO"
  file: "logs/sensor.log"
```

## Architecture

```
src/
├── main.py              # CLI entry point
├── core/
│   ├── packet_processor.py    # Packet to image conversion
│   ├── inference_engine.py    # Model inference with temporal windows
│   ├── traffic_capture.py     # Live/offline packet capture
│   └── signal_handler.py      # Signal management
├── utils/
│   ├── config.py        # Configuration management
│   ├── logger.py        # Structured logging
│   └── validators.py    # Input validation
└── alerts/
    ├── stdout.py        # Console alerts
    ├── sqs.py          # AWS SQS alerts
    └── sns.py          # AWS SNS alerts
```

## Requirements

- Python 3.11+
- Root privileges for live packet capture (use `sudo` or `--privileged` flag)
- TensorFlow 2.15+
- Network interface access

## Performance

- **Memory usage**: ~100MB baseline + packet buffers
- **CPU usage**: Depends on traffic volume and model complexity
- **Latency**: <100ms per inference batch
- **Throughput**: Handles up to 10,000 packets/second

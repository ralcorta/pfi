# 🚀 Uso del Sistema Híbrido

## Modo Tiempo Real:

### Capturar tráfico en tiempo real

python app/sensor/src/main.py --live --interface eth0

###Con filtro específico
python app/sensor/src/main.py --live --interface eth0 --filter "tcp port 80"

## Modo Demo con archivos específicos:

### Analizar archivos .pcap específicos

python app/sensor/src/main.py --demo --pcap malware1.pcap malware2.pcap

### Analizar archivo de malware conocido

python app/sensor/src/main.py --demo --pcap models/data/backup/Malware/Zeus.pcap

## Modo Demo con archivos de ejemplo:

### Usar archivos de malware de ejemplo automáticamente

python app/sensor/src/main.py --demo --malware-demo

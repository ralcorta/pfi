import os
import sys
from pathlib import Path
import numpy as np
from scapy.all import rdpcap, TCP, UDP, Raw
from tensorflow.keras.models import load_model

PAYLOAD_LEN = 1024

# Get the project root directory (where this script is located)
PROJECT_ROOT = Path(__file__).parent
MODEL_PATH = PROJECT_ROOT / "models" / "convlstm_model.keras"
PCAP_DIR = PROJECT_ROOT / "models" / "data" / "backup" / "test_malware-traffic-analysis.net-master"

def extract_payloads_from_pcap(pcap_path):
    rows = []
    try:
        packets = rdpcap(pcap_path)
        for pkt in packets:
            if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
                payload_bytes = payload[:PAYLOAD_LEN] + bytes([0] * (PAYLOAD_LEN - len(payload)))
                rows.append(list(payload_bytes))  # ← CORREGIDO
    except Exception as e:
        print(f"Error leyendo {pcap_path}: {e}")
    return rows


def main():
    # Check if paths exist
    if not MODEL_PATH.exists():
        print(f"❌ Model file not found: {MODEL_PATH}")
        sys.exit(1)
    
    if not PCAP_DIR.exists():
        print(f"❌ PCAP directory not found: {PCAP_DIR}")
        sys.exit(1)
    
    print(f"📁 Using model: {MODEL_PATH}")
    print(f"📁 Using PCAP directory: {PCAP_DIR}")
    
    model = load_model(str(MODEL_PATH))

    total_packets = 0
    malware_packets = 0

    for filename in os.listdir(PCAP_DIR):
        if filename.endswith(".pcap"):
            print(f"Procesando {filename}...")
            file_path = PCAP_DIR / filename
            payloads = extract_payloads_from_pcap(str(file_path))

            if not payloads:
                continue

            X = np.array(payloads, dtype=np.uint8) / 255.0
            # Reshape to match model input: (batch_size, 10, 32, 32, 1)
            # Group packets in windows of 10
            num_windows = len(X) // 10
            if num_windows > 0:
                X = X[:num_windows * 10].reshape(num_windows, 10, 32, 32, 1)
            else:
                print(f"   ⚠️ Not enough packets for analysis (need at least 10, got {len(X)})")
                continue

            predictions = model.predict(X, verbose=0)
            y_pred = np.argmax(predictions, axis=1)

            malware_count = np.sum(y_pred)
            benign_count = len(y_pred) - malware_count

            total_packets += len(y_pred)
            malware_packets += malware_count

            print(f"   ➤ {benign_count} benignos, {malware_count} maliciosos\n")

    print("───────────────")
    print(f"Total de paquetes analizados: {total_packets}")
    print(f"Total detectados como malware: {malware_packets}")
    print(f"Porcentaje de malware detectado: {100 * malware_packets / total_packets:.2f}%")

if __name__ == "__main__":
    main()

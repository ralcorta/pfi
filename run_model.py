import os
import numpy as np
from scapy.all import rdpcap, TCP, UDP, Raw
from tensorflow.keras.models import load_model

PAYLOAD_LEN = 1024
MODEL_PATH = "convlstm_model.h5"
PCAP_DIR = "/Users/rodrigo/Documents/uade/tesis/data/backup/test_malware-traffic-analysis.net-master" # input("Ruta de la carpeta con archivos .pcap: ").strip()

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
    model = load_model(MODEL_PATH)

    total_packets = 0
    malware_packets = 0

    for filename in os.listdir(PCAP_DIR):
        if filename.endswith(".pcap"):
            print(f"Procesando {filename}...")
            file_path = os.path.join(PCAP_DIR, filename)
            payloads = extract_payloads_from_pcap(file_path)

            if not payloads:
                continue

            X = np.array(payloads, dtype=np.uint8) / 255.0
            X = X.reshape(-1, 1, 32, 32, 1)

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

import os
import numpy as np
from scapy.all import rdpcap, TCP, UDP, Raw, IP
from collections import defaultdict

PAYLOAD_LEN = 1024
TIME_STEPS = 10

# Agrupa por flujo (5-tuple)
def extract_flows(pcap_path, label):
    flows = defaultdict(list)
    packets = rdpcap(pcap_path)

    for pkt in packets:
        if IP in pkt and (TCP in pkt or UDP in pkt) and Raw in pkt:
            try:
                proto = 'TCP' if TCP in pkt else 'UDP'
                flow_id = (
                    pkt[IP].src,
                    pkt[IP].dst,
                    pkt.sport,
                    pkt.dport,
                    proto
                )
                payload = bytes(pkt[Raw].load)
                padded = payload[:PAYLOAD_LEN] + bytes([0] * (PAYLOAD_LEN - len(payload)))
                flows[flow_id].append(list(padded))
            except Exception as e:
                print(f"Error en {pcap_path}: {e}")
    
    sequences = []
    labels = []
    for seq in flows.values():
        if len(seq) >= TIME_STEPS:
            clip = seq[:TIME_STEPS]  # Solo los primeros N paquetes
            sequences.append(clip)
            labels.append(label)
    return sequences, labels

def generate_sequences(normal_dir, malware_dir, output_npz):
    all_X, all_y = [], []

    def process_dir(directory, label):
        for filename in os.listdir(directory):
            if filename.endswith('.pcap'):
                path = os.path.join(directory, filename)
                print(f"Procesando {'malware' if label else 'benigno'}: {path}")
                X, y = extract_flows(path, label)
                all_X.extend(X)
                all_y.extend(y)

    process_dir(normal_dir, label=0)
    process_dir(malware_dir, label=1)

    X_array = np.array(all_X).reshape(-1, TIME_STEPS, 32, 32, 1) / 255.0
    y_array = np.eye(2)[np.array(all_y)]  # one-hot
    np.savez(output_npz, X=X_array, y=y_array)
    print(f"Dataset guardado en {output_npz} con {len(all_X)} flujos")

if __name__ == '__main__':
    generate_sequences(
        normal_dir='C:/Users/Elias/Desktop/pfi/data/backup/small/Benign/',
        malware_dir='C:/Users/Elias/Desktop/pfi/data/backup/small/Malware/',
        output_npz='C:/Users/Elias/Desktop/pfi/data/flow_dataset.npz'
    )
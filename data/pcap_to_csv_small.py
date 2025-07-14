import os
import pandas as pd
from scapy.all import rdpcap, TCP, UDP, Raw

PAYLOAD_LEN = 1024  # Tamaño fijo (32x32) como en DeepMAL
MIN_PAYLOAD_LEN = 100  # Filtro para evitar paquetes vacíos

def extract_features(pcap_path, label, pcap_name):
    rows = []
    discarded = 0
    packets = rdpcap(pcap_path)

    for pkt in packets:
        if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
            try:
                payload = bytes(pkt[Raw].load)
                payload_len = len(payload)

                if payload_len < MIN_PAYLOAD_LEN:
                    discarded += 1
                    continue  # Saltar paquetes cortos

                src_port = pkt.sport
                dst_port = pkt.dport
                payload_bytes = payload[:PAYLOAD_LEN] + bytes([0] * (PAYLOAD_LEN - len(payload)))
                row = [label, src_port, dst_port, payload_len] + list(payload_bytes) + [pcap_name]
                rows.append(row)
            except Exception as e:
                print(f"⚠️ Error procesando paquete en {pcap_path}: {e}")

    return rows, discarded

def generate_csv(normal_dir, malware_dir, output_csv):
    columns = ['label', 'src_port', 'dst_port', 'payload_len'] + \
              [f'byte_{i}' for i in range(PAYLOAD_LEN)] + ['pcap_name']

    # Crear archivo CSV vacío con encabezado
    with open(output_csv, 'w') as f:
        pd.DataFrame(columns=columns).to_csv(f, index=False)

    total_discarded = 0

    def process_dir(directory, label):
        nonlocal total_discarded
        for filename in os.listdir(directory):
            if filename.endswith('.pcap'):
                path = os.path.join(directory, filename)
                print(f'Procesando {"malware" if label == 1 else "normal"}: {path}')
                rows, discarded = extract_features(path, label, pcap_name=filename)
                total_discarded += discarded
                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    df.to_csv(output_csv, mode='a', header=False, index=False)

    process_dir(normal_dir, label=0)
    process_dir(malware_dir, label=1)

    print(f'\n✅ CSV final guardado en: {output_csv}')
    print(f'🧹 Total de paquetes descartados por payload corto (<{MIN_PAYLOAD_LEN} bytes): {total_discarded}')

if __name__ == '__main__':
    normal_dir = 'C:/Users/Elias/Desktop/pfi/data/backup/full/Benign/'
    malware_dir = 'C:/Users/Elias/Desktop/pfi/data/backup/full/Malware/'
    output_csv = 'C:/Users/Elias/Desktop/pfi/data/traffic_dataset_full.csv'

    generate_csv(normal_dir, malware_dir, output_csv)
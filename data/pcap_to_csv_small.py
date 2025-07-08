import os
import pandas as pd
from scapy.all import rdpcap, TCP, UDP, Raw

PAYLOAD_LEN = 1024  # número fijo según DeepMAL

def extract_features(pcap_path, label):
    rows = []
    packets = rdpcap(pcap_path)

    for pkt in packets:
        if (pkt.haslayer(TCP) or pkt.haslayer(UDP)) and pkt.haslayer(Raw):
            try:
                src_port = pkt.sport
                dst_port = pkt.dport
                payload = bytes(pkt[Raw].load)
                payload_len = len(payload)
                payload_bytes = payload[:PAYLOAD_LEN] + bytes([0] * (PAYLOAD_LEN - len(payload)))
                row = [label, src_port, dst_port, payload_len] + list(payload_bytes)
                rows.append(row)
            except Exception as e:
                print(f"Error procesando paquete en {pcap_path}: {e}")
    return rows

def generate_csv(normal_dir, malware_dir, output_csv):
    columns = ['label', 'src_port', 'dst_port', 'payload_len'] + [f'byte_{i}' for i in range(PAYLOAD_LEN)]

    # Crear archivo CSV vacío con encabezados
    with open(output_csv, 'w') as f:
        pd.DataFrame(columns=columns).to_csv(f, index=False)

    # Función auxiliar para procesar un directorio
    def process_dir(directory, label):
        for filename in os.listdir(directory):
            if filename.endswith('.pcap'):
                path = os.path.join(directory, filename)
                print(f'Procesando {"malware" if label == 1 else "normal"}: {path}')
                rows = extract_features(path, label)
                if rows:
                    df = pd.DataFrame(rows, columns=columns)
                    df.to_csv(output_csv, mode='a', header=False, index=False)
                break

    # Procesar carpetas
    process_dir(normal_dir, label=0)
    process_dir(malware_dir, label=1)

    print(f'\nCSV final guardado en: {output_csv}')

if __name__ == '__main__':
    # Rutas en tu Mac (ajústalas a tu estructura real)
    normal_dir = 'C:/Users/Elias/Desktop/pfi/data/backup/small/Benign/'
    malware_dir = 'C:/Users/Elias/Desktop/pfi/data/backup/small/Malware/'
    output_csv = 'C:/Users/Elias/Desktop/pfi/data/traffic_dataset_small.csv'

    generate_csv(normal_dir, malware_dir, output_csv)

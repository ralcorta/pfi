import pandas as pd
import numpy as np
from tensorflow.keras.utils import to_categorical
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ───────────────────────────────────────────────
# 1. Configuración
# ───────────────────────────────────────────────
from pathlib import Path

CSV_TYPE = '_full'
PAYLOAD_LEN = 1024

USE_PCAP_LIMIT = False
MAX_ROWS_PER_PCAP = 100000
SEQUENCE_LENGTH = 20

# Resuelve siempre desde la raíz del repo (PFI/)
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]   # detection → training → models → PFI
CSV_PATH = PROJECT_ROOT / 'data' / f'traffic_dataset{CSV_TYPE}.csv'

# (fallback por si movés el script de carpeta)
if not CSV_PATH.exists():
    alt = HERE.parents[2] / 'data' / f'traffic_dataset{CSV_TYPE}.csv'
    if alt.exists():
        CSV_PATH = alt

print(f"📄 CSV_PATH = {CSV_PATH}")

# ───────────────────────────────────────────────
# 2. Funciones para features específicas de ransomware
# ───────────────────────────────────────────────
def extract_ransomware_features(df_group):
    """Extrae features enriquecidas para detección de ransomware"""
    features = {}
    
    payload_cols = [f'byte_{i}' for i in range(PAYLOAD_LEN)]
    payloads = df_group[payload_cols].values

    # --- Entropía de Shannon ---
    entropies = []
    for payload in payloads:
        unique, counts = np.unique(payload, return_counts=True)
        probs = counts / len(payload)
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        entropies.append(entropy)
    features['entropy_mean'] = float(np.mean(entropies))
    features['entropy_std']  = float(np.std(entropies))
    features['entropy_max']  = float(np.max(entropies))

    # --- Tamaño de paquetes ---
    payload_lens = df_group['payload_len'].values
    features['packet_size_mean']  = float(np.mean(payload_lens))
    features['packet_size_std']   = float(np.std(payload_lens))
    features['packet_size_ratio'] = float(np.std(payload_lens) / (np.mean(payload_lens) + 1e-10))

    # --- Puertos únicos ---
    src_ports = df_group['src_port'].values
    dst_ports = df_group['dst_port'].values
    features['unique_src_ports'] = int(len(np.unique(src_ports)))
    features['unique_dst_ports'] = int(len(np.unique(dst_ports)))
    features['port_diversity']   = int(len(np.unique(np.concatenate([src_ports, dst_ports]))))

    # --- Puertos de ransomware comunes ---
    ransomware_ports = [445, 139, 135, 3389, 5985, 5986]
    features['ransomware_port_usage'] = int(sum(1 for port in dst_ports if port in ransomware_ports))

    # --- Variabilidad temporal / interarrival ---
    if 'timestamp' in df_group.columns and len(df_group) >= 2:
        ts = df_group['timestamp'].values.astype(float)
        dt = np.diff(np.sort(ts))
        features['interarrival_mean'] = float(np.mean(dt)) if dt.size else 0.0
        features['interarrival_std']  = float(np.std(dt))  if dt.size else 0.0
        duration = ts.max() - ts.min()
        features['pps'] = float(len(ts) / (duration + 1e-6))
    else:
        features['interarrival_mean'] = 0.0
        features['interarrival_std']  = 0.0
        features['pps'] = 0.0

    # --- Top-3 puertos destino ---
    unique_dst, counts_dst = np.unique(dst_ports, return_counts=True)
    total = counts_dst.sum() + 1e-6
    top_idx = np.argsort(counts_dst)[::-1][:3]
    for rank, i in enumerate(top_idx, start=1):
        features[f'top{rank}_dst_port']  = int(unique_dst[i]) if i < unique_dst.size else -1
        features[f'top{rank}_dst_rate']  = float(counts_dst[i] / total) if i < counts_dst.size else 0.0

    # --- Ratio de protocolos ---
    if 'proto' in df_group.columns:
        protos = df_group['proto'].values
        features['tcp_ratio'] = float(np.mean(protos == 'TCP'))
        features['udp_ratio'] = float(np.mean(protos == 'UDP'))
    else:
        features['tcp_ratio'] = 0.0
        features['udp_ratio'] = 0.0

    # --- Ratios de flags TCP ---
    if 'tcp_flags' in df_group.columns and (df_group['tcp_flags'] != 0).any():
        flags = df_group['tcp_flags'].astype(int).values
        features['syn_rate'] = float(np.mean((flags & 0x02) != 0))
        features['ack_rate'] = float(np.mean((flags & 0x10) != 0))
    else:
        features['syn_rate'] = 0.0
        features['ack_rate'] = 0.0

    # --- Variabilidad en payloads ---
    features['payload_variance'] = float(np.var(payloads.flatten()))

    # --- Bytes nulos ---
    null_bytes = np.sum(payloads == 0, axis=1)
    features['null_bytes_mean']  = float(np.mean(null_bytes))
    features['null_bytes_ratio'] = float(np.mean(null_bytes) / PAYLOAD_LEN)

    # --- NUEVO: Dinámica por puerto destino (lo que pidió tu compañero) ---
    if 'timestamp' in df_group.columns:
        ts = df_group['timestamp'].values.astype(float)
        dp = df_group['dst_port'].values.astype(int)

        # a) cambio de puerto entre paquetes consecutivos (churn)
        features['port_churn_rate'] = float(np.mean(dp[1:] != dp[:-1])) if dp.size > 1 else 0.0

        # b) share del puerto dominante (qué % de hits va al puerto Top-1)
        vals, cnts = np.unique(dp, return_counts=True)
        if cnts.size:
            dom_share = float(cnts.max() / (cnts.sum() + 1e-12))
            features['dominant_port_share'] = dom_share

            # c) índice de concentración (Herfindahl) sobre dst_port
            p = cnts / (cnts.sum() + 1e-12)
            features['dst_port_herfindahl'] = float(np.sum(p**2))

            # d) tiempo entre hits al puerto dominante
            top_port = int(vals[np.argmax(cnts)])
            ts_top = np.sort(ts[dp == top_port])
            if ts_top.size >= 2:
                diffs = np.diff(ts_top)
                features['top_port_interhit_mean'] = float(np.mean(diffs))
                features['top_port_interhit_std']  = float(np.std(diffs))
            else:
                features['top_port_interhit_mean'] = 0.0
                features['top_port_interhit_std']  = 0.0
        else:
            features['dominant_port_share']   = 0.0
            features['dst_port_herfindahl']   = 0.0
            features['top_port_interhit_mean'] = 0.0
            features['top_port_interhit_std']  = 0.0
    else:
        features['port_churn_rate']        = 0.0
        features['dominant_port_share']    = 0.0
        features['dst_port_herfindahl']    = 0.0
        features['top_port_interhit_mean'] = 0.0
        features['top_port_interhit_std']  = 0.0

    return features

# ───────────────────────────────────────────────
# 3. Cargar CSV
# ───────────────────────────────────────────────
print("Cargando CSV...")
df = pd.read_csv(CSV_PATH)
print(f"Total muestras antes del filtro: {len(df)}")

if 'pcap_name' in df.columns and USE_PCAP_LIMIT:
    df = df.groupby('pcap_name').head(MAX_ROWS_PER_PCAP).reset_index(drop=True)
    print(f"Muestras después del filtro por archivo: {len(df)}")
elif 'pcap_name' in df.columns:
    print("✅ Usando todas las muestras disponibles")
else:
    print("⚠️ No se encontró la columna 'pcap_name'")

# ───────────────────────────────────────────────
# 4. Preparar X e y agrupando en secuencias
# ───────────────────────────────────────────────
print("Procesando datos y extrayendo features...")

if 'pcap_name' in df.columns:
    grouped_data = []
    ransomware_features = []

    for pcap_name, group in df.groupby('pcap_name'):
        group = group.reset_index(drop=True)
        usable_len = (len(group) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
        if usable_len < SEQUENCE_LENGTH:
            continue
        group = group.iloc[:usable_len]

        # Features por secuencia
        for i in range(0, len(group), SEQUENCE_LENGTH):
            seq = group.iloc[i:i+SEQUENCE_LENGTH]
            ransomware_features.append(extract_ransomware_features(seq))

        # Payload
        X_group = group[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
        y_group = group['label'].values
        X_group = X_group.reshape(-1, SEQUENCE_LENGTH, PAYLOAD_LEN)
        y_group = y_group.reshape(-1, SEQUENCE_LENGTH)
        grouped_data.append((X_group, y_group))

    X_sequences = np.vstack([d[0] for d in grouped_data])
    y_sequences = np.vstack([d[1] for d in grouped_data])

    feature_names = list(ransomware_features[0].keys())
    X_ransomware_features = np.array([[f[name] for name in feature_names] for f in ransomware_features])

    print(f"Features de ransomware extraídas: {len(feature_names)}")
else:
    # fallback
    X_raw = df[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
    y_raw = df['label'].values
    usable_len = (len(X_raw) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
    X_raw = X_raw[:usable_len]
    y_raw = y_raw[:usable_len]
    X_sequences = X_raw.reshape(-1, SEQUENCE_LENGTH, PAYLOAD_LEN)
    y_sequences = y_raw.reshape(-1, SEQUENCE_LENGTH)
    X_ransomware_features = np.zeros((len(X_sequences), 10))
    feature_names = [f'feat_{i}' for i in range(10)]

# Escalado + reshape a (32x32)
X_scaled = X_sequences / 255.0
X = X_scaled.reshape(-1, SEQUENCE_LENGTH, 32, 32, 1)

# Etiquetas: mayoría por secuencia
y_majority = [np.bincount(block).argmax() for block in y_sequences]
y_cat = to_categorical(y_majority, num_classes=2)

# Grupos por PCAP
groups = []
for i, (_, group) in enumerate(df.groupby('pcap_name')):
    groups.extend([i] * len(group))
groups = groups[:len(y_majority)]

print(f"Secuencias procesadas: {X.shape[0]}")
print(f"Longitud de secuencia: {SEQUENCE_LENGTH}")
print(f"Features de ransomware: {X_ransomware_features.shape}")

# ───────────────────────────────────────────────
# 5. Guardar
# ───────────────────────────────────────────────
np.save('X.npy', X)
np.save('y_cat.npy', y_cat)
np.save('X_ransomware_features.npy', X_ransomware_features)
np.save('groups.npy', np.array(groups))

with open('ransomware_feature_names.txt', 'w') as f:
    for name in feature_names:
        f.write(f"{name}\n")

print("✅ Datos guardados:")
print(f"   - X.npy: {X.shape}")
print(f"   - y_cat.npy: {y_cat.shape}")
print(f"   - X_ransomware_features.npy: {X_ransomware_features.shape}")
print(f"   - groups.npy: {len(groups)} grupos")
print(f"   - ransomware_feature_names.txt: {len(feature_names)} features")

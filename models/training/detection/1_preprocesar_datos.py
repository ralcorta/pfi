import pandas as pd
import numpy as np
from tensorflow.keras.utils import to_categorical
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ───────────────────────────────────────────────
# 1. Configuración
# ───────────────────────────────────────────────
CSV_TYPE = '_full'
PAYLOAD_LEN = 1024
MAX_ROWS_PER_PCAP = 1000
SEQUENCE_LENGTH = 20  # Aumentado de 10 a 20 para capturar mejor patrones de ransomware
CSV_PATH = f'../../data/traffic_dataset{CSV_TYPE}.csv'

# ───────────────────────────────────────────────
# 2. Funciones para features específicas de ransomware
# ───────────────────────────────────────────────
def extract_ransomware_features(df_group):
    """Extrae features específicas para detección de ransomware"""
    features = {}
    
    # 1. Estadísticas de payload
    payload_cols = [f'byte_{i}' for i in range(PAYLOAD_LEN)]
    payloads = df_group[payload_cols].values
    
    # Entropía de Shannon (indicador de encriptación)
    entropies = []
    for payload in payloads:
        # Calcular entropía de Shannon
        unique, counts = np.unique(payload, return_counts=True)
        probabilities = counts / len(payload)
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        entropies.append(entropy)
    
    features['entropy_mean'] = np.mean(entropies)
    features['entropy_std'] = np.std(entropies)
    features['entropy_max'] = np.max(entropies)
    
    # 2. Patrones de tamaño de paquetes
    payload_lens = df_group['payload_len'].values
    features['packet_size_mean'] = np.mean(payload_lens)
    features['packet_size_std'] = np.std(payload_lens)
    features['packet_size_ratio'] = np.std(payload_lens) / (np.mean(payload_lens) + 1e-10)
    
    # 3. Frecuencia de conexiones (puertos únicos)
    src_ports = df_group['src_port'].values
    dst_ports = df_group['dst_port'].values
    features['unique_src_ports'] = len(np.unique(src_ports))
    features['unique_dst_ports'] = len(np.unique(dst_ports))
    features['port_diversity'] = len(np.unique(np.concatenate([src_ports, dst_ports])))
    
    # 4. Patrones de comunicación (puertos comunes de ransomware)
    ransomware_ports = [445, 139, 135, 3389, 5985, 5986]  # SMB, RDP, WinRM
    features['ransomware_port_usage'] = sum(1 for port in dst_ports if port in ransomware_ports)
    
    # 5. Variabilidad temporal (simulada por orden de paquetes)
    features['payload_variance'] = np.var(payloads.flatten())
    
    # 6. Patrones de bytes nulos (común en ransomware)
    null_bytes = np.sum(payloads == 0, axis=1)
    features['null_bytes_mean'] = np.mean(null_bytes)
    features['null_bytes_ratio'] = np.mean(null_bytes) / PAYLOAD_LEN
    
    return features

# ───────────────────────────────────────────────
# 3. Cargar CSV y aplicar límite por pcap
# ───────────────────────────────────────────────
print("Cargando CSV...")
df = pd.read_csv(CSV_PATH)
print(f"Total muestras antes del filtro: {len(df)}")

if 'pcap_name' in df.columns:
    df = df.groupby('pcap_name').head(MAX_ROWS_PER_PCAP).reset_index(drop=True)
    print(f"Muestras después del filtro por archivo: {len(df)}")
else:
    print("⚠️ No se encontró la columna 'pcap_name'")

# ───────────────────────────────────────────────
# 4. Preparar X e y agrupando en bloques de SEQUENCE_LENGTH
# ───────────────────────────────────────────────
print("Procesando datos y extrayendo features de ransomware...")

# Agrupar por pcap_name para mantener secuencias coherentes
if 'pcap_name' in df.columns:
    grouped_data = []
    ransomware_features = []
    
    for pcap_name, group in df.groupby('pcap_name'):
        group = group.reset_index(drop=True)
        
        # Cortar a múltiplo de SEQUENCE_LENGTH
        usable_len = (len(group) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
        if usable_len < SEQUENCE_LENGTH:
            continue
            
        group = group.iloc[:usable_len]
        
        # Extraer features de ransomware para cada secuencia
        for i in range(0, len(group), SEQUENCE_LENGTH):
            sequence = group.iloc[i:i+SEQUENCE_LENGTH]
            features = extract_ransomware_features(sequence)
            ransomware_features.append(features)
        
        # Agregar datos de payload
        X_group = group[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
        y_group = group['label'].values
        
        # Reshape a secuencias
        X_group = X_group.reshape(-1, SEQUENCE_LENGTH, PAYLOAD_LEN)
        y_group = y_group.reshape(-1, SEQUENCE_LENGTH)
        
        grouped_data.append((X_group, y_group))
    
    # Combinar todos los datos
    X_sequences = np.vstack([data[0] for data in grouped_data])
    y_sequences = np.vstack([data[1] for data in grouped_data])
    
    # Convertir features de ransomware a array
    feature_names = list(ransomware_features[0].keys())
    X_ransomware_features = np.array([[features[name] for name in feature_names] 
                                     for features in ransomware_features])
    
    print(f"Features de ransomware extraídas: {len(feature_names)}")
    print(f"Feature names: {feature_names}")
    
else:
    # Fallback al método original si no hay pcap_name
    X_raw = df[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
    y_raw = df['label'].values
    
    usable_len = (len(X_raw) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
    X_raw = X_raw[:usable_len]
    y_raw = y_raw[:usable_len]
    
    X_sequences = X_raw.reshape(-1, SEQUENCE_LENGTH, PAYLOAD_LEN)
    y_sequences = y_raw.reshape(-1, SEQUENCE_LENGTH)
    
    # Features básicas si no hay agrupación por pcap
    X_ransomware_features = np.zeros((len(X_sequences), 10))  # 10 features básicas
    feature_names = [
        'entropy_mean', 'entropy_std', 'entropy_max',
        'packet_size_mean', 'packet_size_std', 'packet_size_ratio',
        'unique_src_ports', 'unique_dst_ports', 'port_diversity',
        'ransomware_port_usage', 'payload_variance', 'null_bytes_mean', 'null_bytes_ratio'
    ][:10]  # Tomar solo las primeras 10

# Escalado de payloads
X_scaled = X_sequences / 255.0

# Reshape a formato CNN (32x32)
X = X_scaled.reshape(-1, SEQUENCE_LENGTH, 32, 32, 1)

# Agrupar etiquetas: mayoría por cada secuencia
y_majority = [np.bincount(block).argmax() for block in y_sequences]
y_cat = to_categorical(y_majority, num_classes=2)

print(f"Secuencias procesadas: {X.shape[0]}")
print(f"Longitud de secuencia: {SEQUENCE_LENGTH}")
print(f"Features de ransomware: {X_ransomware_features.shape}")

# ───────────────────────────────────────────────
# 5. Guardar datos procesados
# ───────────────────────────────────────────────
np.save('X.npy', X)
np.save('y_cat.npy', y_cat)
np.save('X_ransomware_features.npy', X_ransomware_features)

# Guardar nombres de features para referencia
with open('ransomware_feature_names.txt', 'w') as f:
    for name in feature_names:
        f.write(f"{name}\n")

print(f"✅ Datos guardados:")
print(f"   - X.npy: {X.shape} (secuencias de payload)")
print(f"   - y_cat.npy: {y_cat.shape} (etiquetas)")
print(f"   - X_ransomware_features.npy: {X_ransomware_features.shape} (features específicas)")
print(f"   - ransomware_feature_names.txt: {len(feature_names)} features")
print(f"   - Longitud de secuencia: {SEQUENCE_LENGTH} paquetes")
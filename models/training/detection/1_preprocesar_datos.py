# 1_preprocesar_datos.py  ← PASO 1 (robusto, con streaming por chunks)
import pandas as pd
import numpy as np
from tensorflow.keras.utils import to_categorical
from pathlib import Path
import sys
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

# ───────────────────────────────────────────────
# 1) Configuración y paths robustos
# ───────────────────────────────────────────────
CSV_TYPE = '_full'
PAYLOAD_LEN = 1024
USE_PCAP_LIMIT = False
MAX_ROWS_PER_PCAP = 100000
SEQUENCE_LENGTH = 20

# streaming
CHUNK_SIZE = 100_000   # ajustá según tu RAM
FORCE_CHUNKS = False   # ponelo True si querés forzar el modo streaming

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
CSV_PATH = PROJECT_ROOT / 'data' / f'traffic_dataset{CSV_TYPE}.csv'

print(f"📁 SCRIPT_DIR:   {SCRIPT_DIR}")
print(f"📁 PROJECT_ROOT: {PROJECT_ROOT}")
print(f"📄 CSV_PATH:     {CSV_PATH}")

if not CSV_PATH.exists():
    alt1 = Path.cwd() / 'data' / f'traffic_dataset{CSV_TYPE}.csv'
    alt2 = Path.cwd().parent / 'data' / f'traffic_dataset{CSV_TYPE}.csv'
    print("⚠️ No encuentro el CSV en la ruta principal. Pruebo alternativas:")
    print(f"   - {alt1}\n   - {alt2}")
    if alt1.exists():
        CSV_PATH = alt1
    elif alt2.exists():
        CSV_PATH = alt2
    else:
        print("❌ No se encontró el CSV. Verificá que el generador lo haya creado en pfi/data/")
        print(r"   Podés setear manualmente: CSV_PATH = Path(r'C:\Users\Elias\Desktop\pfi\data\traffic_dataset_full.csv')")
        sys.exit(1)

# ───────────────────────────────────────────────
# 2) Funciones de features por secuencia
# ───────────────────────────────────────────────
def shannon_entropy_uint8_row(payload_uint8: np.ndarray) -> float:
    counts = np.bincount(payload_uint8, minlength=256).astype(np.float64)
    total = counts.sum()
    if total <= 0:
        return 0.0
    probs = counts / total
    return float(-np.sum(probs * np.log2(probs + 1e-12)))

def extract_ransomware_features(df_group: pd.DataFrame) -> dict:
    feats = {}
    payload_cols = [f'byte_{i}' for i in range(PAYLOAD_LEN)]
    payloads = df_group[payload_cols].to_numpy(dtype=np.uint8, copy=False)  # (T, 1024)

    entropies = [shannon_entropy_uint8_row(row) for row in payloads]
    feats['entropy_mean'] = float(np.mean(entropies))
    feats['entropy_std']  = float(np.std(entropies))
    feats['entropy_max']  = float(np.max(entropies))

    feats['payload_variance'] = float(np.var(payloads))

    null_bytes = (payloads == 0).sum(axis=1).astype(np.float32)
    feats['null_bytes_mean']  = float(np.mean(null_bytes))
    feats['null_bytes_ratio'] = float(np.mean(null_bytes) / PAYLOAD_LEN)

    if 'payload_len' in df_group.columns:
        lens = df_group['payload_len'].to_numpy(dtype=np.float32, copy=False)
    else:
        lens = (payloads != 0).sum(axis=1).astype(np.float32)
    feats['packet_size_mean']  = float(np.mean(lens))
    feats['packet_size_std']   = float(np.std(lens))
    feats['packet_size_ratio'] = float(np.std(lens) / (np.mean(lens) + 1e-10))

    ransomware_ports = {445, 139, 135, 3389, 5985, 5986}
    if 'src_port' in df_group.columns:
        src_ports = df_group['src_port'].to_numpy(copy=False)
        feats['unique_src_ports'] = int(len(np.unique(src_ports)))
    else:
        src_ports = np.array([], dtype=int)
        feats['unique_src_ports'] = 0

    if 'dst_port' in df_group.columns:
        dst_ports = df_group['dst_port'].to_numpy(copy=False)
        feats['unique_dst_ports'] = int(len(np.unique(dst_ports)))
        feats['port_diversity']   = int(len(np.unique(np.concatenate([src_ports, dst_ports])))) \
                                    if src_ports.size else int(len(np.unique(dst_ports)))
        feats['ransomware_port_usage'] = int(np.sum(np.isin(dst_ports, list(ransomware_ports))))
    else:
        feats['unique_dst_ports'] = 0
        feats['port_diversity']   = feats['unique_src_ports']
        feats['ransomware_port_usage'] = 0
    return feats

# ───────────────────────────────────────────────
# 3) Esquema de columnas + dtypes compactos
# ───────────────────────────────────────────────
payload_cols = [f'byte_{i}' for i in range(PAYLOAD_LEN)]
usecols = ['label', 'src_port', 'dst_port', 'payload_len', *payload_cols, 'pcap_name']

dtype_map = {
    'label': 'uint8',
    'src_port': 'uint16',
    'dst_port': 'uint16',
    'payload_len': 'uint16',
    'pcap_name': 'category',
}
for c in payload_cols:
    dtype_map[c] = 'uint8'

# ───────────────────────────────────────────────
# 4) Lectura del CSV: pyarrow → sino, streaming por chunks
# ───────────────────────────────────────────────
def process_fully_in_memory() -> pd.DataFrame | None:
    """Intenta leer el CSV completo si hay pyarrow; si no, devuelve None."""
    try:
        print("Intentando lectura completa con engine='pyarrow'…")
        df = pd.read_csv(
            CSV_PATH,
            engine='pyarrow',
            dtype=dtype_map,
            usecols=usecols,
        )
        print("✅ Leído con engine='pyarrow'")
        return df
    except Exception as e:
        print(f"⚠️ No se pudo usar pyarrow ({e}).")
        return None

def process_streaming_chunks():
    """Lee por chunks y arma secuencias + features sin cargar todo a RAM."""
    print(f"⏳ Modo streaming: leyendo por chunks de {CHUNK_SIZE} filas…")
    # Buffers por pcap
    buffers = {}          # pcap_name -> DataFrame
    all_X_seq = []        # lista de (1,T,1024)
    all_y_seq = []        # lista de (1,T)
    ransomware_feats = [] # lista de dicts
    pcap_seq_groups = []  # lista de ids de grupo por secuencia
    pcap_id_map = {}      # pcap_name -> int
    next_pcap_id = 0

    def flush_pcap_sequences(pcap_name, df_buf):
        nonlocal next_pcap_id
        if len(df_buf) < SEQUENCE_LENGTH:
            return df_buf  # todavía no alcanza para una secuencia

        usable_len = (len(df_buf) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
        work = df_buf.iloc[:usable_len].reset_index(drop=True)

        # asignar id estable
        if pcap_name not in pcap_id_map:
            pcap_id_map[pcap_name] = next_pcap_id
            next_pcap_id += 1
        pid = pcap_id_map[pcap_name]

        for start in range(0, usable_len, SEQUENCE_LENGTH):
            seq = work.iloc[start:start+SEQUENCE_LENGTH]
            feats = extract_ransomware_features(seq)
            ransomware_feats.append(feats)

            X_block = seq[payload_cols].to_numpy(dtype=np.uint8, copy=False)
            y_block = seq['label'].to_numpy(dtype=int, copy=False)

            all_X_seq.append(X_block.reshape(1, SEQUENCE_LENGTH, PAYLOAD_LEN))
            all_y_seq.append(y_block.reshape(1, SEQUENCE_LENGTH))
            pcap_seq_groups.append(pid)

        # devolver remanente < SEQUENCE_LENGTH (si lo hay)
        return df_buf.iloc[usable_len:].reset_index(drop=True)

    # Leer por trozos
    reader = pd.read_csv(
        CSV_PATH,
        engine='c',
        dtype=dtype_map,
        usecols=usecols,
        chunksize=CHUNK_SIZE,
        low_memory=False
    )

    total_rows = 0
    for chunk in reader:
        total_rows += len(chunk)
        # (opcional) limitar por PCAP si quisieras en streaming
        if USE_PCAP_LIMIT and 'pcap_name' in chunk.columns:
            chunk = chunk.groupby('pcap_name', group_keys=False).head(MAX_ROWS_PER_PCAP)

        # acumular por pcap_name
        for pcap_name, g in chunk.groupby('pcap_name', sort=False):
            if pcap_name not in buffers:
                buffers[pcap_name] = g.copy()
            else:
                buffers[pcap_name] = pd.concat([buffers[pcap_name], g], ignore_index=True)
            # flush si ya puedo formar secuencias
            buffers[pcap_name] = flush_pcap_sequences(pcap_name, buffers[pcap_name])

        print(f"  • Procesadas {total_rows:,} filas…", end='\r')

    # flush final por si quedó remanente que alcance
    for pcap_name in list(buffers.keys()):
        buffers[pcap_name] = flush_pcap_sequences(pcap_name, buffers[pcap_name])

    if not all_X_seq:
        raise RuntimeError("No se obtuvieron secuencias suficientes en streaming. Revisa SEQUENCE_LENGTH o dataset.")

    X_sequences = np.vstack(all_X_seq)   # (N, T, 1024)
    y_sequences = np.vstack(all_y_seq)   # (N, T)

    feature_names = list(ransomware_feats[0].keys())
    X_ransomware_features = np.array(
        [[fe[name] for name in feature_names] for fe in ransomware_feats],
        dtype=np.float32
    )

    groups = np.asarray(pcap_seq_groups, dtype=int)
    print(f"\n✅ Streaming completado. Secuencias: {len(X_sequences)} | PCAPs únicos: {len(np.unique(groups))}")
    return X_sequences, y_sequences, X_ransomware_features, feature_names, groups

# ───────────────────────────────────────────────
# 5) Pipeline principal: in-memory (si hay) o streaming
# ───────────────────────────────────────────────
has_pcap = True  # nuestro CSV la trae; si no, lo detectamos luego
X_sequences = y_sequences = X_ransomware_features = feature_names = groups = None

if not FORCE_CHUNKS:
    df_full = process_fully_in_memory()
else:
    df_full = None

if df_full is not None:
    # ——— Ruta “memoria completa” (pyarrow) ———
    print(f"Total muestras antes del filtro: {len(df_full)}")
    has_pcap = 'pcap_name' in df_full.columns

    if has_pcap and USE_PCAP_LIMIT:
        print(f"Aplicando límite de {MAX_ROWS_PER_PCAP} filas por PCAP…")
        df_full = df_full.groupby('pcap_name', group_keys=False).head(MAX_ROWS_PER_PCAP).reset_index(drop=True)

    print("Procesando datos y extrayendo features por secuencia (memoria completa)…")
    all_X_seq, all_y_seq, ransomware_features, pcap_seq_groups = [], [], [], []

    for pcap_id, (pcap_name, g) in enumerate(df_full.groupby('pcap_name', sort=False)):
        g = g.reset_index(drop=True)
        usable_len = (len(g) // SEQUENCE_LENGTH) * SEQUENCE_LENGTH
        if usable_len < SEQUENCE_LENGTH:
            continue
        g = g.iloc[:usable_len]
        for start in range(0, usable_len, SEQUENCE_LENGTH):
            seq = g.iloc[start:start+SEQUENCE_LENGTH]
            feats = extract_ransomware_features(seq)
            ransomware_features.append(feats)

            X_block = seq[payload_cols].to_numpy(dtype=np.uint8, copy=False)
            y_block = seq['label'].to_numpy(dtype=int, copy=False)
            all_X_seq.append(X_block.reshape(1, SEQUENCE_LENGTH, PAYLOAD_LEN))
            all_y_seq.append(y_block.reshape(1, SEQUENCE_LENGTH))
            pcap_seq_groups.append(pcap_id)

    if not all_X_seq:
        raise RuntimeError("No se obtuvieron secuencias suficientes. Revisa SEQUENCE_LENGTH o dataset.")

    X_sequences = np.vstack(all_X_seq)
    y_sequences = np.vstack(all_y_seq)
    feature_names = list(ransomware_features[0].keys())
    X_ransomware_features = np.array(
        [[fe[name] for name in feature_names] for fe in ransomware_features],
        dtype=np.float32
    )
    groups = np.asarray(pcap_seq_groups, dtype=int)

else:
    # ——— Ruta “streaming por chunks” ———
    X_sequences, y_sequences, X_ransomware_features, feature_names, groups = process_streaming_chunks()

# ───────────────────────────────────────────────
# 6) Escalado, reshape a 32×32 y etiquetas por mayoría
# ───────────────────────────────────────────────
X_scaled = X_sequences.astype(np.float32) / 255.0
X = X_scaled.reshape(-1, SEQUENCE_LENGTH, 32, 32, 1)

y_majority = np.array([np.bincount(block).argmax() for block in y_sequences], dtype=int)
y_cat = to_categorical(y_majority, num_classes=2)

assert len(X) == len(y_cat) == len(groups) == len(X_ransomware_features), \
    f"Desalineado: X={len(X)}, y={len(y_cat)}, groups={len(groups)}, feats={len(X_ransomware_features)}"

print(f"Secuencias procesadas: {X.shape[0]}")
print(f"Longitud de secuencia: {SEQUENCE_LENGTH}")
print(f"Features de ransomware: {X_ransomware_features.shape}")
print(f"PCAPs únicos (groups): {len(np.unique(groups))}")

# ───────────────────────────────────────────────
# 7) Guardar a disco
# ───────────────────────────────────────────────
np.save('X.npy', X)
np.save('y_cat.npy', y_cat)
np.save('X_ransomware_features.npy', X_ransomware_features.astype(np.float32, copy=False))
np.save('groups.npy', groups)

with open('ransomware_feature_names.txt', 'w', encoding='utf-8') as f:
    for name in feature_names:
        f.write(f"{name}\n")

print("✅ Datos guardados:")
print(f"   - X.npy: {X.shape} (secuencias 20×32×32×1)")
print(f"   - y_cat.npy: {y_cat.shape} (one-hot)")
print(f"   - X_ransomware_features.npy: {X_ransomware_features.shape}")
print(f"   - groups.npy: {groups.shape}")
print(f"   - ransomware_feature_names.txt: {len(feature_names)} nombres")
print(f"   - SEQUENCE_LENGTH: {SEQUENCE_LENGTH} paquetes")
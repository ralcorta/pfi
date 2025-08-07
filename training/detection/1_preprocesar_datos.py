import pandas as pd
import numpy as np
from tensorflow.keras.utils import to_categorical

# ───────────────────────────────────────────────
# 1. Configuración
# ───────────────────────────────────────────────
CSV_TYPE = '_full'
PAYLOAD_LEN = 1024
MAX_ROWS_PER_PCAP = 1000
CSV_PATH = f'C:/Users/Elias/Desktop/pfi/data/traffic_dataset{CSV_TYPE}.csv'

# ───────────────────────────────────────────────
# 2. Cargar CSV y aplicar límite por pcap
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
# 3. Preparar X e y agrupando en bloques de 10
# ───────────────────────────────────────────────
X_raw = df[[f'byte_{i}' for i in range(PAYLOAD_LEN)]].astype(np.uint8).values
y_raw = df['label'].values

# Cortar a múltiplo de 10
usable_len = (len(X_raw) // 10) * 10
X_raw = X_raw[:usable_len]
y_raw = y_raw[:usable_len]

# Escalado
X_scaled = X_raw / 255.0

# Reshape a secuencias de 10 paquetes
X = X_scaled.reshape(-1, 10, 32, 32, 1)

# Agrupar etiquetas: mayoría por cada bloque de 10
y_grouped = y_raw.reshape(-1, 10)
y_majority = [np.bincount(block).argmax() for block in y_grouped]
y_cat = to_categorical(y_majority, num_classes=2)

# ───────────────────────────────────────────────
# 4. Guardar
# ───────────────────────────────────────────────
np.save('X.npy', X)
np.save('y_cat.npy', y_cat)
print(f"Listo: X.npy ({X.shape}) y y_cat.npy ({y_cat.shape}) generados.")
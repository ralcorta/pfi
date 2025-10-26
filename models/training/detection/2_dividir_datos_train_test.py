# 2_dividir_train_test.py  ← PASO 2 (versión robusta)
import json
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.utils import to_categorical
import joblib
from pathlib import Path

# ───────────────────────────────────────────────
# 0) Paths y setup
# ───────────────────────────────────────────────
script_dir = Path(__file__).parent

X_path = script_dir / 'X.npy'
y_cat_path = script_dir / 'y_cat.npy'
groups_path = script_dir / 'groups.npy'
feats_path = script_dir / 'X_ransomware_features.npy'
scaler_out = script_dir / 'ransomware_features_scaler.pkl'
summary_out = script_dir / 'split_summary.json'

# ───────────────────────────────────────────────
# 1) Cargar datos completos
# ───────────────────────────────────────────────
print("Cargando datos procesados...")

# Memmap para ahorrar RAM en X
X = np.load(X_path, mmap_mode='r')               # (N, T, 32, 32, 1)
y_cat = np.load(y_cat_path)                      # (N, 2) one-hot
groups = np.load(groups_path, allow_pickle=False)  # (N,) int ids por secuencia

y_labels = np.argmax(y_cat, axis=1)

# Features de ransomware (opcional)
has_ransomware_features = feats_path.exists()
if has_ransomware_features:
    X_ransomware_features = np.load(feats_path, mmap_mode='r')  # (N, F)

# Validaciones básicas
N = len(X)
assert len(y_cat) == N, f"y_cat desalineado: {len(y_cat)} vs X={N}"
assert len(groups) == N, f"groups desalineado: {len(groups)} vs X={N}"
if has_ransomware_features:
    assert len(X_ransomware_features) == N, f"feats desalineado: {len(X_ransomware_features)} vs X={N}"

print(f"Datos cargados:")
print(f"  - X: {X.shape}")
print(f"  - y_cat: {y_cat.shape}")
print(f"  - groups: {groups.shape}")
if has_ransomware_features:
    print(f"  - X_ransomware_features: {X_ransomware_features.shape}")
else:
    print("  - X_ransomware_features: no encontrado (opcional)")

# Si por algún motivo viniera sin one-hot:
if y_cat.ndim == 1 or y_cat.shape[1] != 2:
    print("[WARN] y_cat no está en one-hot; convierto desde labels.")
    y_cat = to_categorical(y_labels, num_classes=2)

# ───────────────────────────────────────────────
# 2) Normalizar features de ransomware (fit SOLO en train)
#     *Se hace DESPUÉS de conocer train_idx; por eso difiero el fit.
# ───────────────────────────────────────────────
scaler = None  # se inicializa tras split si hay features

# ───────────────────────────────────────────────
# 3) Dividir en train/test por grupos (PCAPs)
# ───────────────────────────────────────────────
print("\nDividiendo datos en train/test por grupos (PCAPs)...")
print("   Esto evita leakage manteniendo PCAPs completos juntos.")

gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y_cat, groups=groups))

# Slicing (nota: X es memmap → slicing crea copia de esos índices)
X_train, X_test = X[train_idx], X[test_idx]
y_train, y_test = y_cat[train_idx], y_cat[test_idx]

print(f"División completada:")
print(f"  - Train: {X_train.shape[0]} secuencias")
print(f"  - Test:  {X_test.shape[0]} secuencias")

# ───────────────────────────────────────────────
# 4) Features de ransomware (si existen) — fit en train, transform ambos
# ───────────────────────────────────────────────
if has_ransomware_features:
    print("\nNormalizando features de ransomware (fit en TRAIN, transform en TRAIN/TEST)...")
    scaler = StandardScaler()
    X_ransomware_train = scaler.fit_transform(X_ransomware_features[train_idx])
    X_ransomware_test  = scaler.transform(X_ransomware_features[test_idx])
    print("  - OK: features normalizadas y divididas.")
else:
    X_ransomware_train = None
    X_ransomware_test = None
    print("\n(No hay features de ransomware; continúo sin normalización.)")

# ───────────────────────────────────────────────
# 5) Guardar a disco
# ───────────────────────────────────────────────
print("\nGuardando datos divididos...")

np.save(script_dir / 'X_train.npy', X_train)
np.save(script_dir / 'X_test.npy',  X_test)
np.save(script_dir / 'y_train.npy', y_train)
np.save(script_dir / 'y_test.npy',  y_test)

if has_ransomware_features:
    np.save(script_dir / 'X_ransomware_train.npy', X_ransomware_train)
    np.save(script_dir / 'X_ransomware_test.npy',  X_ransomware_test)

# Guardar scaler si corresponde
if scaler is not None:
    joblib.dump(scaler, scaler_out)
    print(f"  - Scaler guardado en: {scaler_out.name}")

# Guardar índices para trazabilidad
np.save(script_dir / 'train_idx.npy', train_idx)
np.save(script_dir / 'test_idx.npy',  test_idx)

# ───────────────────────────────────────────────
# 6) Resumen + distribución de clases
# ───────────────────────────────────────────────
train_labels = np.argmax(y_train, axis=1)
test_labels  = np.argmax(y_test,  axis=1)

print("\n✅ Datos divididos y guardados:")
print(f"  - Train: {X_train.shape[0]}  | clases: {np.bincount(train_labels)}")
print(f"  - Test:  {X_test.shape[0]}   | clases: {np.bincount(test_labels)}")
print(f"  - División por grupos (PCAPs) para evitar data leakage")
if has_ransomware_features:
    print("  - Features de ransomware normalizadas y guardadas")

# Guardar resumen JSON (útil para la tesis/anexos)
summary = {
    "n_total": int(N),
    "train": {
        "n": int(X_train.shape[0]),
        "class_counts": [int(x) for x in np.bincount(train_labels, minlength=2)]
    },
    "test": {
        "n": int(X_test.shape[0]),
        "class_counts": [int(x) for x in np.bincount(test_labels, minlength=2)]
    },
    "has_ransomware_features": bool(has_ransomware_features),
    "files": {
        "X_train": "X_train.npy",
        "X_test": "X_test.npy",
        "y_train": "y_train.npy",
        "y_test": "y_test.npy",
        "X_ransomware_train": "X_ransomware_train.npy" if has_ransomware_features else None,
        "X_ransomware_test":  "X_ransomware_test.npy"  if has_ransomware_features else None,
        "scaler": scaler_out.name if scaler is not None else None,
        "train_idx": "train_idx.npy",
        "test_idx":  "test_idx.npy"
    }
}
with open(summary_out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"  - Resumen guardado en: {summary_out.name}")
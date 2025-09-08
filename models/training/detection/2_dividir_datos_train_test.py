import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.utils import to_categorical
import joblib
from pathlib import Path

# Obtener el directorio del script actual
script_dir = Path(__file__).parent

# ───────────────────────────────────────────────
# 1. Cargar datos completos
# ───────────────────────────────────────────────
print("Cargando datos procesados...")

# Cargar con mmap_mode='r' para ahorrar RAM
X = np.load(script_dir / 'X.npy', mmap_mode='r')
y_cat = np.load(script_dir / 'y_cat.npy')  # Cargar etiquetas en formato one-hot
groups = np.load(script_dir / 'groups.npy', allow_pickle=True)  # Agregar groups

# Convertir de one-hot a etiquetas numéricas
y_labels = np.argmax(y_cat, axis=1)

# Verificar si existen las features de ransomware (opcional)
ransomware_features_path = script_dir / 'X_ransomware_features.npy'
has_ransomware_features = ransomware_features_path.exists()

print(f"Datos cargados:")
print(f"  - X (payloads): {X.shape}")
print(f"  - y_labels: {y_labels.shape}")
print(f"  - groups: {groups.shape}")
if has_ransomware_features:
    X_ransomware_features = np.load(ransomware_features_path, mmap_mode='r')
    print(f"  - X_ransomware_features: {X_ransomware_features.shape}")
else:
    print("  - X_ransomware_features: No encontrado (opcional)")

# One-hot encoding aquí para ahorrar RAM
print("Convirtiendo etiquetas a one-hot...")
y = to_categorical(y_labels, num_classes=2)

# ───────────────────────────────────────────────
# 2. Normalizar features de ransomware (si existen)
# ───────────────────────────────────────────────
scaler = None
if has_ransomware_features:
    print("Normalizando features de ransomware...")
    scaler = StandardScaler()
    X_ransomware_features_scaled = scaler.fit_transform(X_ransomware_features)
else:
    print("⚠️ Saltando normalización de features de ransomware (no encontradas)")

# ───────────────────────────────────────────────
# 3. Dividir en train/test por grupos (PCAPs)
# ───────────────────────────────────────────────
print("Dividiendo datos en train/test por grupos (PCAPs)...")
print("   Esto evita data leakage manteniendo PCAPs completos juntos")

# Usar GroupShuffleSplit para mantener PCAPs juntos
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(X, y, groups=groups))

# Dividir datos principales
X_train, X_test = X[train_idx], X[test_idx]
y_train, y_test = y[train_idx], y[test_idx]

print(f"División completada:")
print(f"  - Train: {X_train.shape[0]} muestras")
print(f"  - Test: {X_test.shape[0]} muestras")

# Dividir features de ransomware si existen
if has_ransomware_features:
    X_ransomware_train = X_ransomware_features_scaled[train_idx]
    X_ransomware_test = X_ransomware_features_scaled[test_idx]
    print(f"  - Features de ransomware divididas")

# ───────────────────────────────────────────────
# 4. Guardar a disco
# ───────────────────────────────────────────────
print("Guardando datos divididos...")

# Datos principales
np.save(script_dir / 'X_train.npy', X_train)
np.save(script_dir / 'X_test.npy', X_test)
np.save(script_dir / 'y_train.npy', y_train)
np.save(script_dir / 'y_test.npy', y_test)

# Features de ransomware (si existen)
if has_ransomware_features:
    np.save(script_dir / 'X_ransomware_train.npy', X_ransomware_train)
    np.save(script_dir / 'X_ransomware_test.npy', X_ransomware_test)

# Guardar scaler para uso posterior (si existe)
if scaler is not None:
    joblib.dump(scaler, script_dir / 'ransomware_features_scaler.pkl')

# Guardar índices para trazabilidad
np.save(script_dir / 'train_idx.npy', train_idx)
np.save(script_dir / 'test_idx.npy', test_idx)

# ───────────────────────────────────────────────
# 5. Resumen final
# ───────────────────────────────────────────────
print("✅ Datos divididos y guardados:")
print(f"  - Train: {X_train.shape[0]} muestras")
print(f"  - Test: {X_test.shape[0]} muestras")
print(f"  - División por grupos (PCAPs) para evitar data leakage")
if has_ransomware_features:
    print(f"  - Features de ransomware normalizadas y guardadas")
    print(f"  - Scaler guardado en: ransomware_features_scaler.pkl")
print(f"  - Índices guardados para trazabilidad")

# Verificar distribución de clases
train_labels = np.argmax(y_train, axis=1)
test_labels = np.argmax(y_test, axis=1)
print(f"\n📊 Distribución de clases:")
print(f"  - Train: {np.bincount(train_labels)}")
print(f"  - Test: {np.bincount(test_labels)}")
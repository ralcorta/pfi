import numpy as np
from tensorflow.keras.models import load_model
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Cargar modelo
model = load_model('convlstm_model.h5')

# Cargar train/test directamente de archivos
print("Cargando splits de entrenamiento y prueba...")
X_train = np.load('X_train.npy')
X_test = np.load('X_test.npy')
y_train = np.load('y_train.npy')
y_test = np.load('y_test.npy')

# Evaluar
print("Evaluando precisión general...")
loss, accuracy = model.evaluate(X_test, y_test)
print(f"Accuracy final sobre test: {accuracy:.4f}\\n")

# Métricas detalladas
print("Calculando métricas detalladas...")
y_pred = model.predict(X_test)
y_pred_labels = np.argmax(y_pred, axis=1)
y_true_labels = np.argmax(y_test, axis=1)

print("Reporte de clasificación:")
print(classification_report(y_true_labels, y_pred_labels, target_names=["Benigno", "Malware"]))
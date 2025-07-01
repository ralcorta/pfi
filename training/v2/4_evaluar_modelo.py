import numpy as np
from tensorflow.keras.models import load_model
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Cargar datos y modelo
print("Cargando datos...")
X = np.load('X.npy')
y = np.load('y_cat.npy')
model = load_model('convlstm_model.h5')

# Separar en train/test
print("Dividiendo en train/test...")
_, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

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
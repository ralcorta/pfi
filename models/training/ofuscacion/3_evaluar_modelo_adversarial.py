import numpy as np
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report

# ───────────────────────────────────────────────
# 1. Cargar modelo entrenado con datos adversarios
# ───────────────────────────────────────────────
model = load_model('convlstm_model_adversarial.keras')
print("✅ Modelo cargado")

# ───────────────────────────────────────────────
# 2. Evaluar en datos reales (X_test)
# ───────────────────────────────────────────────
X_test = np.load('X_test.npy')
y_test = np.load('y_test.npy')

loss_real, acc_real = model.evaluate(X_test, y_test)
y_pred_real = np.argmax(model.predict(X_test), axis=1)
y_true_real = np.argmax(y_test, axis=1)

print("\n📊 Evaluación en datos reales (X_test):")
print(f"Loss: {loss_real:.4f}, Accuracy: {acc_real:.4f}")
print(classification_report(y_true_real, y_pred_real, target_names=["Benigno", "Malware"]))

# ───────────────────────────────────────────────
# 3. Evaluar en datos ofuscados (X_adv)
# ───────────────────────────────────────────────
X_adv = np.load('X_adv.npy')
y_adv = np.load('y_adv.npy')

loss_adv, acc_adv = model.evaluate(X_adv, y_adv)
y_pred_adv = np.argmax(model.predict(X_adv), axis=1)
y_true_adv = np.argmax(y_adv, axis=1)

print("\n🛡️ Evaluación en datos adversarios (PGD - X_adv):")
print(f"Loss: {loss_adv:.4f}, Accuracy: {acc_adv:.4f}")
print(classification_report(y_true_adv, y_pred_adv, target_names=["Benigno", "Malware"]))
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from sklearn.metrics import classification_report

# Cargar modelo y datos
model = load_model('convlstm_model.keras')
X_test = np.load('X_test.npy')
y_test = np.load('y_test.npy')

# Convertir a tensor
X_original = tf.convert_to_tensor(X_test, dtype=tf.float32)
y_tensor = tf.convert_to_tensor(y_test, dtype=tf.float32)

# Parámetros PGD
epsilon = 0.03     # Perturbación total máxima permitida
alpha = 0.005      # Paso por iteración
num_iter = 10      # Número de iteraciones

# Inicializar X_adv como copia de X_original
X_adv = tf.identity(X_original)

for i in range(num_iter):
    with tf.GradientTape() as tape:
        tape.watch(X_adv)
        prediction = model(X_adv)
        loss = tf.keras.losses.categorical_crossentropy(y_tensor, prediction)

    # Calcular gradiente
    gradient = tape.gradient(loss, X_adv)

    # Subir en la dirección del gradiente
    X_adv = X_adv + alpha * tf.sign(gradient)

    # Proyectar: limitar perturbación total a epsilon
    perturbation = tf.clip_by_value(X_adv - X_original, -epsilon, epsilon)
    X_adv = tf.clip_by_value(X_original + perturbation, 0.0, 1.0)  # mantener en rango [0,1]

    print(f"Iteración {i+1} completa.")

# Evaluar el ataque PGD
y_pred_adv = np.argmax(model.predict(X_adv), axis=1)
y_true = np.argmax(y_test, axis=1)

print("\n🔍 PGD Adversarial Evaluation:")
print(classification_report(y_true, y_pred_adv, target_names=["Benigno", "Malware"]))

# Guardar los ejemplos adversarios generados para entrenamiento posterior
np.save("X_adv.npy", X_adv.numpy())
np.save("y_adv.npy", y_test)

print("✅ Ejemplos adversarios guardados como X_adv.npy y y_adv.npy")
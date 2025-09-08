# 🎯 Pipeline de Detección de Ransomware

Este pipeline implementa un modelo híbrido CNN+LSTM mejorado específicamente para la detección de ransomware, con features adicionales y métricas especializadas.

## 🚀 Características Principales

### ✨ Mejoras Implementadas

1. **Features Específicas de Ransomware**:

   - Entropía de Shannon (detecta encriptación)
   - Patrones de tamaño de paquetes
   - Frecuencia de conexiones y diversidad de puertos
   - Uso de puertos comunes de ransomware (SMB, RDP, WinRM)
   - Análisis de bytes nulos y variabilidad de payload

2. **Arquitectura Híbrida Mejorada**:

   - CNN para patrones espaciales de payloads
   - LSTM para dependencias temporales (20 paquetes)
   - Dense layers para features específicas de ransomware
   - Regularización y normalización por lotes

3. **Métricas Especializadas**:
   - Precision, Recall, F1-Score específicos para ransomware
   - ROC AUC y Average Precision
   - Análisis de falsos positivos/negativos
   - Visualizaciones detalladas

## 📁 Estructura de Archivos

```
training/detection/
├── 1_preprocesar_datos.py          # Extracción de features de ransomware
├── 2_dividir_datos_train_test.py   # División y normalización
├── 3_entrenar_modelo.py            # Entrenamiento del modelo híbrido
├── 4_evaluar_modelo.py             # Evaluación con métricas específicas
├── 5_visualizar_resultados.py      # Visualización de resultados
├── run_ransomware_training.py      # Pipeline completo automatizado
└── README_RANSOMWARE.md            # Esta documentación
```

## 🛠️ Uso del Pipeline

### Opción 1: Pipeline Automatizado (Recomendado)

```bash
cd models/training/detection/
python run_ransomware_training.py
```

### Opción 2: Ejecución Manual

```bash
cd models/training/detection/

# 1. Preprocesar datos y extraer features
python 1_preprocesar_datos.py

# 2. Dividir datos y normalizar
python 2_dividir_datos_train_test.py

# 3. Entrenar modelo
python 3_entrenar_modelo.py

# 4. Evaluar modelo
python 4_evaluar_modelo.py

# 5. Visualizar resultados
python 5_visualizar_resultados.py
```

## 📊 Features de Ransomware Extraídas

| Feature                 | Descripción                      | Importancia                             |
| ----------------------- | -------------------------------- | --------------------------------------- |
| `entropy_mean`          | Entropía promedio de payloads    | 🔴 Alta - Detecta encriptación          |
| `entropy_std`           | Desviación estándar de entropía  | 🟡 Media - Variabilidad de encriptación |
| `packet_size_mean`      | Tamaño promedio de paquetes      | 🟡 Media - Patrones de comunicación     |
| `packet_size_ratio`     | Ratio de variabilidad de tamaños | 🟡 Media - Consistencia de tráfico      |
| `unique_src_ports`      | Puertos origen únicos            | 🟢 Baja - Diversidad de conexiones      |
| `unique_dst_ports`      | Puertos destino únicos           | 🟢 Baja - Diversidad de conexiones      |
| `port_diversity`        | Diversidad total de puertos      | 🟡 Media - Complejidad de red           |
| `ransomware_port_usage` | Uso de puertos de ransomware     | 🔴 Alta - Puertos SMB, RDP, WinRM       |
| `payload_variance`      | Varianza de payloads             | 🟡 Media - Variabilidad de datos        |
| `null_bytes_ratio`      | Ratio de bytes nulos             | 🟡 Media - Patrones de padding          |

## 🎯 Arquitectura del Modelo

```
Input Payloads (20, 32, 32, 1)     Input Features (10,)
           ↓                               ↓
    CNN Branch                        Dense Branch
           ↓                               ↓
    Conv2D(16) → BatchNorm → MaxPool     Dense(32) → BatchNorm → Dropout
           ↓                               ↓
    Conv2D(32) → BatchNorm → MaxPool     Dense(16) → Dropout
           ↓                               ↓
    Conv2D(64) → BatchNorm → GAP         ↓
           ↓                               ↓
    LSTM(64) → LSTM(32) ────────────────→ Concatenate
           ↓
    Dense(64) → BatchNorm → Dropout
           ↓
    Dense(32) → Dropout
           ↓
    Dense(2) → Softmax
```

## 📈 Métricas de Evaluación

### Métricas Básicas

- **Accuracy**: Precisión general del modelo
- **Loss**: Pérdida del modelo

### Métricas Específicas de Ransomware

- **Precision**: Proporción de predicciones de ransomware correctas
- **Recall**: Proporción de ransomware real detectado
- **F1-Score**: Media armónica de precision y recall
- **ROC AUC**: Área bajo la curva ROC
- **Average Precision**: Área bajo la curva Precision-Recall

### Métricas de Confusión

- **True Positives**: Ransomware detectado correctamente
- **False Positives**: Falsas alarmas (benigno clasificado como ransomware)
- **True Negatives**: Tráfico benigno detectado correctamente
- **False Negatives**: Ransomware no detectado

## 📁 Archivos Generados

### Modelos

- `convlstm_model_ransomware_final.keras`: Modelo entrenado final
- `convlstm_model_ransomware.keras`: Mejor modelo durante entrenamiento

### Datos Procesados

- `X.npy`: Secuencias de payloads procesadas
- `y_cat.npy`: Etiquetas categóricas
- `X_ransomware_features.npy`: Features específicas de ransomware
- `ransomware_feature_names.txt`: Nombres de las features

### Datos de Entrenamiento

- `X_train.npy`, `X_test.npy`: Datos divididos
- `y_train.npy`, `y_test.npy`: Etiquetas divididas
- `X_ransomware_train.npy`, `X_ransomware_test.npy`: Features divididas
- `ransomware_features_scaler.pkl`: Normalizador de features

### Resultados

- `evaluation_results.json`: Métricas detalladas en JSON
- `evaluation_visualization.png`: Gráficos de evaluación
- `evaluation_visualization.pdf`: Gráficos en PDF
- `training_history.npy`: Historial de entrenamiento
- `y_pred_proba.npy`: Probabilidades de predicción
- `y_pred.npy`: Predicciones finales

## 🔧 Configuración

### Parámetros Principales

```python
# En 1_preprocesar_datos.py
SEQUENCE_LENGTH = 20        # Longitud de secuencia (aumentado de 10)
PAYLOAD_LEN = 1024         # Tamaño de payload
MAX_ROWS_PER_PCAP = 1000   # Máximo de filas por archivo PCAP

# En 3_entrenar_modelo.py
batch_size = 32            # Tamaño de lote
epochs = 50                # Épocas máximas
patience = 5               # Paciencia para early stopping
```

### Puertos de Ransomware Monitoreados

```python
ransomware_ports = [445, 139, 135, 3389, 5985, 5986]
# 445, 139: SMB (Server Message Block)
# 135: RPC Endpoint Mapper
# 3389: RDP (Remote Desktop Protocol)
# 5985, 5986: WinRM (Windows Remote Management)
```

## 🎯 Interpretación de Resultados

### Criterios de Evaluación

| F1-Score  | Interpretación | Recomendación                     |
| --------- | -------------- | --------------------------------- |
| > 0.8     | Excelente      | Listo para producción             |
| 0.7 - 0.8 | Bueno          | Funcional, considerar fine-tuning |
| 0.6 - 0.7 | Moderado       | Necesita más datos                |
| < 0.6     | Bajo           | Revisar arquitectura y datos      |

### Análisis de Features

- **Entropía alta**: Indica posible encriptación (típico de ransomware)
- **Uso de puertos SMB/RDP**: Comportamiento típico de ransomware
- **Variabilidad de payload**: Patrones de comunicación anómalos
- **Bytes nulos**: Posible padding o datos corruptos

## 🚨 Consideraciones Importantes

1. **Dataset**: El modelo actual usa malware general, no ransomware específico
2. **Features**: Las features implementadas son indicadores, no garantías
3. **Falsos Positivos**: El modelo puede generar falsas alarmas
4. **Actualización**: Requiere retrenamiento con nuevos tipos de ransomware

## 🔄 Próximos Pasos

1. **Dataset Específico**: Obtener datos de ransomware real
2. **Features Adicionales**: Agregar más indicadores de comportamiento
3. **Validación Cruzada**: Implementar validación más robusta
4. **Tiempo Real**: Adaptar para detección en tiempo real
5. **Ensemble**: Combinar múltiples modelos para mayor precisión

## 📞 Soporte

Para preguntas o problemas con el pipeline, revisa:

1. Los logs de ejecución
2. Los archivos de resultados generados
3. Las métricas de evaluación
4. Los gráficos de visualización

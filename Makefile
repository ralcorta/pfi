# =============================================================================
# AI RANSOMWARE DETECTION SYSTEM - MAKEFILE
# =============================================================================
# Este Makefile contiene todos los comandos necesarios para trabajar con el
# sistema de detección de ransomware basado en IA. Está organizado por secciones
# para facilitar su uso y comprensión.
# =============================================================================

# =============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO
# =============================================================================
# Comandos para configurar y gestionar el entorno de desarrollo Python

# Activar el entorno virtual (ejecutar directamente en terminal)
env:
	@echo "Para activar el entorno virtual, ejecuta:"
	@echo "  source .venv/bin/activate"
	@echo "O usa: poetry shell"

# Instalar todas las dependencias del proyecto
install:
	poetry install

# Instalar dependencias incluyendo herramientas de desarrollo
install-dev:
	poetry install --with dev

# Abrir shell de Poetry para trabajar en el entorno virtual
shell:
	poetry shell

# Actualizar todas las dependencias a sus últimas versiones
update:
	poetry update

# =============================================================================
# 2. PROCESAMIENTO DE DATOS
# =============================================================================
# Comandos para extraer, preprocesar y preparar los datos de tráfico de red

# Extraer datos de archivos PCAP a formato CSV
# Uso: make extract ARGS="--input archivo.pcap --output datos.csv"
extract:
	poetry run python models/data/pcap_to_csv_full.py $(ARGS)

# Preprocesar datos de tráfico para entrenamiento del modelo
preprocess:
	poetry run python models/training/detection/1_preprocesar_datos.py

# Dividir datos en conjuntos de entrenamiento y prueba
split-data:
	poetry run python models/training/detection/2_dividir_datos_train_test.py

# =============================================================================
# 3. ENTRENAMIENTO DE MODELOS
# =============================================================================
# Comandos para entrenar y evaluar los modelos de detección de ransomware

# Entrenar el modelo principal de detección
train:
	poetry run python models/training/detection/3_entrenar_modelo.py

# Evaluar el rendimiento del modelo entrenado
evaluate:
	poetry run python models/training/detection/4_evaluar_modelo.py

# Flujo completo de entrenamiento (preprocesar + dividir + entrenar + evaluar)
train-all:
	make preprocess
	make split-data
	make train
	make evaluate

# =============================================================================
# 4. ENTRENAMIENTO ADVERSARIAL
# =============================================================================
# Comandos para entrenar modelos resistentes a ataques adversarios

# Ofuscar datos para simular ataques adversarios
obfuscate:
	poetry run python models/training/ofuscacion/1_ofuscar_datos.py

# Re-entrenar modelo con datos ofuscados
retrain-adversarial:
	poetry run python models/training/ofuscacion/2_reentrenar_modelo.py

# Evaluar modelo entrenado adversarialmente
evaluate-adversarial:
	poetry run python models/training/ofuscacion/3_evaluar_modelo_adversarial.py

# Flujo completo de entrenamiento adversarial
train-adversarial-all:
	make obfuscate
	make retrain-adversarial
	make evaluate-adversarial

# =============================================================================
# 5. APLICACIONES DE DETECCIÓN
# =============================================================================
# Comandos para ejecutar las aplicaciones de detección en tiempo real

# Ejecutar modelo standalone para pruebas
run-model:
	poetry run python run_model.py

# =============================================================================
# 6. SENSOR DE RANSOMWARE EN TIEMPO REAL
# =============================================================================
# Comandos para el sensor avanzado de detección de ransomware

# Mostrar ayuda del sensor
sensor-help:
	poetry run sensor --help

# Monitoreo en vivo de tráfico de red (interfaz por defecto)
sensor-live:
	poetry run sensor --mode live --interface en0

# Monitoreo en vivo con filtro específico (solo HTTPS)
sensor-live-https:
	poetry run sensor --mode live --interface en0 --filter "tcp port 443"

# Análisis de archivo PCAP offline
# Uso: make sensor-pcap PCAP_FILE=ruta/al/archivo.pcap
sensor-pcap:
	poetry run sensor --mode pcap --input $(PCAP_FILE)

# Análisis con umbral personalizado
# Uso: make sensor-pcap-threshold PCAP_FILE=archivo.pcap THRESHOLD=0.85
sensor-pcap-threshold:
	poetry run sensor --mode pcap --input $(PCAP_FILE) --threshold $(THRESHOLD)

# Ejecutar suite de pruebas del sensor
sensor-test:
	poetry run python app/sensor/test_sensor.py

# =============================================================================
# 7. HERRAMIENTAS DE DESARROLLO
# =============================================================================
# Comandos para mantener la calidad del código y realizar pruebas

# Formatear código con Black
format:
	poetry run black .

# Verificar estilo de código con Flake8
lint:
	poetry run flake8 .

# Verificar tipos con MyPy
type-check:
	poetry run mypy .

# Ejecutar todas las pruebas
test:
	poetry run pytest

# Verificar todo: formato + lint + tipos + pruebas
check-all:
	make format
	make lint
	make type-check
	make test

# =============================================================================
# 8. COMANDOS DE CONVENIENCIA
# =============================================================================
# Comandos útiles para operaciones comunes

# Alias para abrir shell (compatibilidad)
run: shell

# Mostrar información del proyecto
info:
	@echo "=========================================="
	@echo "AI RANSOMWARE DETECTION SYSTEM"
	@echo "=========================================="
	@echo "Versión: $(shell poetry version --short)"
	@echo "Python: $(shell poetry run python --version)"
	@echo "Entorno: $(shell poetry env info --path)"
	@echo ""
	@echo "Comandos principales:"
	@echo "  make train-all          - Entrenar modelo completo"
	@echo "  make sensor-live        - Monitoreo en vivo"
	@echo "  make sensor-pcap        - Análisis de PCAP"
	@echo "  make check-all          - Verificar código"
	@echo ""
	@echo "Para más información: make help"

# Mostrar ayuda detallada
help:
	@echo "=========================================="
	@echo "AYUDA - AI RANSOMWARE DETECTION SYSTEM"
	@echo "=========================================="
	@echo ""
	@echo "SECCIONES DISPONIBLES:"
	@echo ""
	@echo "1. CONFIGURACIÓN DEL ENTORNO:"
	@echo "   make install           - Instalar dependencias"
	@echo "   make shell             - Abrir entorno virtual"
	@echo "   make update            - Actualizar dependencias"
	@echo ""
	@echo "2. PROCESAMIENTO DE DATOS:"
	@echo "   make extract ARGS=...  - Extraer datos de PCAP"
	@echo "   make preprocess        - Preprocesar datos"
	@echo "   make split-data        - Dividir datos"
	@echo ""
	@echo "3. ENTRENAMIENTO:"
	@echo "   make train             - Entrenar modelo"
	@echo "   make evaluate          - Evaluar modelo"
	@echo "   make train-all         - Flujo completo"
	@echo ""
	@echo "4. ENTRENAMIENTO ADVERSARIAL:"
	@echo "   make obfuscate         - Ofuscar datos"
	@echo "   make retrain-adversarial - Re-entrenar"
	@echo "   make train-adversarial-all - Flujo completo"
	@echo ""
	@echo "5. DETECCIÓN:"
	@echo "   make run-model         - Modelo standalone"
	@echo "   make sensor-live       - Monitoreo en vivo"
	@echo "   make sensor-pcap PCAP_FILE=... - Análisis PCAP"
	@echo ""
	@echo "6. DESARROLLO:"
	@echo "   make format            - Formatear código"
	@echo "   make lint              - Verificar estilo"
	@echo "   make check-all         - Verificar todo"
	@echo ""
	@echo "EJEMPLOS DE USO:"
	@echo "  make sensor-pcap PCAP_FILE=models/data/small/Benign/Gmail.pcap"
	@echo "  make sensor-pcap-threshold PCAP_FILE=archivo.pcap THRESHOLD=0.85"
	@echo "  make train-all"
	@echo ""
# =============================================================================
# AI RANSOMWARE DETECTION SYSTEM - MAKEFILE COMPLETO
# =============================================================================
# Este Makefile contiene todos los comandos necesarios para trabajar con el
# sistema de detección de ransomware basado en IA. Incluye entrenamiento,
# detección, CI/CD, Docker, Terraform, SageMaker y despliegue automatizado.
# =============================================================================

# Variables de configuración
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?= 339712899854
ECR_REPOSITORY ?= mirror-sensor
ECS_CLUSTER ?= mirror-cluster
ECS_SERVICE ?= mirror-sensor
SAGEMAKER_ENDPOINT ?= sm-detector
MODEL_PATH ?= models/convlstm_model_ransomware_final.keras
TAG ?= latest
ENVIRONMENT ?= academy

# Colores para output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
RESET := \033[0m

# Comando por defecto
.DEFAULT_GOAL := help

# =============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO
# =============================================================================

.PHONY: info
info: ## Mostrar información del proyecto
	@echo "$(CYAN)=== INFORMACIÓN DEL PROYECTO ===$(RESET)"
	@echo "$(GREEN)Versión:$(RESET) $(shell poetry version --short)"
	@echo "$(GREEN)Python:$(RESET) $(shell poetry run python --version)"
	@echo "$(GREEN)AWS Account ID:$(RESET) $(AWS_ACCOUNT_ID)"
	@echo "$(GREEN)AWS Region:$(RESET) $(AWS_REGION)"
	@echo "$(GREEN)ECR Repository:$(RESET) $(ECR_REPOSITORY)"
	@echo "$(GREEN)ECS Cluster:$(RESET) $(ECS_CLUSTER)"
	@echo "$(GREEN)SageMaker Endpoint:$(RESET) $(SAGEMAKER_ENDPOINT)"
	@echo "$(GREEN)Model Path:$(RESET) $(MODEL_PATH)"
	@echo "$(GREEN)Environment:$(RESET) $(ENVIRONMENT)"

.PHONY: env
env: ## Activar el entorno virtual
	@echo "$(BLUE)Para activar el entorno virtual, ejecuta:$(RESET)"
	@echo "  source .venv/bin/activate"
	@echo "O usa: poetry shell"

.PHONY: install
install: ## Instalar dependencias del proyecto
	@echo "$(BLUE)📦 Instalando dependencias...$(RESET)"
	poetry install
	@echo "$(GREEN)✅ Dependencias instaladas$(RESET)"

.PHONY: setup
setup: check-dependencies install setup-aws
	@echo "$(GREEN)✅ Configuración inicial completada$(RESET)"

.PHONY: check-dependencies
check-dependencies: ## Verificar dependencias del sistema
	@echo "$(BLUE)🔍 Verificando dependencias...$(RESET)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ Docker no está instalado$(RESET)"; exit 1; }
	@command -v aws >/dev/null 2>&1 || { echo "$(RED)❌ AWS CLI no está instalado$(RESET)"; exit 1; }
	@command -v terraform >/dev/null 2>&1 || { echo "$(RED)❌ Terraform no está instalado$(RESET)"; exit 1; }
	@command -v poetry >/dev/null 2>&1 || { echo "$(RED)❌ Poetry no está instalado$(RESET)"; exit 1; }
	@echo "$(GREEN)✅ Todas las dependencias están instaladas$(RESET)"

.PHONY: setup-aws
setup-aws: ## Configurar AWS CLI
	@echo "$(BLUE)☁️ Configurando AWS CLI...$(RESET)"
	@aws sts get-caller-identity >/dev/null 2>&1 || { echo "$(RED)❌ AWS CLI no está configurado. Ejecuta: aws configure$(RESET)"; exit 1; }
	@echo "$(GREEN)✅ AWS CLI configurado$(RESET)"


# =============================================================================
# 2. PROCESAMIENTO DE DATOS
# =============================================================================

.PHONY: extract
extract: ## Extraer datos de archivos PCAP a formato CSV
	@echo "$(BLUE)📊 Extrayendo datos de PCAP...$(RESET)"
	@if [ -z "$(ARGS)" ]; then \
		echo "$(YELLOW)Uso: make extract ARGS=\"--input archivo.pcap --output datos.csv\"$(RESET)"; \
		exit 1; \
	fi
	poetry run python models/data/pcap_to_csv_full.py $(ARGS)
	@echo "$(GREEN)✅ Datos extraídos$(RESET)"

.PHONY: preprocess
preprocess: ## Preprocesar datos de tráfico para entrenamiento del modelo
	@echo "$(BLUE)🔄 Preprocesando datos...$(RESET)"
	poetry run python models/training/detection/1_preprocesar_datos.py
	@echo "$(GREEN)✅ Datos preprocesados$(RESET)"

.PHONY: split-data
split-data: ## Dividir datos en conjuntos de entrenamiento y prueba
	@echo "$(BLUE)✂️ Dividiendo datos...$(RESET)"
	poetry run python models/training/detection/2_dividir_datos_train_test.py
	@echo "$(GREEN)✅ Datos divididos$(RESET)"

# =============================================================================
# 3. ENTRENAMIENTO DE MODELOS
# =============================================================================

.PHONY: train
train: ## Entrenar el modelo principal de detección
	@echo "$(BLUE)🤖 Entrenando modelo...$(RESET)"
	poetry run python models/training/detection/3_entrenar_modelo.py
	@echo "$(GREEN)✅ Modelo entrenado$(RESET)"

# Flujo completo de entrenamiento (preprocesar + dividir + entrenar + evaluar)
train-all:
	make preprocess
	make split-data
	make train

# =============================================================================
# 4. ENTRENAMIENTO ADVERSARIAL
# =============================================================================

.PHONY: obfuscate
obfuscate: ## Ofuscar datos para simular ataques adversarios
	@echo "$(BLUE)🔒 Ofuscando datos...$(RESET)"
	poetry run python models/training/ofuscacion/1_ofuscar_datos.py
	@echo "$(GREEN)✅ Datos ofuscados$(RESET)"

# Flujo completo de entrenamiento adversarial
train-adversarial-all:
	make obfuscate

# =============================================================================
# 5. DOCKER Y CONTAINERIZACIÓN
# =============================================================================

.PHONY: docker-build
docker-build: ## Construir imagen Docker
	@echo "$(BLUE)🐳 Construyendo imagen Docker...$(RESET)"
	docker build -t $(ECR_REPOSITORY):$(TAG) .
	@echo "$(GREEN)✅ Imagen Docker construida: $(ECR_REPOSITORY):$(TAG)$(RESET)"

.PHONY: docker-build-tag
docker-build-tag: ## Construir imagen con tag específico
	@echo "$(BLUE)🐳 Construyendo imagen Docker con tag $(TAG)...$(RESET)"
	docker build -t $(ECR_REPOSITORY):$(TAG) .
	@echo "$(GREEN)✅ Imagen Docker construida: $(ECR_REPOSITORY):$(TAG)$(RESET)"

.PHONY: docker-run
docker-run: ## Ejecutar contenedor localmente
	@echo "$(BLUE)🚀 Ejecutando contenedor localmente...$(RESET)"
	docker run -p 4789:4789/udp --env-file .env $(ECR_REPOSITORY):$(TAG)

.PHONY: docker-run-interactive
docker-run-interactive: ## Ejecutar contenedor en modo interactivo
	@echo "$(BLUE)🚀 Ejecutando contenedor en modo interactivo...$(RESET)"
	docker run -it --env-file .env $(ECR_REPOSITORY):$(TAG) /bin/bash

.PHONY: docker-clean
docker-clean: ## Limpiar imágenes Docker
	@echo "$(BLUE)🧹 Limpiando imágenes Docker...$(RESET)"
	-docker rmi $(ECR_REPOSITORY):$(TAG) 2>/dev/null || true
	-docker system prune -f
	@echo "$(GREEN)✅ Imágenes Docker limpiadas$(RESET)"


# =============================================================================
# 6. HERRAMIENTAS DE DESARROLLO
# =============================================================================
# Comandos para mantener la calidad del código y realizar pruebas

# Formatear código con Black
format:
	poetry run black .
	@echo "$(GREEN)✅ Código formateado$(RESET)"

.PHONY: lint
lint: ## Verificar estilo de código con Flake8
	@echo "$(BLUE)🔍 Ejecutando linting...$(RESET)"
	poetry run flake8 .
	@echo "$(GREEN)✅ Linting completado$(RESET)"

.PHONY: type-check
type-check: ## Verificar tipos con MyPy
	@echo "$(BLUE)🔍 Verificando tipos...$(RESET)"
	poetry run mypy .
	@echo "$(GREEN)✅ Verificación de tipos completada$(RESET)"

.PHONY: test
test: ## Ejecutar todas las pruebas
	@echo "$(BLUE)🧪 Ejecutando tests...$(RESET)"
	poetry run pytest
	@echo "$(GREEN)✅ Tests completados$(RESET)"

.PHONY: test-coverage
test-coverage: ## Ejecutar tests con coverage
	@echo "$(BLUE)🧪 Ejecutando tests con coverage...$(RESET)"
	poetry run pytest --cov=app --cov-report=html
	@echo "$(GREEN)✅ Tests con coverage completados$(RESET)"

.PHONY: check-all
check-all: ## Verificar todo: formato + lint + tipos + pruebas
	@echo "$(BLUE)🔍 Ejecutando verificación completa...$(RESET)"
	make format
	make lint
	make type-check
	make test
	@echo "$(GREEN)✅ Verificación completa finalizada$(RESET)"


# =============================================================================
# 7. COMANDOS DE CONVENIENCIA
# =============================================================================

.PHONY: train-adversarial-rl
train-adversarial-rl: ## 🚀 Entrenamiento completo: extract → train-all → obfuscate → retrain-adversarial → adversarial-rl
	@echo "$(CYAN)🚀 INICIANDO ENTRENAMIENTO COMPLETO CON ADVERSARIAL RL$(RESET)"
	@echo "$(YELLOW)⏱️ Tiempo estimado: 45-90 minutos$(RESET)"
	@read -p "¿Continuar? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo ""
	@echo "$(GREEN)📦 Paso 1/5: Extrayendo datos...$(RESET)"
	@cd models/data && poetry run python pcap_to_csv_full.py
	@echo "$(GREEN)🤖 Paso 2/5: Entrenando detector...$(RESET)"
	@$(MAKE) train-all
	@echo "$(GREEN)🔒 Paso 3/5: Ofuscando datos...$(RESET)"
	@$(MAKE) obfuscate
	@echo "$(GREEN)🔄 Paso 4/5: Re-entrenamiento adversarial...$(RESET)"
	@$(MAKE) retrain-adversarial
	@echo "$(GREEN)🎮 Paso 5/5: Adversarial Reinforcement Learning...$(RESET)"
	@cd models/training/adversarial-reinforcement && poetry run python 1_adversarial_reinforcement.py
	@echo ""
	@echo "$(GREEN)🎉 ENTRENAMIENTO COMPLETO FINALIZADO!$(RESET)"
	@echo "$(CYAN)📁 Modelos generados:$(RESET)"
	@ls -la models/training/detection/*.keras 2>/dev/null || echo "  No hay modelos en detection"
	@ls -la models/training/adversarial-reinforcement/*.keras 2>/dev/null || echo "  No hay modelos en adversarial-reinforcement"

.PHONY: check-adversarial-rl
check-adversarial-rl: ## Verificar prerrequisitos para Adversarial RL
	@echo "$(BLUE)🔍 Verificando prerrequisitos...$(RESET)"
	@if [ -d "models/data/backup" ]; then \
		benign=$$(ls models/data/backup/Benign/*.pcap 2>/dev/null | wc -l); \
		malware=$$(ls models/data/backup/Malware/*.pcap 2>/dev/null | wc -l); \
		echo "✅ Archivos .pcap: $$benign benignos, $$malware malware"; \
	else \
		echo "❌ Directorio models/data/backup no encontrado"; \
	fi
	@if command -v poetry >/dev/null 2>&1; then \
		echo "✅ Poetry instalado"; \
	else \
		echo "❌ Poetry no encontrado"; \
	fi
	@if [ -f "models/training/adversarial-reinforcement/1_adversarial_reinforcement.py" ]; then \
		echo "✅ Script Adversarial RL encontrado"; \
	else \
		echo "❌ Script Adversarial RL no encontrado"; \
	fi

.PHONY: resume-adversarial-rl
resume-adversarial-rl: ## Reanudar desde el último paso completado
	@echo "$(BLUE)🔄 Reanudando entrenamiento...$(RESET)"
	@if [ ! -f "models/data/traffic_dataset_full.csv" ]; then \
		echo "📍 Reanudando desde: Extracción"; \
		$(MAKE) _adversarial-step1-extract; \
	elif [ ! -f "models/training/detection/convlstm_model.keras" ]; then \
		echo "📍 Reanudando desde: Entrenamiento detector"; \
		$(MAKE) _adversarial-step2-train-all; \
	elif [ ! -f "models/training/detection/X_adv_eval.npy" ]; then \
		echo "📍 Reanudando desde: Ofuscación"; \
		$(MAKE) _adversarial-step3-obfuscate; \
	elif [ ! -f "models/training/detection/convlstm_model_advtrained.keras" ]; then \
		echo "📍 Reanudando desde: Re-entrenamiento adversarial"; \
		$(MAKE) _adversarial-step4-retrain-adversarial; \
	elif [ ! -f "models/training/adversarial-reinforcement/convlstm_model_adversarial.keras" ]; then \
		echo "📍 Reanudando desde: Adversarial RL"; \
		$(MAKE) _adversarial-step5-reinforcement-learning; \
	else \
		echo "✅ Entrenamiento ya completado"; \
	fi

.PHONY: _adversarial-step1-extract
_adversarial-step1-extract:
	@cd models/data && poetry run python pcap_to_csv_full.py

.PHONY: _adversarial-step2-train-all
_adversarial-step2-train-all:
	@$(MAKE) train-all

.PHONY: _adversarial-step3-obfuscate
_adversarial-step3-obfuscate:
	@$(MAKE) obfuscate

.PHONY: _adversarial-step4-retrain-adversarial
_adversarial-step4-retrain-adversarial:
	@$(MAKE) retrain-adversarial

.PHONY: _adversarial-step5-reinforcement-learning
_adversarial-step5-reinforcement-learning:
	@cd models/training/adversarial-reinforcement && poetry run python 1_adversarial_reinforcement.py


# Comando por defecto
.DEFAULT_GOAL := help
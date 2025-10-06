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

.PHONY: evaluate
evaluate: ## Evaluar el rendimiento del modelo entrenado
	@echo "$(BLUE)📊 Evaluando modelo...$(RESET)"
	poetry run python models/training/detection/4_evaluar_modelo.py
	@echo "$(GREEN)✅ Modelo evaluado$(RESET)"

.PHONY: train-all
train-all: ## Flujo completo de entrenamiento (preprocesar + dividir + entrenar + evaluar)
	@echo "$(BLUE)🚀 Iniciando flujo completo de entrenamiento...$(RESET)"
	make preprocess
	make split-data
	make train
	make evaluate
	@echo "$(GREEN)✅ Entrenamiento completo finalizado$(RESET)"

# =============================================================================
# 4. ENTRENAMIENTO ADVERSARIAL
# =============================================================================

.PHONY: obfuscate
obfuscate: ## Ofuscar datos para simular ataques adversarios
	@echo "$(BLUE)🔒 Ofuscando datos...$(RESET)"
	poetry run python models/training/ofuscacion/1_ofuscar_datos.py
	@echo "$(GREEN)✅ Datos ofuscados$(RESET)"

.PHONY: retrain-adversarial
retrain-adversarial: ## Re-entrenar modelo con datos ofuscados
	@echo "$(BLUE)🔄 Re-entrenando modelo adversarial...$(RESET)"
	poetry run python models/training/ofuscacion/2_reentrenar_modelo.py
	@echo "$(GREEN)✅ Modelo adversarial entrenado$(RESET)"

.PHONY: evaluate-adversarial
evaluate-adversarial: ## Evaluar modelo entrenado adversarialmente
	@echo "$(BLUE)📊 Evaluando modelo adversarial...$(RESET)"
	poetry run python models/training/ofuscacion/3_evaluar_modelo_adversarial.py
	@echo "$(GREEN)✅ Modelo adversarial evaluado$(RESET)"

.PHONY: train-adversarial-all
train-adversarial-all: ## Flujo completo de entrenamiento adversarial
	@echo "$(BLUE)🚀 Iniciando entrenamiento adversarial completo...$(RESET)"
	make obfuscate
	make retrain-adversarial
	make evaluate-adversarial
	@echo "$(GREEN)✅ Entrenamiento adversarial completo finalizado$(RESET)"


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

.PHONY: format
format: ## Formatear código con Black
	@echo "$(BLUE)🎨 Formateando código...$(RESET)"
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
# 7 ENTRENAMIENTO COMPLETO CON ADVERSARIAL RL - VERSIÓN SIMPLE
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


# =============================================================================
# 8. COMANDOS DE TESTING DEL SENSOR
# =============================================================================
.PHONY: build-clean
build-clean: ## Limpiar cache de Docker y rebuild
	@echo "🧹 Limpiando cache de Docker..."
	@docker-compose down
	@docker system prune -f
	@docker-compose build --no-cache sensor-app-mock
	@echo "✅ Cache limpiada y rebuild completado"

.PHONY: run-udp-server-local
init-udp-server-local: ## Ejecutar servidor UDP localmente para pruebas
	@echo "⏳ Inicializando DynamoDB localmente..."
	@docker-compose up -d dynamodb-local
	@echo "⏳ Creando tabla DynamoDB localmente..."
	@poetry run python scripts/init_local_dynamo.py

.PHONY: run-udp-server-local
run-udp-server-local: ## Ejecutar servidor UDP localmente para pruebas
	@echo "🚀 Iniciando servidor UDP local en puerto 4789..."
	@poetry run python -m app.sensor.src.main --udp-port 4789

.PHONY: run-hybrid-server-local
run-hybrid-server-local: ## Ejecutar servidor híbrido UDP + HTTP localmente
	@echo "🚀 Iniciando servidor híbrido local..."
	@echo "   📡 UDP: puerto 4789"
	@echo "   🌐 HTTP: puerto 8080"
	@poetry run python -m app.sensor.src.main --udp-port 4789 --http-port 8080

.PHONY: test-api
test-api: ## Probar endpoints de la API HTTP
	@echo "🧪 Probando endpoints de la API..."
	@echo "📋 Health Check:"
	@curl -s http://localhost:8080/health | jq .
	@echo ""
	@echo "📊 Detecciones:"
	@curl -s http://localhost:8080/detections | jq .
	@echo ""
	@echo "📈 Estadísticas:"
	@curl -s http://localhost:8080/stats | jq .

.PHONY: init-app
init-app: ## Inicializar aplicación completa (DynamoDB + registros base)
	@echo "🚀 Inicializando aplicación completa..."
	@poetry run python scripts/init_app.py

.PHONY: init-aws-app
init-aws-app: ## Inicializar aplicación en AWS (registros base en DynamoDB)
	@echo "🚀 Inicializando aplicación en AWS..."
	@poetry run python scripts/init_aws_app.py

.PHONY: check-status
check-status: ## Verificar estado de la aplicación
	@echo "🔍 Verificando estado de la aplicación..."
	@poetry run python scripts/check_app_status.py

.PHONY: check-aws-status
check-aws-status: ## Verificar estado de la aplicación en AWS
	@echo "🔍 Verificando estado de la aplicación en AWS..."
	@poetry run python scripts/check_aws_status.py

.PHONY: test-udp-server
test-udp-server: ## Probar el servidor UDP con paquetes sintéticos
	@echo "🧪 Probando servidor UDP..."
	@echo "⚠️  Asegúrate de que el servidor esté corriendo en otro terminal"
	@poetry run python scripts/test_udp_server.py

.PHONY: test-udp
test-udp: ## Testear con tráfico UDP simulado
	@echo "📡 Testeando con tráfico UDP..."
	@echo "🎯 Enviando tráfico UDP simulado..."
	@poetry run python scripts/test_udp_traffic.py --host localhost --port 4789 --duration 30
	@echo "📊 Verificando detecciones en DynamoDB..."
	@poetry run python scripts/check_malware_detections.py

.PHONY: demo-on
demo-on-local: ## Habilitar modo demo (local)
	@echo "🎭 Habilitando modo demo..."
	@echo "⏳ Asegurando que DynamoDB local esté corriendo..."
	@poetry run python scripts/enable_demo.py enable --pcap models/data/small/Malware/Zeus.pcap

.PHONY: demo-on
demo-on: ## Habilitar modo demo (AWS)
	@echo "🎭 Habilitando modo demo..."
	@echo "⏳ Asegurando que DynamoDB local esté corriendo..."
	@poetry run python scripts/enable_demo.py enable --pcap /app/models/data/small/Malware/Zeus.pcap

.PHONY: demo-off
demo-off: ## Deshabilitar modo demo
	@echo "🛡️ Deshabilitando modo demo..."
	@echo "⏳ Asegurando que DynamoDB local esté corriendo..."
	@poetry run python scripts/enable_demo.py disable

# =============================================================================
# COMANDOS DE DEMO VÍA API HTTP
# =============================================================================

.PHONY: demo-start
demo-start: ## 🎭 Iniciar demo vía API HTTP
	@echo "🎭 Iniciando demo vía API HTTP..."
	@ALB_DNS=$$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo ""); \
	if [ -z "$$ALB_DNS" ]; then \
		echo "❌ No se pudo obtener DNS del ALB. Asegúrate de que la infraestructura esté desplegada."; \
		exit 1; \
	fi; \
	echo "🌐 Usando ALB: $$ALB_DNS"; \
	curl -X POST "http://$$ALB_DNS/demo/start" \
		-H "Content-Type: application/json" \
		-d '{"pcap_file": "/app/models/data/small/Malware/Zeus.pcap"}' | jq .

.PHONY: demo-stop
demo-stop: ## 🛡️ Detener demo vía API HTTP
	@echo "🛡️ Deteniendo demo vía API HTTP..."
	@ALB_DNS=$$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo ""); \
	if [ -z "$$ALB_DNS" ]; then \
		echo "❌ No se pudo obtener DNS del ALB. Asegúrate de que la infraestructura esté desplegada."; \
		exit 1; \
	fi; \
	echo "🌐 Usando ALB: $$ALB_DNS"; \
	curl -X POST "http://$$ALB_DNS/demo/stop" \
		-H "Content-Type: application/json" | jq .

.PHONY: demo-toggle
demo-toggle: ## 🔄 Alternar demo vía API HTTP
	@echo "🔄 Alternando demo vía API HTTP..."
	@ALB_DNS=$$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo ""); \
	if [ -z "$$ALB_DNS" ]; then \
		echo "❌ No se pudo obtener DNS del ALB. Asegúrate de que la infraestructura esté desplegada."; \
		exit 1; \
	fi; \
	echo "🌐 Usando ALB: $$ALB_DNS"; \
	curl -X POST "http://$$ALB_DNS/demo/toggle" \
		-H "Content-Type: application/json" \
		-d '{"pcap_file": "/app/models/data/small/Malware/Zeus.pcap"}' | jq .

.PHONY: demo-status
demo-status: ## 📊 Ver estado del demo vía API HTTP
	@echo "📊 Verificando estado del demo vía API HTTP..."
	@ALB_DNS=$$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo ""); \
	if [ -z "$$ALB_DNS" ]; then \
		echo "❌ No se pudo obtener DNS del ALB. Asegúrate de que la infraestructura esté desplegada."; \
		exit 1; \
	fi; \
	echo "🌐 Usando ALB: $$ALB_DNS"; \
	curl -s "http://$$ALB_DNS/demo/status" | jq .

.PHONY: test-dynamodb-permissions
test-dynamodb-permissions: ## 🧪 Test de permisos DynamoDB en ECS
	@echo "🧪 Probando permisos de DynamoDB en ECS..."
	@ALB_DNS=$$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo ""); \
	if [ -z "$$ALB_DNS" ]; then \
		echo "❌ No se pudo obtener DNS del ALB. Asegúrate de que la infraestructura esté desplegada."; \
		exit 1; \
	fi; \
	echo "🌐 Usando ALB: $$ALB_DNS"; \
	curl -X POST "http://$$ALB_DNS/test/dynamodb-write" \
		-H "Content-Type: application/json" | jq .

.PHONY: dynamo-explorer
dynamo-explorer: ## Explorador completo de DynamoDB
	@poetry run python scripts/dynamo_explorer.py

# =============================================================================
# DEPLOYMENT Y CONFIGURACIÓN DE CUENTAS
# =============================================================================

.PHONY: setup-new-account
setup-new-account: ## Configurar automáticamente para nueva cuenta AWS
	@echo "🚀 Configurando infraestructura para nueva cuenta AWS..."
	@echo "⚠️  Asegúrate de tener AWS CLI configurado con las credenciales correctas"
	@echo ""
	@read -p "¿Continuar? (y/N): " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/deploy/setup_new_account.sh; \
	else \
		echo "❌ Configuración cancelada"; \
	fi

.PHONY: cleanup-account
cleanup-account: ## Limpiar todos los recursos de la cuenta AWS
	@echo "🧹 Limpiando recursos de la cuenta AWS..."
	@echo "⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos del proyecto"
	@echo ""
	@read -p "¿Estás seguro? (y/N): " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/deploy/cleanup_account.sh; \
	else \
		echo "❌ Limpieza cancelada"; \
	fi

.PHONY: get-account-info
get-account-info: ## Obtener información de la cuenta AWS actual
	@echo "📋 Información de la cuenta AWS:"
	@echo "================================="
	@aws sts get-caller-identity --query 'Account' --output text | xargs -I {} echo "Account ID: {}"
	@aws configure get region | xargs -I {} echo "Región: {}"
	@echo ""
	@echo "🌐 VPC por defecto:"
	@aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].[VpcId,CidrBlock]' --output table
	@echo ""
	@echo "🔗 Subnets disponibles:"
	@aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text | xargs -I {} aws ec2 describe-subnets --filters "Name=vpc-id,Values={}" --query 'Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]' --output table

.PHONY: update-ecr-config
update-ecr-config: ## Actualizar configuración ECR con Account ID actual
	@echo "🔄 Actualizando configuración ECR..."
	@ACCOUNT_ID=$$(aws sts get-caller-identity --query Account --output text); \
	REGION=$$(aws configure get region || echo "us-east-1"); \
	echo "Account ID: $$ACCOUNT_ID"; \
	echo "Región: $$REGION"; \
	sed -i.bak "s/[0-9]*\.dkr\.ecr\.[^/]*\.amazonaws\.com/$$ACCOUNT_ID.dkr.ecr.$$REGION.amazonaws.com/g" terraform/env/terraform.tfvars; \
	echo "✅ Configuración ECR actualizada en terraform/env/terraform.tfvars"

.PHONY: reset-complete
reset-complete: ## 🔄 BORRAR TODO y volver a crear desde cero (RESET COMPLETO)
	@echo "🔄 RESET COMPLETO DEL SISTEMA"
	@echo "============================="
	@echo ""
	@echo "⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos existentes y los recreará"
	@echo ""
	@echo "El script va a:"
	@echo "  1. 🧹 Borrar TODA la infraestructura existente"
	@echo "  2. 🚀 Configurar la cuenta AWS desde cero"
	@echo "  3. 🐳 Construir y subir nueva imagen Docker"
	@echo "  4. 🏗️  Desplegar nueva infraestructura"
	@echo "  5. ⚙️  Inicializar la aplicación"
	@echo "  6. ✅ Verificar que todo funcione"
	@echo ""
	@read -p "¿Continuar con el reset completo? (y/N): " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/deploy/reset_complete.sh; \
	else \
		echo "❌ Reset cancelado"; \
	fi

.PHONY: redeploy
redeploy: ## 🔄 REDEPLOY de la aplicación (nuevo código)
	@echo "🔄 REDEPLOY DE LA APLICACIÓN"
	@echo "============================="
	@echo ""
	@echo "Este script va a:"
	@echo "  1. 🐳 Construir nueva imagen Docker con el código actualizado"
	@echo "  2. 📤 Subir la imagen a ECR"
	@echo "  3. 🚀 Forzar nuevo deployment de ECS (detendrá las tareas actuales)"
	@echo "  4. ✅ Verificar que todo funcione correctamente"
	@echo ""
	@echo "⚠️  ADVERTENCIA: Esto detendrá las tareas ECS actuales y las reemplazará con nuevas"
	@echo ""
	@read -p "¿Continuar con el redeploy? (y/N): " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/deploy/redeploy_app.sh; \
	else \
		echo "❌ Redeploy cancelado"; \
	fi

.PHONY: run
run: shell ## Alias para abrir shell (compatibilidad)

# =============================================================================
# 📚 DOCUMENTACIÓN DE LA API
# =============================================================================
# Comandos para generar y gestionar la documentación automática de la API
# =============================================================================

.PHONY: generate-docs
generate-docs: ## 📚 Generar documentación automática de la API
	@echo "📚 Generando documentación automática de la API..."
	poetry run python scripts/generate_api_docs.py

.PHONY: docs-openapi
docs-openapi: ## 📋 Generar solo el esquema OpenAPI JSON
	@echo "📋 Generando esquema OpenAPI..."
	poetry run python -c "from scripts.generate_api_docs import generate_openapi_schema; generate_openapi_schema()"

.PHONY: docs-markdown
docs-markdown: ## 📝 Generar documentación en Markdown
	@echo "📝 Generando documentación Markdown..."
	poetry run python -c "from scripts.generate_api_docs import generate_markdown_docs; generate_markdown_docs()"

.PHONY: docs-html
docs-html: ## 🌐 Generar documentación HTML con Swagger UI
	@echo "🌐 Generando documentación HTML..."
	poetry run python -c "from scripts.generate_api_docs import generate_html_docs; generate_html_docs()"

.PHONY: docs-serve
docs-serve: ## 🚀 Servir documentación HTML localmente
	@echo "🚀 Sirviendo documentación HTML en http://localhost:8000..."
	@cd docs && python -m http.server 8000

.PHONY: docs-open
docs-open: ## 🔍 Abrir documentación en el navegador
	@echo "🔍 Abriendo documentación..."
	@if [ -f "docs/index.html" ]; then \
		open docs/index.html; \
	else \
		echo "❌ Documentación no encontrada. Ejecuta 'make generate-docs' primero."; \
	fi

.PHONY: docs-clean
docs-clean: ## 🧹 Limpiar archivos de documentación generados
	@echo "🧹 Limpiando archivos de documentación..."
	@rm -rf docs/
	@echo "✅ Archivos de documentación eliminados"

.PHONY: docs-status
docs-status: ## 📊 Verificar estado de la documentación
	@echo "📊 Estado de la documentación:"
	@if [ -d "docs" ]; then \
		echo "📁 Directorio docs: ✅ Existe"; \
		if [ -f "docs/openapi.json" ]; then \
			echo "📋 openapi.json: ✅ Existe"; \
		else \
			echo "📋 openapi.json: ❌ No existe"; \
		fi; \
		if [ -f "docs/API_DOCUMENTATION.md" ]; then \
			echo "📝 API_DOCUMENTATION.md: ✅ Existe"; \
		else \
			echo "📝 API_DOCUMENTATION.md: ❌ No existe"; \
		fi; \
		if [ -f "docs/index.html" ]; then \
			echo "🌐 index.html: ✅ Existe"; \
		else \
			echo "🌐 index.html: ❌ No existe"; \
		fi; \
	else \
		echo "📁 Directorio docs: ❌ No existe"; \
		echo "💡 Ejecuta 'make generate-docs' para crear la documentación"; \
	fi

# Comando por defecto
.DEFAULT_GOAL := help
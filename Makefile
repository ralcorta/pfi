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

.PHONY: help
help: ## Mostrar ayuda completa
	@echo "$(CYAN)=== AI RANSOMWARE DETECTION SYSTEM ===$(RESET)"
	@echo "$(GREEN)Comandos disponibles:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-25s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Ejemplos de uso:$(RESET)"
	@echo "  make setup                    # Configuración inicial completa"
	@echo "  make train-all                # Entrenar modelo completo"
	@echo "  make sensor-live              # Monitoreo en vivo"
	@echo "  make pipeline                 # Pipeline completo de despliegue"
	@echo "  make docker-build TAG=v1.0.0 # Construir imagen con tag específico"

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

.PHONY: install-dev
install-dev: ## Instalar dependencias incluyendo herramientas de desarrollo
	@echo "$(BLUE)📦 Instalando dependencias de desarrollo...$(RESET)"
	poetry install --with dev
	@echo "$(GREEN)✅ Dependencias de desarrollo instaladas$(RESET)"

.PHONY: shell
shell: ## Abrir shell de Poetry
	poetry shell

.PHONY: update
update: ## Actualizar todas las dependencias
	@echo "$(BLUE)🔄 Actualizando dependencias...$(RESET)"
	poetry update
	@echo "$(GREEN)✅ Dependencias actualizadas$(RESET)"

.PHONY: setup
setup: check-dependencies install-dev setup-aws setup-github ## Configuración inicial completa
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

.PHONY: setup-github
setup-github: ## Configurar GitHub CLI y secrets
	@echo "$(BLUE)🐙 Configurando GitHub CLI...$(RESET)"
	@command -v gh >/dev/null 2>&1 || { echo "$(YELLOW)⚠️ GitHub CLI no está instalado. Instala con: brew install gh$(RESET)"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "$(YELLOW)⚠️ No estás autenticado con GitHub CLI. Ejecuta: gh auth login$(RESET)"; exit 1; }
	@echo "$(GREEN)✅ GitHub CLI configurado$(RESET)"

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
# 5. APLICACIONES DE DETECCIÓN
# =============================================================================

.PHONY: run-model
run-model: ## Ejecutar modelo standalone para pruebas
	@echo "$(BLUE)🚀 Ejecutando modelo standalone...$(RESET)"
	poetry run python run_model.py

.PHONY: demo
demo: ## Ejecutar demo con archivos de ejemplo
	@echo "$(BLUE)🎬 Ejecutando demo...$(RESET)"
	poetry run python demo_detector.py --benign models/data/backup/Benign/Gmail.pcap --malicious models/data/backup/Malware/Zeus.pcap --delay 0

# =============================================================================
# 6. SENSOR DE RANSOMWARE EN TIEMPO REAL
# =============================================================================

.PHONY: sensor-help
sensor-help: ## Mostrar ayuda del sensor
	poetry run sensor --help

.PHONY: sensor-live
sensor-live: ## Monitoreo en vivo de tráfico de red (interfaz por defecto)
	@echo "$(BLUE)🔍 Iniciando monitoreo en vivo...$(RESET)"
	poetry run sensor --mode live --interface en0

.PHONY: sensor-live-https
sensor-live-https: ## Monitoreo en vivo con filtro específico (solo HTTPS)
	@echo "$(BLUE)🔍 Iniciando monitoreo HTTPS...$(RESET)"
	poetry run sensor --mode live --interface en0 --filter "tcp port 443"

.PHONY: sensor-pcap
sensor-pcap: ## Análisis de archivo PCAP offline
	@echo "$(BLUE)📁 Analizando archivo PCAP...$(RESET)"
	@if [ -z "$(PCAP_FILE)" ]; then \
		echo "$(YELLOW)Uso: make sensor-pcap PCAP_FILE=ruta/al/archivo.pcap$(RESET)"; \
		exit 1; \
	fi
	poetry run sensor --mode pcap --input $(PCAP_FILE)

.PHONY: sensor-pcap-threshold
sensor-pcap-threshold: ## Análisis con umbral personalizado
	@echo "$(BLUE)📁 Analizando PCAP con umbral personalizado...$(RESET)"
	@if [ -z "$(PCAP_FILE)" ] || [ -z "$(THRESHOLD)" ]; then \
		echo "$(YELLOW)Uso: make sensor-pcap-threshold PCAP_FILE=archivo.pcap THRESHOLD=0.85$(RESET)"; \
		exit 1; \
	fi
	poetry run sensor --mode pcap --input $(PCAP_FILE) --threshold $(THRESHOLD)

.PHONY: sensor-test
sensor-test: ## Ejecutar suite de pruebas del sensor
	@echo "$(BLUE)🧪 Ejecutando pruebas del sensor...$(RESET)"
	poetry run python app/sensor/test_sensor.py
	@echo "$(GREEN)✅ Pruebas del sensor completadas$(RESET)"

# =============================================================================
# 7. DOCKER Y CONTAINERIZACIÓN
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
# 8. AWS ECR (Elastic Container Registry)
# =============================================================================

.PHONY: ecr-login
ecr-login: ## Login a ECR
	@echo "$(BLUE)🔐 Haciendo login a ECR...$(RESET)"
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
	@echo "$(GREEN)✅ Login a ECR exitoso$(RESET)"

.PHONY: ecr-create
ecr-create: ## Crear repositorio ECR
	@echo "$(BLUE)📦 Creando repositorio ECR...$(RESET)"
	-aws ecr create-repository --repository-name $(ECR_REPOSITORY) --region $(AWS_REGION) 2>/dev/null || echo "$(YELLOW)⚠️ Repositorio ya existe$(RESET)"
	@echo "$(GREEN)✅ Repositorio ECR listo$(RESET)"

.PHONY: ecr-tag
ecr-tag: ## Tag imagen para ECR
	@echo "$(BLUE)🏷️ Taggeando imagen para ECR...$(RESET)"
	docker tag $(ECR_REPOSITORY):$(TAG) $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):$(TAG)
	docker tag $(ECR_REPOSITORY):$(TAG) $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):latest
	@echo "$(GREEN)✅ Imagen taggeada para ECR$(RESET)"

.PHONY: ecr-push
ecr-push: ecr-login ecr-create ecr-tag ## Push imagen a ECR
	@echo "$(BLUE)⬆️ Subiendo imagen a ECR...$(RESET)"
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):$(TAG)
	docker push $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):latest
	@echo "$(GREEN)✅ Imagen subida a ECR$(RESET)"

# =============================================================================
# 9. SAGEMAKER Y MODELOS
# =============================================================================

.PHONY: deploy-model
deploy-model: ## Desplegar modelo a SageMaker
	@echo "$(BLUE)🤖 Desplegando modelo a SageMaker...$(RESET)"
	@if [ ! -f "$(MODEL_PATH)" ]; then \
		echo "$(RED)❌ Modelo no encontrado: $(MODEL_PATH)$(RESET)"; \
		echo "$(YELLOW)📁 Modelos disponibles:$(RESET)"; \
		ls -la models/*.keras 2>/dev/null || echo "$(RED)No hay modelos .keras disponibles$(RESET)"; \
		exit 1; \
	fi
	poetry run python scripts/deploy_model.py \
		--model-path $(MODEL_PATH) \
		--endpoint-name $(SAGEMAKER_ENDPOINT) \
		--instance-type ml.t2.medium \
		--region $(AWS_REGION)
	@echo "$(GREEN)✅ Modelo desplegado a SageMaker$(RESET)"

.PHONY: check-endpoint
check-endpoint: ## Verificar estado del endpoint
	@echo "$(BLUE)🔍 Verificando estado del endpoint...$(RESET)"
	aws sagemaker describe-endpoint --endpoint-name $(SAGEMAKER_ENDPOINT) --region $(AWS_REGION) --query 'EndpointStatus' --output text

.PHONY: test-endpoint
test-endpoint: ## Probar endpoint de SageMaker
	@echo "$(BLUE)🧪 Probando endpoint de SageMaker...$(RESET)"
	poetry run python scripts/test_endpoint.py --endpoint-name $(SAGEMAKER_ENDPOINT)

.PHONY: delete-endpoint
delete-endpoint: ## Eliminar endpoint de SageMaker
	@echo "$(BLUE)🗑️ Eliminando endpoint de SageMaker...$(RESET)"
	aws sagemaker delete-endpoint --endpoint-name $(SAGEMAKER_ENDPOINT) --region $(AWS_REGION)
	@echo "$(GREEN)✅ Endpoint eliminado$(RESET)"

.PHONY: list-models
list-models: ## Listar modelos disponibles
	@echo "$(BLUE)📁 Modelos disponibles:$(RESET)"
	@ls -la models/*.keras 2>/dev/null || echo "$(RED)No hay modelos .keras disponibles$(RESET)"

# =============================================================================
# 10. TERRAFORM E INFRAESTRUCTURA
# =============================================================================

.PHONY: tf-init
tf-init: ## Inicializar Terraform
	@echo "$(BLUE)🏗️ Inicializando Terraform...$(RESET)"
	cd terraform/env && terraform init
	@echo "$(GREEN)✅ Terraform inicializado$(RESET)"

.PHONY: tf-plan
tf-plan: ## Plan de Terraform
	@echo "$(BLUE)📋 Generando plan de Terraform...$(RESET)"
	cd terraform/env && terraform plan -var-file="terraform.tfvars"

.PHONY: tf-apply
tf-apply: ## Aplicar cambios de Terraform
	@echo "$(BLUE)🚀 Aplicando cambios de Terraform...$(RESET)"
	cd terraform/env && terraform apply -auto-approve -var-file="terraform.tfvars"
	@echo "$(GREEN)✅ Infraestructura desplegada$(RESET)"

.PHONY: tf-destroy
tf-destroy: ## Destruir infraestructura
	@echo "$(RED)⚠️ ¿Estás seguro de que quieres destruir la infraestructura? (y/N)$(RESET)"
	@read -r response && [ "$$response" = "y" ] || exit 1
	@echo "$(BLUE)🗑️ Destruyendo infraestructura...$(RESET)"
	cd terraform/env && terraform destroy -auto-approve -var-file="terraform.tfvars"
	@echo "$(GREEN)✅ Infraestructura destruida$(RESET)"

.PHONY: tf-output
tf-output: ## Mostrar outputs de Terraform
	@echo "$(BLUE)📤 Outputs de Terraform:$(RESET)"
	cd terraform/env && terraform output

.PHONY: tf-validate
tf-validate: ## Validar configuración de Terraform
	@echo "$(BLUE)✅ Validando configuración de Terraform...$(RESET)"
	cd terraform/env && terraform validate

.PHONY: tf-fmt
tf-fmt: ## Formatear archivos de Terraform
	@echo "$(BLUE)🎨 Formateando archivos de Terraform...$(RESET)"
	cd terraform/env && terraform fmt -recursive

.PHONY: tf-graph
tf-graph: ## Generar diagrama de arquitectura
	@echo "$(BLUE)📊 Generando diagrama de arquitectura...$(RESET)"
	cd terraform/env && terraform graph | dot -Tpng -Gdpi=300 -Gsize=16,12 -o ../../aws-architecture.png
	cd terraform/env && terraform graph | dot -Tsvg -o ../../aws-architecture.svg
	@echo "$(GREEN)✅ Diagramas generados: aws-architecture.png y aws-architecture.svg$(RESET)"

# =============================================================================
# 11. ECS (Elastic Container Service)
# =============================================================================

.PHONY: ecs-update
ecs-update: ## Actualizar servicio ECS
	@echo "$(BLUE)🔄 Actualizando servicio ECS...$(RESET)"
	aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--force-new-deployment \
		--region $(AWS_REGION)
	@echo "$(GREEN)✅ Servicio ECS actualizado$(RESET)"

.PHONY: ecs-status
ecs-status: ## Ver estado del servicio ECS
	@echo "$(BLUE)📊 Estado del servicio ECS:$(RESET)"
	aws ecs describe-services \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION) \
		--query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount,TaskDefinition:taskDefinition}'

.PHONY: ecs-logs
ecs-logs: ## Ver logs del servicio ECS
	@echo "$(BLUE)📋 Logs del servicio ECS (Ctrl+C para salir):$(RESET)"
	aws logs tail /aws/ecs/net-mirror-sensor --follow --region $(AWS_REGION)

.PHONY: ecs-scale
ecs-scale: ## Escalar servicio ECS
	@echo "$(BLUE)📈 Escalando servicio ECS a $(COUNT) tasks...$(RESET)"
	aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--desired-count $(COUNT) \
		--region $(AWS_REGION)
	@echo "$(GREEN)✅ Servicio escalado a $(COUNT) tasks$(RESET)"

.PHONY: ecs-connect
ecs-connect: ## Conectar a contenedor ECS
	@echo "$(BLUE)🔗 Para conectar al contenedor ECS:$(RESET)"
	@echo "aws ecs execute-command --cluster $(ECS_CLUSTER) --task <TASK_ID> --container sensor --interactive --command /bin/bash"

# =============================================================================
# 12. PIPELINE COMPLETO
# =============================================================================

.PHONY: pipeline
pipeline: docker-build ecr-push deploy-model tf-apply ecs-update ## Pipeline completo: build, push, deploy
	@echo "$(GREEN)🎉 Pipeline completado exitosamente!$(RESET)"

.PHONY: pipeline-quick
pipeline-quick: ecr-push ecs-update ## Pipeline rápido (sin rebuild de infraestructura)
	@echo "$(GREEN)⚡ Pipeline rápido completado!$(RESET)"

.PHONY: pipeline-model-only
pipeline-model-only: deploy-model ## Pipeline solo para modelo
	@echo "$(GREEN)🤖 Modelo desplegado exitosamente!$(RESET)"

.PHONY: pipeline-infra-only
pipeline-infra-only: tf-apply ## Pipeline solo para infraestructura
	@echo "$(GREEN)🏗️ Infraestructura desplegada exitosamente!$(RESET)"

# =============================================================================
# 13. HERRAMIENTAS DE DESARROLLO
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
# 14. MONITOREO Y DEBUGGING
# =============================================================================

.PHONY: logs
logs: ## Ver logs de CloudWatch
	@echo "$(BLUE)📋 Logs de CloudWatch (Ctrl+C para salir):$(RESET)"
	aws logs tail /aws/ecs/net-mirror-sensor --follow --region $(AWS_REGION)

.PHONY: metrics
metrics: ## Ver métricas de ECS
	@echo "$(BLUE)📊 Métricas de ECS:$(RESET)"
	aws cloudwatch get-metric-statistics \
		--namespace AWS/ECS \
		--metric-name CPUUtilization \
		--dimensions Name=ServiceName,Value=$(ECS_SERVICE) Name=ClusterName,Value=$(ECS_CLUSTER) \
		--start-time $(shell date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
		--end-time $(shell date -u +%Y-%m-%dT%H:%M:%S) \
		--period 300 \
		--statistics Average \
		--region $(AWS_REGION)

.PHONY: health-check
health-check: ## Verificar salud del sistema
	@echo "$(BLUE)🏥 Verificando salud del sistema...$(RESET)"
	@echo "$(YELLOW)ECS Service:$(RESET)"
	@make ecs-status
	@echo ""
	@echo "$(YELLOW)SageMaker Endpoint:$(RESET)"
	@make check-endpoint
	@echo ""
	@echo "$(YELLOW)Terraform State:$(RESET)"
	@cd terraform/env && terraform show -json | jq -r '.values.root_module.resources[] | select(.type | startswith("aws_")) | "\(.type): \(.values.name // .values.id)"' 2>/dev/null || echo "Terraform no inicializado"

# =============================================================================
# 15. UTILIDADES
# =============================================================================

.PHONY: clean-all
clean-all: docker-clean tf-destroy delete-endpoint ## Limpiar todo (cuidado!)
	@echo "$(RED)⚠️ ¿Estás seguro de que quieres limpiar TODO? (y/N)$(RESET)"
	@read -r response && [ "$$response" = "y" ] || exit 1
	@echo "$(GREEN)✅ Todo limpiado$(RESET)"

.PHONY: clean-docker
clean-docker: docker-clean ## Limpiar solo Docker
	@echo "$(GREEN)✅ Docker limpiado$(RESET)"

.PHONY: clean-terraform
clean-terraform: tf-destroy ## Limpiar solo Terraform
	@echo "$(GREEN)✅ Terraform limpiado$(RESET)"

.PHONY: clean-sagemaker
clean-sagemaker: delete-endpoint ## Limpiar solo SageMaker
	@echo "$(GREEN)✅ SageMaker limpiado$(RESET)"

.PHONY: update-tfvars
update-tfvars: ## Actualizar terraform.tfvars con valores actuales
	@echo "$(BLUE)📝 Actualizando terraform.tfvars...$(RESET)"
	@echo "$(YELLOW)Ingresa los nuevos valores (presiona Enter para mantener el actual):$(RESET)"
	@read -p "VPC ID: " vpc_id; \
	read -p "Subnets (separadas por comas): " subnets; \
	read -p "Container Image: " container_image; \
	read -p "SageMaker Endpoint: " sagemaker_endpoint; \
	read -p "Allowed Ingress CIDR: " allowed_ingress_cidr; \
	cat > terraform/env/terraform.tfvars << EOF; \
region = "$(AWS_REGION)" \
analyzer_vpc_id = "$${vpc_id:-vpc-04f3ea9a31c5074e6}" \
analyzer_subnets = [$$(echo "$$subnets" | sed 's/,/", "/g' | sed 's/^/"/' | sed 's/$$/"/')] \
container_image = "$${container_image:-123456789012.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest}" \
sagemaker_endpoint = "$${sagemaker_endpoint:-sm-detector}" \
allowed_ingress_cidr = "$${allowed_ingress_cidr:-131.229.145.26}" \
tags = { \
  Project = "NetMirror-ML" \
  Env     = "$(ENVIRONMENT)" \
} \
EOF
	@echo "$(GREEN)✅ terraform.tfvars actualizado$(RESET)"

# =============================================================================
# 16. GITHUB ACTIONS
# =============================================================================

.PHONY: setup-github-secrets
setup-github-secrets: ## Configurar secrets de GitHub Actions
	@echo "$(BLUE)🔐 Configurando secrets de GitHub Actions...$(RESET)"
	@command -v gh >/dev/null 2>&1 || { echo "$(RED)❌ GitHub CLI no está instalado$(RESET)"; exit 1; }
	@gh auth status >/dev/null 2>&1 || { echo "$(RED)❌ No estás autenticado con GitHub CLI$(RESET)"; exit 1; }
	@echo "$(YELLOW)Ingresa los valores para los secrets:$(RESET)"
	@read -p "AWS Access Key ID: " aws_access_key_id; \
	read -s -p "AWS Secret Access Key: " aws_secret_access_key; \
	echo; \
	gh secret set AWS_ACCESS_KEY_ID --body "$$aws_access_key_id"; \
	gh secret set AWS_SECRET_ACCESS_KEY --body "$$aws_secret_access_key"; \
	gh secret set AWS_REGION --body "$(AWS_REGION)"; \
	gh secret set ECR_REPOSITORY --body "$(ECR_REPOSITORY)"; \
	gh secret set ECS_CLUSTER --body "$(ECS_CLUSTER)"; \
	gh secret set ECS_SERVICE --body "$(ECS_SERVICE)"; \
	echo "$(GREEN)✅ Secrets configurados$(RESET)"

.PHONY: github-secrets-list
github-secrets-list: ## Listar secrets de GitHub
	@echo "$(BLUE)🔐 Secrets de GitHub:$(RESET)"
	@gh secret list






# =============================================================================
# 17 ENTRENAMIENTO COMPLETO CON ADVERSARIAL RL - VERSIÓN SIMPLE
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
# 18. COMANDOS DE CONVENIENCIA
# =============================================================================

.PHONY: run
run: shell ## Alias para abrir shell (compatibilidad)

# Comando por defecto
.DEFAULT_GOAL := help
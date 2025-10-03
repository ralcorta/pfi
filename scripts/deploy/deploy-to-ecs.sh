#!/bin/bash

# Script para desplegar a ECS
set -e

# Variables
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
CLUSTER_NAME=${CLUSTER_NAME:-sensor-cluster}
SERVICE_NAME=${SERVICE_NAME:-sensor-service}
TASK_DEFINITION_FAMILY="sensor-app"

echo "🚀 Desplegando sensor-app a ECS..."
echo "📋 Configuración:"
echo "   - AWS Account: $AWS_ACCOUNT_ID"
echo "   - AWS Region: $AWS_REGION"
echo "   - Cluster: $CLUSTER_NAME"
echo "   - Service: $SERVICE_NAME"

# 1. Crear cluster ECS si no existe
echo "📦 Creando cluster ECS..."
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION 2>/dev/null || \
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION

# 2. Crear grupo de logs CloudWatch
echo "📝 Creando grupo de logs..."
aws logs describe-log-groups --log-group-name-prefix "/ecs/sensor-app" --region $AWS_REGION 2>/dev/null || \
aws logs create-log-group --log-group-name "/ecs/sensor-app" --region $AWS_REGION

# 3. Procesar task definition
echo "📋 Procesando task definition..."
envsubst < ecs-task-definition.json > ecs-task-definition-processed.json

# 4. Registrar task definition
echo "📝 Registrando task definition..."
TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition-processed.json \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "✅ Task definition registrada: $TASK_DEFINITION_ARN"

# 5. Crear o actualizar servicio
echo "🔄 Creando/actualizando servicio ECS..."
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION 2>/dev/null && \
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --task-definition $TASK_DEFINITION_ARN \
  --region $AWS_REGION || \
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition $TASK_DEFINITION_ARN \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
  --region $AWS_REGION

echo "✅ Servicio ECS creado/actualizado!"

# 6. Limpiar archivo temporal
rm -f ecs-task-definition-processed.json

echo "🎉 Despliegue a ECS completado!"
echo "💡 Para ver logs:"
echo "   aws logs tail /ecs/sensor-app --follow --region $AWS_REGION"

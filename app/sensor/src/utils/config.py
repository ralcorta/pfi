# app/sensor/src/utils/config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración de la aplicación"""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'dummy')
    AWS_REGION=os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCOUNT_ID=os.getenv('AWS_ACCOUNT_ID', '111111111111')
    ECR_REPOSITORY=os.getenv('ECR_REPOSITORY', 'mirror-sensor')
    ECS_CLUSTER=os.getenv('ECS_CLUSTER', 'mirror-cluster')
    ECS_SERVICE=os.getenv('ECS_SERVICE', 'mirror-sensor')
    SAGEMAKER_ENDPOINT=os.getenv('SAGEMAKER_ENDPOINT', 'sm-detector')
    MODEL_PATH=os.getenv('MODEL_PATH', 'models/convlstm_model_ransomware_final.keras')
    ENVIRONMENT=os.getenv('ENVIRONMENT', 'local')
    
    @classmethod
    def get_aws_config(cls):
        """Obtiene configuración de AWS"""
        return {
            'aws_access_key_id': cls.AWS_ACCESS_KEY_ID,
            'aws_region': cls.AWS_REGION,
            'aws_account_id': cls.AWS_ACCOUNT_ID,
            'ecr_repository': cls.ECR_REPOSITORY,
            'ecs_cluster': cls.ECS_CLUSTER,
            'ecs_service': cls.ECS_SERVICE,
            'sagemaker_endpoint': cls.SAGEMAKER_ENDPOINT,
            'model_path': cls.MODEL_PATH,
            'environment': cls.ENVIRONMENT
        }
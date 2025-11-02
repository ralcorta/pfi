"""
Cliente para gestionar usuarios en DynamoDB.
Maneja la tabla de usuarios/clientes con asignación automática de VNI.
"""

import boto3
import secrets
import hashlib
from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta

from app.sensor.src.utils.environment import env
from app.sensor.src.utils.email_service import email_service
from app.sensor.src.db.models import User, UserResponse


class UserClient:
    """Cliente para operaciones de usuarios en DynamoDB."""
    
    # Constantes
    VNI_START = 3001
    VNI_DEFAULT = 3000
    TOKEN_EXPIRY_DAYS = 7
    
    def __init__(self):
        self.table_name = env.users_table_name
        self.dynamo, self.client = self._init_dynamodb()
        self._ensure_table_exists()
        self.table = self.dynamo.Table(self.table_name)

    def _init_dynamodb(self):
        """Inicializa la conexión a DynamoDB (local o AWS)."""
        config = {"region_name": env.aws_region}
        
        if env.dynamodb_endpoint:
            config["endpoint_url"] = env.dynamodb_endpoint
            print(f"🔗 Usando DynamoDB local en: {env.dynamodb_endpoint}")
        else:
            print(f"☁️  Usando DynamoDB en AWS región: {env.aws_region}")
        
        return boto3.resource("dynamodb", **config), boto3.client("dynamodb", **config)

    def _ensure_table_exists(self):
        """Crea la tabla de usuarios si no existe."""
        try:
            self.client.describe_table(TableName=self.table_name)
            print(f"✅ Tabla de usuarios '{self.table_name}' ya existe")
        except self.client.exceptions.ResourceNotFoundException:
            print(f"📋 Creando tabla de usuarios '{self.table_name}'...")
            self._create_table()
        except Exception as e:
            print(f"❌ Error verificando tabla de usuarios: {e}")
            raise

    def _create_table(self):
        """Crea la tabla de usuarios."""
        schema = {
            'TableName': self.table_name,
            'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'email', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        }
        
        try:
            self.client.create_table(**schema)
            print(f"🔄 Tabla '{self.table_name}' creada, esperando activación...")
            
            waiter = self.client.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            
            print(f"✅ Tabla '{self.table_name}' activa y lista para usar")
        except Exception as e:
            print(f"❌ Error creando tabla de usuarios: {e}")
            raise

    def _normalize_user(self, item: dict) -> User:
        """Normaliza un item de DynamoDB y lo convierte a modelo User."""
        # Convertir Decimal a int y None a valores por defecto
        normalized = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                normalized[key] = int(value)
            elif value is None and key in ['password_token', 'token_expires_at', 'password_hash']:
                normalized[key] = None
            else:
                normalized[key] = value
        return User(**normalized)

    def _format_user_response(self, user: User, traffic_mirror_target_id: str) -> UserResponse:
        """Formatea la respuesta del usuario para la API."""
        return UserResponse(
            email=user.email,
            vni_cliente=user.vni,
            traffic_mirror_target_id=user.traffic_mirror_target_id or traffic_mirror_target_id,
            created_at=user.created_at
        )

    def _get_next_vni(self) -> int:
        """Obtiene el siguiente VNI disponible."""
        try:
            response = self.table.scan(ProjectionExpression='vni')
            max_vni = max(
                (int(item['vni']) for item in response.get('Items', []) if 'vni' in item),
                default=self.VNI_DEFAULT
            )
            return max_vni + 1
        except Exception as e:
            print(f"⚠️  Error escaneando usuarios para obtener VNI: {e}")
            return self.VNI_START

    def _generate_password_token(self) -> tuple[str, int]:
        """Genera un token único para establecimiento de contraseña."""
        token = secrets.token_urlsafe(32)
        expires_at = int((datetime.now() + timedelta(days=self.TOKEN_EXPIRY_DAYS)).timestamp() * 1000)
        return token, expires_at

    def _hash_password(self, password: str) -> str:
        """Hashea una contraseña (SHA256 - en producción usar bcrypt/argon2)."""
        return hashlib.sha256(password.encode()).hexdigest()

    def _is_token_expired(self, expires_at: int) -> bool:
        """Verifica si un token ha expirado."""
        return int(datetime.now().timestamp() * 1000) > expires_at

    def _find_user_by_token(self, token: str) -> Optional[User]:
        """Busca un usuario por su token de contraseña."""
        try:
            response = self.table.scan(
                FilterExpression="password_token = :token",
                ExpressionAttributeValues={":token": token}
            )
            items = response.get('Items', [])
            return self._normalize_user(items[0]) if items else None
        except Exception as e:
            print(f"❌ Error buscando usuario por token: {e}")
            return None
        
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por su email."""
        try:
            response = self.table.get_item(Key={'email': email})
            if 'Item' in response:
                return self._normalize_user(response['Item'])
            return None
        except Exception as e:
            print(f"❌ Error obteniendo usuario {email}: {e}")
            raise

    def verify_password(self, email: str, password: str) -> bool:
        """
        Verifica si la contraseña es correcta para un usuario.
        
        Args:
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            True si la contraseña es correcta, False en caso contrario
        """
        user = self.get_user_by_email(email)
        if not user or not user.password_hash:
            return False
        
        password_hash = self._hash_password(password)
        return password_hash == user.password_hash

    def create_user(self, email: str, traffic_mirror_target_id: str) -> UserResponse:
        """Crea un nuevo usuario o retorna el existente."""
        existing_user = self.get_user_by_email(email)
        if existing_user:
            print(f"ℹ️  Usuario {email} ya existe, retornando datos existentes")
            return self._format_user_response(existing_user, traffic_mirror_target_id)
        
        # Crear nuevo usuario
        vni = self._get_next_vni()
        password_token, token_expires_at = self._generate_password_token()
        created_at = int(datetime.now().timestamp() * 1000)
        
        user_item = {
            'email': email,
            'vni': vni,
            'traffic_mirror_target_id': traffic_mirror_target_id,
            'created_at': created_at,
            'password_token': password_token,
            'token_expires_at': token_expires_at,
            'password_hash': None
        }
        
        try:
            self.table.put_item(Item=user_item)
            print(f"✅ Usuario creado: {email} con VNI {vni}")
            
            # Enviar email de bienvenida (no crítico)
            try:
                email_service.send_welcome_email(to_email=email, vni=vni, password_token=password_token)
            except Exception as e:
                print(f"⚠️  Error enviando email de bienvenida (no crítico): {e}")
            
            return UserResponse(
                email=email,
                vni_cliente=vni,
                traffic_mirror_target_id=traffic_mirror_target_id,
                created_at=created_at
            )
        except Exception as e:
            print(f"❌ Error creando usuario {email}: {e}")
            raise

    def verify_token(self, token: str) -> Optional[User]:
        """
        Verifica si un token es válido y retorna el usuario si existe.
        
        Args:
            token: Token de verificación
            
        Returns:
            User si el token es válido y no expirado, None en caso contrario
        """
        user = self._find_user_by_token(token)
        if not user:
            return None
        
        if user.token_expires_at and self._is_token_expired(user.token_expires_at):
            return None
        
        return user

    def set_password(self, token: str, password: str) -> bool:
        """Establece la contraseña de un usuario usando el token de verificación."""
        user = self.verify_token(token)
        if not user:
            print("❌ Token inválido o expirado")
            return False
        
        try:
            password_hash = self._hash_password(password)
            self.table.update_item(
                Key={'email': user.email},
                UpdateExpression="SET password_hash = :pwd REMOVE password_token, token_expires_at",
                ExpressionAttributeValues={":pwd": password_hash}
            )
            print(f"✅ Contraseña establecida para {user.email}")
            return True
        except Exception as e:
            print(f"❌ Error estableciendo contraseña: {e}")
            return False

    def get_all_users(self) -> list[User]:
        """
        Obtiene todos los usuarios de la tabla.
        
        Returns:
            Lista de usuarios (sin información sensible)
        """
        try:
            users = []
            last_key = None
            
            while True:
                scan_kwargs = {} if not last_key else {'ExclusiveStartKey': last_key}
                response = self.table.scan(**scan_kwargs)
                items = response.get('Items', [])
                
                for item in items:
                    user = self._normalize_user(item)
                    if user:
                        users.append(user)
                
                last_key = response.get('LastEvaluatedKey')
                if not last_key:
                    break
            
            return users
        except Exception as e:
            print(f"❌ Error obteniendo usuarios: {e}")
            raise

    def clear_table(self) -> None:
        """Elimina todos los usuarios de la tabla."""
        print(f"🗑️  Limpiando tabla de usuarios '{self.table_name}'...")
        deleted_count = 0
        
        last_key = None
        while True:
            scan_kwargs = {} if not last_key else {'ExclusiveStartKey': last_key}
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            if not items:
                break
            
            for item in items:
                self.table.delete_item(Key={'email': item['email']})
                deleted_count += 1
                print(f"  ✓ Eliminado: {item['email']}")
            
            last_key = response.get('LastEvaluatedKey')
            if not last_key:
                break
        
        print(f"✅ Tabla de usuarios limpiada: {deleted_count} elementos eliminados")


# Instancia global
user_db = UserClient()

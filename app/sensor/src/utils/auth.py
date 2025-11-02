"""
Utilidades para autenticación JWT.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# Instancia global del esquema de seguridad HTTP Bearer
security = HTTPBearer()


class AuthService:
    """Servicio para manejo de tokens JWT."""
    
    # Configuración JWT
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 horas por defecto
    
    @classmethod
    def create_access_token(cls, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Crea un token JWT de acceso.
        
        Args:
            data: Datos a incluir en el token (ej: {"sub": email})
            expires_delta: Tiempo de expiración personalizado
            
        Returns:
            Token JWT codificado
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[dict]:
        """
        Verifica y decodifica un token JWT.
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            Payload del token si es válido, None en caso contrario
        """
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @classmethod
    def get_current_user_email(cls, token: str) -> Optional[str]:
        """
        Obtiene el email del usuario del token JWT.
        
        Args:
            token: Token JWT
            
        Returns:
            Email del usuario o None si el token es inválido
        """
        payload = cls.verify_token(token)
        if payload:
            return payload.get("sub")  # 'sub' es el estándar JWT para subject (usuario)
        return None

    @classmethod
    async def get_current_user(cls, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """
        Dependency para FastAPI que obtiene el usuario actual del token JWT.
        
        Args:
            credentials: Credenciales HTTP Bearer del request
            
        Returns:
            Email del usuario autenticado
            
        Raises:
            HTTPException: Si el token es inválido o no está presente
        """
        token = credentials.credentials
        email = cls.get_current_user_email(token)
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return email


# Instancia global
auth_service = AuthService()


"""
Modelos de datos tipados para las estructuras de base de datos.
Usa Pydantic para validación y tipado fuerte.
"""

from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """Modelo completo de usuario almacenado en DynamoDB."""
    email: str
    vni: int
    traffic_mirror_target_id: str
    created_at: int
    password_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    password_hash: Optional[str] = None

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class UserResponse(BaseModel):
    """Respuesta de la API al crear/obtener un usuario."""
    email: str
    vni_cliente: int
    traffic_mirror_target_id: str
    created_at: int

    class Config:
        """Configuración del modelo."""
        from_attributes = True
        populate_by_name = True


class Detection(BaseModel):
    """Modelo de detección almacenada en DynamoDB."""
    id: str
    timestamp: int
    # Campos adicionales pueden ser dinámicos
    # Usar extra="allow" para permitir campos no definidos

    class Config:
        """Configuración del modelo."""
        from_attributes = True
        extra = "allow"  # Permite campos adicionales dinámicos


class DetectionResponse(BaseModel):
    """Respuesta al obtener todas las detecciones."""
    detections: list[Detection]
    total_count: int
    message: str

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class TokenVerificationResponse(BaseModel):
    """Respuesta de verificación de token."""
    valid: bool
    email: Optional[str] = None
    message: str

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class SetPasswordRequest(BaseModel):
    """Request para establecer contraseña."""
    password: str
    password_confirm: str

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class SetPasswordResponse(BaseModel):
    """Respuesta al establecer contraseña."""
    message: str
    status: str

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class LoginRequest(BaseModel):
    """Request para login."""
    email: str
    password: str

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class LoginResponse(BaseModel):
    """Respuesta de login con JWT."""
    access_token: str
    token_type: str = "bearer"
    email: str
    vni_cliente: int

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class UsersResponse(BaseModel):
    """Respuesta al obtener todos los usuarios."""
    users: list[UserResponse]
    total_count: int
    message: str = "Usuarios obtenidos exitosamente"

    class Config:
        """Configuración del modelo."""
        from_attributes = True


class CurrentUserResponse(BaseModel):
    """Respuesta con información del usuario actual."""
    email: str
    vni_cliente: int
    traffic_mirror_target_id: str
    created_at: int

    class Config:
        """Configuración del modelo."""
        from_attributes = True


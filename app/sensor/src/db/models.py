
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    email: str
    vni: int
    traffic_mirror_target_id: str
    created_at: int
    password_token: Optional[str] = None
    token_expires_at: Optional[int] = None
    password_hash: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    email: str
    vni_cliente: int
    traffic_mirror_target_id: str
    created_at: int

    class Config:
        from_attributes = True
        populate_by_name = True


class Detection(BaseModel):
    id: str
    timestamp: int

    class Config:
        from_attributes = True
        extra = "allow"


class DetectionResponse(BaseModel):
    detections: list[Detection]
    total_count: int
    message: str

    class Config:
        from_attributes = True


class TokenVerificationResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    message: str

    class Config:
        from_attributes = True


class SetPasswordRequest(BaseModel):
    password: str
    password_confirm: str

    class Config:
        from_attributes = True


class SetPasswordResponse(BaseModel):
    message: str
    status: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    vni_cliente: int

    class Config:
        from_attributes = True


class UsersResponse(BaseModel):
    users: list[UserResponse]
    total_count: int
    message: str = "Usuarios obtenidos exitosamente"

    class Config:
        from_attributes = True


class CurrentUserResponse(BaseModel):
    email: str
    vni_cliente: int
    traffic_mirror_target_id: str
    created_at: int

    class Config:
        from_attributes = True


"""
Router para la API de control del sensor de malware.
Maneja endpoints de salud, estadísticas y detecciones.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from app.sensor.src.db.detection_client import detection_db
from app.sensor.src.db.user_client import user_db
from app.sensor.src.db.models import (
    UserResponse,
    TokenVerificationResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    DetectionResponse,
    LoginRequest,
    LoginResponse,
    UsersResponse,
    CurrentUserResponse
)
from app.sensor.src.utils.auth import auth_service
from app.sensor.src.utils.environment import env


router = APIRouter()


@router.get("/health")
def health():
    """Endpoint de salud del sistema."""
    return {
        "status": "ok",
        "system": "simplified",
        "http_server": "running"
    }

@router.get("/detections", response_model=DetectionResponse)
def get_all_database(current_user_email: str = Depends(auth_service.get_current_user)):
    """
    Trae toda la base de datos de detecciones.
    Requiere autenticación JWT.
    """
    try:
        return detection_db.get_all_detections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/clients/terraform-config", response_model=UserResponse)
def get_terraform_config(email: str = Query(..., description="Email del cliente para despliegue Terraform")):
    """
    Endpoint exclusivo para Terraform durante el despliegue.
    
    Crea o retorna la configuración del cliente necesaria para el despliegue de Terraform.
    Si el cliente existe, retorna su configuración existente.
    Si no existe, crea un nuevo cliente con un VNI único asignado automáticamente.
    
    Este endpoint está diseñado para ser llamado por Terraform durante el despliegue
    del módulo cliente, no para uso directo por usuarios finales.
    
    Args:
        email: Email del cliente
        
    Returns:
        JSON con traffic_mirror_target_id y vni_cliente
    """
    # Validar que el traffic_mirror_target_id esté configurado
    if not env.traffic_mirror_target_id:
        raise HTTPException(
            status_code=500,
            detail="Traffic Mirror Target ID no está configurado en el sistema"
        )
    
    # Validar formato básico del email
    if not email or "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Email inválido. Debe tener formato válido."
        )
    
    try:
        # Crear o obtener usuario
        user_data = user_db.create_user(
            email=email,
            traffic_mirror_target_id=env.traffic_mirror_target_id
        )
        
        # Retornar solo los campos requeridos por Terraform
        return UserResponse(
            email=user_data.email,
            vni_cliente=user_data.vni_cliente,
            traffic_mirror_target_id=user_data.traffic_mirror_target_id,
            created_at=user_data.created_at
        )
        
    except Exception as e:
        print(f"❌ Error procesando solicitud para {email}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud: {str(e)}"
        )


@router.get("/v1/users/verify-token", response_model=TokenVerificationResponse)
def verify_token(token: str = Query(..., description="Token de verificación para establecer contraseña")):
    """
    Endpoint para verificar si un token de establecimiento de contraseña es válido.
    Retorna información sobre la validez del token.
    """
    try:
        user = user_db.verify_token(token)
        
        if not user:
            return TokenVerificationResponse(
                valid=False,
                message="Token inválido o expirado"
            )
        
        return TokenVerificationResponse(
            valid=True,
            email=user.email,
            message="Token válido"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validando token: {str(e)}")


@router.post("/v1/users/setup-password", response_model=SetPasswordResponse)
def setup_password(request: SetPasswordRequest, token: str = Query(..., description="Token de verificación")):
    """
    Endpoint para establecer la contraseña del usuario usando el token de verificación.
    
    Args:
        request: Datos con password y password_confirm
        token: Token de verificación único
        
    Returns:
        Mensaje de éxito o error
    """
    # Validar que las contraseñas coincidan
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=400,
            detail="Las contraseñas no coinciden"
        )
    
    # Validar longitud mínima
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    try:
        # Establecer contraseña usando el token
        success = user_db.set_password(token=token, password=request.password)
        
        if success:
            return SetPasswordResponse(
                message="Contraseña establecida exitosamente",
                status="success"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Token inválido o expirado"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error estableciendo contraseña: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al establecer contraseña: {str(e)}"
        )


@router.post("/v1/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Endpoint para autenticación de usuarios.
    Valida email y contraseña, y retorna un JWT si las credenciales son correctas.
    
    Args:
        request: Datos de login (email y password)
        
    Returns:
        JWT token y información del usuario
    """
    # Verificar credenciales
    if not user_db.verify_password(request.email, request.password):
        raise HTTPException(
            status_code=401,
            detail="Email o contraseña incorrectos"
        )
    
    # Obtener usuario completo
    user = user_db.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )
    
    # Crear token JWT
    access_token = auth_service.create_access_token(
        data={"sub": user.email}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        email=user.email,
        vni_cliente=user.vni
    )


@router.get("/v1/auth/me", response_model=CurrentUserResponse)
def get_current_user_info(current_user_email: str = Depends(auth_service.get_current_user)):
    """
    Endpoint para obtener la información del usuario actual autenticado.
    Requiere autenticación JWT.
    
    Returns:
        Información del usuario actual (sin información sensible)
    """
    try:
        user = user_db.get_user_by_email(current_user_email)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )
        
        return CurrentUserResponse(
            email=user.email,
            vni_cliente=user.vni,
            traffic_mirror_target_id=user.traffic_mirror_target_id,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obteniendo información del usuario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información del usuario: {str(e)}"
        )


@router.get("/v1/users", response_model=UsersResponse)
def get_all_users(current_user_email: str = Depends(auth_service.get_current_user)):
    """
    Endpoint para obtener todos los usuarios del sistema.
    Requiere autenticación JWT.
    
    Returns:
        Lista de todos los usuarios (sin información sensible)
    """
    try:
        users = user_db.get_all_users()
        
        # Convertir a UserResponse (sin información sensible)
        users_response = [
            UserResponse(
                email=user.email,
                vni_cliente=user.vni,
                traffic_mirror_target_id=user.traffic_mirror_target_id,
                created_at=user.created_at
            )
            for user in users
        ]
        
        return UsersResponse(
            users=users_response,
            total_count=len(users_response)
        )
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener usuarios: {str(e)}"
        )



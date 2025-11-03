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
    return {
        "status": "ok",
        "system": "simplified",
        "http_server": "running"
    }

@router.get("/detections", response_model=DetectionResponse)
def get_all_database(current_user_email: str = Depends(auth_service.get_current_user)):
    try:
        return detection_db.get_all_detections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/clients/terraform-config", response_model=UserResponse)
def get_terraform_config(email: str = Query(..., description="Email del cliente para despliegue Terraform")):
    if not env.traffic_mirror_target_id:
        raise HTTPException(
            status_code=500,
            detail="Traffic Mirror Target ID no está configurado en el sistema"
        )
    
    if not email or "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Email inválido. Debe tener formato válido."
        )
    
    try:
        user_data = user_db.create_user(
            email=email,
            traffic_mirror_target_id=env.traffic_mirror_target_id
        )
        
        return UserResponse(
            email=user_data.email,
            vni_cliente=user_data.vni_cliente,
            traffic_mirror_target_id=user_data.traffic_mirror_target_id,
            created_at=user_data.created_at
        )
        
    except Exception as e:
        print(f"Error procesando solicitud para {email}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud: {str(e)}"
        )


@router.get("/v1/users/verify-token", response_model=TokenVerificationResponse)
def verify_token(token: str = Query(..., description="Token de verificación para establecer contraseña")):
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
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=400,
            detail="Las contraseñas no coinciden"
        )
    
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    try:
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
        print(f"Error estableciendo contraseña: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al establecer contraseña: {str(e)}"
        )


@router.post("/v1/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if not user_db.verify_password(request.email, request.password):
        raise HTTPException(
            status_code=401,
            detail="Email o contraseña incorrectos"
        )
    
    user = user_db.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )
    
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
        print(f"Error obteniendo información del usuario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información del usuario: {str(e)}"
        )


@router.get("/v1/users", response_model=UsersResponse)
def get_all_users(current_user_email: str = Depends(auth_service.get_current_user)):
    try:
        users = user_db.get_all_users()
        
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
        print(f"Error obteniendo usuarios: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener usuarios: {str(e)}"
        )



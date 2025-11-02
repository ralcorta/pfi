"""
Servicio simple para envío de emails usando Resend.com.
"""

import os
import requests
from typing import Optional

from app.sensor.src.utils.environment import env


class EmailService:
    """Servicio simple para enviar emails mediante Resend.com."""
    
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY", "")
        self.from_email = env.email_from_address
        self.enabled = env.email_enabled
        
        if not self.enabled:
            print("⚠️  Envío de emails deshabilitado (EMAIL_ENABLED=false)")
        elif not self.api_key:
            print("⚠️  RESEND_API_KEY no configurado, emails deshabilitados")
    
    def send_welcome_email(self, to_email: str, vni: int, password_token: str) -> bool:
        """
        Envía un email de bienvenida al usuario registrado con URL para establecer contraseña.
        
        Args:
            to_email: Email del destinatario
            vni: VNI único asignado al cliente
            password_token: Token único para establecer contraseña
            
        Returns:
            True si el email se envió correctamente, False en caso contrario
        """
        if not self.enabled or not self.api_key:
            return False
        
        if not self.from_email:
            print(f"⚠️  EMAIL_FROM_ADDRESS no configurado, saltando envío de email")
            return False
        
        setup_password_url = f"{env.dashboard_url}/auth/setup-password?token={password_token}"
        
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": "Bienvenido al Sistema de Detección de Ransomware",
            "html": f"""
            <h2>Bienvenido al Sistema de Detección de Ransomware</h2>
            <p>Su cuenta ha sido registrada exitosamente.</p>
            
            <h3>Detalles de su cuenta:</h3>
            <ul>
              <li><strong>Email:</strong> {to_email}</li>
              <li><strong>VNI Cliente:</strong> {vni}</li>
            </ul>
            
            <p>Su infraestructura está siendo configurada y estará disponible pronto.</p>
            
            <h3>Establecer su contraseña</h3>
            <p>Para completar su registro, por favor establezca su contraseña haciendo clic en el siguiente enlace:</p>
            <p><a href="{setup_password_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Establecer Contraseña</a></p>
            <p style="color: #666; font-size: 12px;">O copie y pegue esta URL en su navegador:</p>
            <p style="color: #666; font-size: 12px; word-break: break-all;">{setup_password_url}</p>
            <p style="color: #999; font-size: 11px;"><strong>Nota:</strong> Este enlace expirará en 7 días por razones de seguridad.</p>
            
            <p>Saludos,<br>Equipo de Seguridad</p>
            """
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Email de bienvenida enviado a {to_email} (ID: {result.get('id', 'N/A')})")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error enviando email a {to_email}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Respuesta: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado enviando email a {to_email}: {e}")
            return False


# Instancia global
email_service = EmailService()


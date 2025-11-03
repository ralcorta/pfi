import os
import requests
from typing import Optional

from app.sensor.src.utils.environment import env


class EmailService:
    
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY", "")
        self.from_email = env.email_from_address
        self.enabled = env.email_enabled
        
        if not self.enabled:
            print("Email sending disabled (EMAIL_ENABLED=false)")
        elif not self.api_key:
            print("RESEND_API_KEY not configured, emails disabled")
    
    def send_welcome_email(self, to_email: str, vni: int, password_token: str) -> bool:
        if not self.enabled or not self.api_key:
            return False
        
        if not self.from_email:
            print(f"EMAIL_FROM_ADDRESS not configured, skipping email sending")
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
            print(f"Welcome email sent to {to_email} (ID: {result.get('id', 'N/A')})")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error sending email to {to_email}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"Error unexpected sending email to {to_email}: {e}")
            return False
    
    def send_malware_alert_email(self, to_email: str, vni: int, detection_details: dict) -> bool:
        if not self.enabled or not self.api_key:
            return False
        
        if not self.from_email:
            print(f"EMAIL_FROM_ADDRESS not configured, skipping email sending")
            return False
        
        malware_prob = detection_details.get('malware_probability', 0.0)
        src_ip = detection_details.get('src_ip', 'N/A')
        dst_ip = detection_details.get('dst_ip', 'N/A')
        src_port = detection_details.get('src_port', 'N/A')
        dst_port = detection_details.get('dst_port', 'N/A')
        protocol = detection_details.get('protocol', 'N/A')
        
        timestamp = detection_details.get('timestamp', 0)
        if timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(timestamp / 1000)
                timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp_str = str(timestamp)
        else:
            timestamp_str = 'N/A'
        
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        if malware_prob >= 0.9:
            severity = "CRÍTICA"
            severity_color = "#d32f2f"
        elif malware_prob >= 0.7:
            severity = "ALTA"
            severity_color = "#f57c00"
        else:
            severity = "MEDIA"
            severity_color = "#fbc02d"
        
        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": f"🚨 ALERTA: Malware Detectado (VNI: {vni})",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f; border-bottom: 3px solid #d32f2f; padding-bottom: 10px;">
                    🚨 Alerta de Detección de Malware
                </h2>
                
                <div style="background-color: #ffebee; border-left: 4px solid {severity_color}; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 16px; font-weight: bold;">
                        Severidad: <span style="color: {severity_color};">{severity}</span>
                    </p>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">
                        Probabilidad de malware: <strong>{(malware_prob * 100):.1f}%</strong>
                    </p>
                </div>
                
                <h3 style="color: #333; margin-top: 30px;">Detalles de la Detección</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <td style="padding: 8px; background-color: #f5f5f5; font-weight: bold; width: 40%;">VNI Cliente:</td>
                        <td style="padding: 8px;">{vni}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #f5f5f5; font-weight: bold;">Origen:</td>
                        <td style="padding: 8px;">{src_ip}:{src_port}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #f5f5f5; font-weight: bold;">Destino:</td>
                        <td style="padding: 8px;">{dst_ip}:{dst_port}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #f5f5f5; font-weight: bold;">Protocolo:</td>
                        <td style="padding: 8px;">{protocol}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; background-color: #f5f5f5; font-weight: bold;">Fecha y Hora:</td>
                        <td style="padding: 8px;">{timestamp_str}</td>
                    </tr>
                </table>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px;">
                    <p style="margin: 0; font-size: 14px;">
                        <strong>⚠️ Acción Recomendada:</strong><br>
                        Revise el tráfico de red de su infraestructura y tome las medidas necesarias según su política de seguridad.
                    </p>
                </div>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    Puede ver más detalles de esta y otras detecciones en el dashboard del sistema.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                <p style="color: #999; font-size: 11px;">
                    Este es un mensaje automático del Sistema de Detección de Ransomware.
                    Por favor, no responda a este email.
                </p>
            </div>
            """
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            print(f"Malware alert email sent to {to_email} (ID: {result.get('id', 'N/A')})")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error sending malware alert email to {to_email}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"Error unexpected sending malware alert email to {to_email}: {e}")
            return False


email_service = EmailService()


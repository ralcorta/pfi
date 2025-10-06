#!/usr/bin/env python3
"""
Configuración de documentación web automática para la API
"""
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
import json

def setup_docs_endpoints(app: FastAPI):
    """
    Configura endpoints adicionales para documentación web
    Sin modificar las funciones existentes
    """
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Documentación interactiva con Swagger UI mejorado"""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Documentación",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            init_oauth=app.swagger_ui_init_oauth,
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Documentación alternativa con ReDoc"""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi():
        """Esquema OpenAPI en formato JSON"""
        return get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

    @app.get("/api-docs", include_in_schema=False)
    async def api_docs_landing():
        """Página de aterrizaje para la documentación"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - Documentación</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .docs-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-top: 30px;
                }}
                .doc-card {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    text-decoration: none;
                    color: #333;
                    transition: transform 0.2s;
                }}
                .doc-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .doc-card h3 {{
                    margin: 0 0 10px 0;
                    color: #007bff;
                }}
                .doc-card p {{
                    margin: 0;
                    color: #666;
                }}
                .info {{
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    border-left: 4px solid #2196f3;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ {app.title}</h1>
                <div class="info">
                    <strong>Versión:</strong> {app.version}<br>
                    <strong>Descripción:</strong> {app.description}
                </div>
                
                <h2>📚 Documentación Disponible</h2>
                <div class="docs-grid">
                    <a href="/docs" class="doc-card">
                        <h3>🔍 Swagger UI</h3>
                        <p>Documentación interactiva con pruebas en vivo</p>
                    </a>
                    
                    <a href="/redoc" class="doc-card">
                        <h3>📖 ReDoc</h3>
                        <p>Documentación alternativa con mejor legibilidad</p>
                    </a>
                    
                    <a href="/openapi.json" class="doc-card">
                        <h3>📋 OpenAPI Schema</h3>
                        <p>Esquema JSON de la API</p>
                    </a>
                    
                    <a href="/health" class="doc-card">
                        <h3>💚 Health Check</h3>
                        <p>Verificar estado del sistema</p>
                    </a>
                </div>
                
                <div class="info">
                    <strong>💡 Tip:</strong> Usa Swagger UI para probar los endpoints directamente desde el navegador
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

def enhance_openapi_schema(app: FastAPI):
    """
    Mejora el esquema OpenAPI con información adicional
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Agregar información adicional
        openapi_schema["info"]["contact"] = {
            "name": "Equipo de Desarrollo",
            "email": "dev@example.com",
        }
        
        openapi_schema["info"]["license"] = {
            "name": "MIT License",
        }
        
        # Agregar servidores
        openapi_schema["servers"] = [
            {
                "url": "http://sensor-api-alb-802948491.us-east-1.elb.amazonaws.com",
                "description": "Servidor de Producción AWS"
            },
            {
                "url": "http://localhost:8080",
                "description": "Servidor de Desarrollo Local"
            }
        ]
        
        # Agregar tags con descripciones
        openapi_schema["tags"] = [
            {
                "name": "health",
                "description": "Endpoints de verificación de salud del sistema"
            },
            {
                "name": "detections",
                "description": "Endpoints para consultar detecciones de malware"
            },
            {
                "name": "stats",
                "description": "Endpoints para estadísticas y métricas"
            },
            {
                "name": "demo",
                "description": "Endpoints para controlar el modo demo"
            },
            {
                "name": "testing",
                "description": "Endpoints para testing y verificación de permisos"
            }
        ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

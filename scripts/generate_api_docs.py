#!/usr/bin/env python3
"""
Script para generar documentación automática de la API
"""
import json
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.sensor.src.http_server import HTTPServer

def generate_openapi_schema():
    """Genera el esquema OpenAPI de la API"""
    print("🔄 Generando esquema OpenAPI...")
    
    # Crear instancia del servidor HTTP
    http_server = HTTPServer()
    
    # Obtener el esquema OpenAPI
    openapi_schema = http_server.app.openapi()
    
    # Guardar el esquema en un archivo JSON
    docs_dir = root_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    schema_file = docs_dir / "openapi.json"
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Esquema OpenAPI guardado en: {schema_file}")
    return openapi_schema

def generate_markdown_docs():
    """Genera documentación en Markdown"""
    print("🔄 Generando documentación en Markdown...")
    
    # Obtener el esquema OpenAPI
    openapi_schema = generate_openapi_schema()
    
    # Generar documentación en Markdown
    docs_dir = root_dir / "docs"
    markdown_file = docs_dir / "API_DOCUMENTATION.md"
    
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(f"# {openapi_schema['info']['title']}\n\n")
        f.write(f"**Versión**: {openapi_schema['info']['version']}\n\n")
        f.write(f"**Descripción**: {openapi_schema['info']['description']}\n\n")
        
        # Servidores
        if 'servers' in openapi_schema:
            f.write("## 🌐 Servidores\n\n")
            for server in openapi_schema['servers']:
                f.write(f"- **{server['description']}**: `{server['url']}`\n")
            f.write("\n")
        
        # Tags
        if 'tags' in openapi_schema:
            f.write("## 📋 Categorías de Endpoints\n\n")
            for tag in openapi_schema['tags']:
                f.write(f"### {tag['name'].title()}\n")
                f.write(f"{tag['description']}\n\n")
        
        # Endpoints por tag
        if 'paths' in openapi_schema:
            f.write("## 🔗 Endpoints\n\n")
            
            # Agrupar endpoints por tag
            endpoints_by_tag = {}
            for path, methods in openapi_schema['paths'].items():
                for method, details in methods.items():
                    if 'tags' in details and details['tags']:
                        tag = details['tags'][0]
                        if tag not in endpoints_by_tag:
                            endpoints_by_tag[tag] = []
                        endpoints_by_tag[tag].append((path, method, details))
            
            # Escribir endpoints por tag
            for tag, endpoints in endpoints_by_tag.items():
                f.write(f"### {tag.title()}\n\n")
                
                for path, method, details in endpoints:
                    f.write(f"#### `{method.upper()} {path}`\n\n")
                    f.write(f"**{details.get('summary', 'Sin resumen')}**\n\n")
                    
                    if 'description' in details:
                        f.write(f"{details['description']}\n\n")
                    
                    # Parámetros
                    if 'parameters' in details:
                        f.write("**Parámetros:**\n\n")
                        for param in details['parameters']:
                            f.write(f"- `{param['name']}` ({param.get('schema', {}).get('type', 'unknown')}): {param.get('description', 'Sin descripción')}\n")
                        f.write("\n")
                    
                    # Respuestas
                    if 'responses' in details:
                        f.write("**Respuestas:**\n\n")
                        for status_code, response in details['responses'].items():
                            f.write(f"- `{status_code}`: {response.get('description', 'Sin descripción')}\n")
                        f.write("\n")
                    
                    f.write("---\n\n")
    
    print(f"✅ Documentación Markdown guardada en: {markdown_file}")

def generate_html_docs():
    """Genera documentación HTML usando Swagger UI"""
    print("🔄 Generando documentación HTML...")
    
    # Obtener el esquema OpenAPI
    openapi_schema = generate_openapi_schema()
    
    # Generar HTML con Swagger UI embebido
    docs_dir = root_dir / "docs"
    html_file = docs_dir / "index.html"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{openapi_schema['info']['title']} - Documentación</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: './openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                tryItOutEnabled: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
                docExpansion: 'list',
                defaultModelsExpandDepth: 3,
                defaultModelExpandDepth: 3
            }});
        }};
    </script>
</body>
</html>
"""
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Documentación HTML guardada en: {html_file}")

def main():
    """Función principal"""
    print("🚀 Generando documentación automática de la API...")
    print("=" * 60)
    
    try:
        # Generar todos los tipos de documentación
        generate_openapi_schema()
        generate_markdown_docs()
        generate_html_docs()
        
        print("\n" + "=" * 60)
        print("✅ ¡Documentación generada exitosamente!")
        print("\n📁 Archivos generados:")
        print("   - docs/openapi.json (Esquema OpenAPI)")
        print("   - docs/API_DOCUMENTATION.md (Documentación Markdown)")
        print("   - docs/index.html (Documentación HTML con Swagger UI)")
        
        print("\n🌐 URLs de acceso:")
        print("   - Local: http://localhost:8080/docs")
        print("   - AWS: http://sensor-api-alb-802948491.us-east-1.elb.amazonaws.com/docs")
        print("   - HTML: Abre docs/index.html en tu navegador")
        
    except Exception as e:
        print(f"❌ Error generando documentación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

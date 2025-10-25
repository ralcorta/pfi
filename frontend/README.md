# Malware Detection Dashboard

Frontend Vue.js para visualizar las detecciones de malware almacenadas en DynamoDB a través de la API REST.

## 🚀 Características

- **Dashboard en tiempo real** - Visualización de detecciones de malware
- **Estadísticas** - Contadores de detecciones activas/inactivas, IPs únicas, etc.
- **Control de Demo** - Iniciar/detener demos de detección
- **Auto-refresh** - Actualización automática cada 5 segundos
- **Responsive** - Diseño adaptativo para móviles y desktop
- **Modal de detalles** - Vista detallada de cada detección

## 🛠️ Instalación

```bash
# Instalar dependencias
npm install

# Desarrollo
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview
```

## 🔧 Configuración

### Variables de entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
# Para desarrollo local (usa proxy)
VITE_API_URL=/api

# Para producción (usa URL del ALB)
VITE_API_URL=http://your-alb-dns-name.us-east-1.elb.amazonaws.com
```

### Proxy de desarrollo

El archivo `vite.config.js` está configurado para hacer proxy de `/api/*` a `http://localhost:8080/*` durante el desarrollo.

## 📡 API Endpoints

El frontend consume los siguientes endpoints:

- `GET /detections` - Obtener todas las detecciones
- `GET /detections/{id}` - Obtener detección específica
- `GET /health` - Health check de la API
- `POST /demo/start` - Iniciar demo
- `POST /demo/stop` - Detener demo
- `POST /demo/toggle` - Alternar demo

## 🎨 Componentes

- **App.vue** - Componente principal con lógica de estado
- **StatsCards.vue** - Tarjetas de estadísticas
- **DetectionTable.vue** - Tabla de detecciones
- **DetectionCard.vue** - Tarjeta individual de detección

## 📱 Responsive Design

- **Desktop** - Vista completa con tabla y estadísticas
- **Mobile** - Vista optimizada con tarjetas y controles adaptativos

## 🔄 Auto-refresh

- Actualización automática cada 5 segundos
- Se puede activar/desactivar con el botón correspondiente
- Muestra notificaciones de estado

## 🚀 Deployment

### Desarrollo local

```bash
npm run dev
```

Accede a `http://localhost:3000`

### Producción

```bash
npm run build
npm run serve
```

O sirve los archivos estáticos desde el directorio `dist/` con cualquier servidor web.

## 🔗 Integración con AWS

Para conectar con tu API desplegada en AWS:

1. Obtén la URL del ALB desde Terraform
2. Actualiza `VITE_API_URL` en tu archivo `.env`
3. Rebuild y deploy

```bash
# Ejemplo de URL del ALB
VITE_API_URL=http://sensor-api-alb-123456789.us-east-1.elb.amazonaws.com
```

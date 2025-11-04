# Arquitectura del Sistema de Análisis de Tráfico

Este documento describe la arquitectura completa del sistema, cómo se comunican los componentes y el flujo de datos desde que el tráfico es capturado hasta que se analiza.

## Visión General

El sistema está diseñado para analizar tráfico de red en tiempo real usando AWS Traffic Mirroring. Permite que múltiples clientes (cada uno en su propia VPC) envíen una copia de su tráfico a un analizador centralizado que procesa, detecta amenazas y almacena los resultados.

La arquitectura es completamente serverless en el lado del analizador (usa ECS Fargate), lo que elimina la necesidad de gestionar servidores. En el lado del cliente, **cualquier servicio que se conecte a través de una Elastic Network Interface (ENI) configurada puede tener su tráfico espejado**. Aunque en los ejemplos se muestra una instancia EC2, en producción pueden ser servidores web, bases de datos, contenedores, servicios ECS, o cualquier otro recurso de AWS que genere tráfico de red.

## Componentes Principales

### 1. VPC del Analizador

La VPC del analizador (`10.10.0.0/16` por defecto) contiene todos los componentes del sistema de análisis:

- **ECS Cluster**: Cluster Fargate que ejecuta el contenedor del sensor
- **Network Load Balancer (NLB) interno**: Recibe el tráfico espejado encapsulado en VXLAN
- **Network Load Balancer (NLB) público**: Expone la API HTTP del sensor (puerto 80 → 8080)
- **Traffic Mirror Target**: Punto de recepción para el tráfico espejado de los clientes
- **Transit Gateway**: Conecta las VPCs del analizador y los clientes
- **Bucket S3**: Almacena el dashboard frontend estático

### 2. VPC del Cliente

Cada cliente tiene su propia VPC (`10.20.0.0/16` por defecto, pero puede variar):

- **Elastic Network Interface (ENI)**: Interfaz de red a la que se conectan los servicios del cliente. **Nota importante**: Aunque en los ejemplos y la configuración de Terraform se usa una instancia EC2 para demostración, en producción cualquier servicio del cliente puede conectarse a esta ENI (servidores web, bases de datos, contenedores, servicios ECS, etc.). El tráfico que pase por esta ENI será automáticamente espejado.
- **Traffic Mirror Session**: Configuración que indica qué tráfico espejar y hacia dónde. Se vincula a la ENI específica.
- **Traffic Mirror Filter**: Reglas que definen qué paquetes capturar (TCP/UDP, ingress/egress)
- **Transit Gateway Attachment**: Conexión al Transit Gateway para comunicación entre VPCs

**Sobre la ENI y los servicios del cliente**: La arquitectura está diseñada para que cualquier recurso de AWS que use la ENI configurada (ya sea una EC2, un contenedor ECS, una Lambda con VPC, o cualquier otro servicio) tenga su tráfico espejado automáticamente. La instancia EC2 en los ejemplos es solo una representación simplificada; en la práctica, el cliente puede tener múltiples servicios conectados a diferentes ENIs, y cada una puede tener su propia Traffic Mirror Session configurada.

### 3. Servicio ECS (Sensor)

El contenedor del sensor es el corazón del sistema:

- **Escucha VXLAN**: Recibe tráfico encapsulado en el puerto UDP 4789
- **Procesamiento**: Desencapsula VXLAN, analiza paquetes, detecta patrones sospechosos
- **API REST**: Expone endpoints HTTP en el puerto 8080 para gestión y consulta
- **Almacenamiento**: Guarda detecciones en DynamoDB

### 4. Dashboard Frontend

Aplicación web estática servida desde S3:

- **Autenticación**: Login con JWT
- **Visualización**: Muestra detecciones
- **Gestión de usuarios**: Registro de clientes

## Flujo de Comunicación

### 1. Registro de Cliente

Cuando un nuevo cliente necesita conectarse al sistema:

```
Cliente → API del Analizador (GET /v1/clients/terraform-config?email=...)
    ↓
API consulta/crea usuario en DynamoDB
    ↓
API asigna VNI único (3001, 3002, 3003, ...)
    ↓
API retorna: { traffic_mirror_target_id, vni_cliente }
    ↓
Terraform del cliente usa estos valores para crear la Traffic Mirror Session
```

**Endpoint de la API**: `GET http://<nlb-dns>/v1/clients/terraform-config?email=<email>`

**Respuesta**:

```json
{
  "email": "cliente@example.com",
  "vni_cliente": 3001,
  "traffic_mirror_target_id": "tmt-0abc123def456",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Flujo de Tráfico Espejado

Una vez configurado, el tráfico fluye automáticamente:

```
1. Servicio del cliente (EC2, ECS, base de datos, etc.) genera tráfico de red
   (HTTP, HTTPS, SSH, conexiones de base de datos, etc.) a través de la ENI
   ↓
2. AWS Traffic Mirroring intercepta el tráfico según las reglas del Filter
   ↓
3. El tráfico se encapsula en VXLAN con el VNI del cliente
   ↓
4. Paquetes VXLAN se envían por UDP al puerto 4789 del NLB interno
   ↓
5. NLB interno distribuye el tráfico a las tareas ECS del sensor
   ↓
6. Contenedor del sensor recibe VXLAN en puerto 4789/UDP
   ↓
7. Sensor desencapsula VXLAN y extrae el tráfico original
   ↓
8. Sensor analiza paquetes buscando patrones de ransomware/malware
   ↓
9. Si detecta algo, guarda en DynamoDB (tabla "detections")
   ↓
10. El tráfico original continúa normalmente (no es interceptado, solo espejado)
```

**Punto importante**: El tráfico espejado es una copia. El tráfico original sigue su curso normal sin interrupciones. Esto es clave para no afectar la operación del cliente.

**Sobre los servicios del cliente**: La Traffic Mirror Session se configura a nivel de ENI (Elastic Network Interface), no a nivel de instancia o servicio específico. Esto significa que cualquier tráfico que pase por esa ENI será automáticamente espejado, independientemente de qué servicio lo genere. Por ejemplo:

- Si tienes una instancia EC2 con una aplicación web, el tráfico HTTP/HTTPS será espejado
- Si tienes un servicio ECS con múltiples contenedores usando la misma ENI, todo su tráfico será espejado
- Si tienes una base de datos RDS o un servicio ElastiCache conectado a través de la ENI, ese tráfico también será espejado
- Si tienes múltiples servicios en la misma VPC, cada uno puede tener su propia ENI con su propia Traffic Mirror Session configurada

En resumen, el sistema funciona con cualquier recurso de AWS que genere tráfico de red a través de una ENI configurada. La instancia EC2 en los ejemplos de Terraform es solo una forma simple de demostrar el concepto.

### 3. Comunicación API

El dashboard y otras herramientas se comunican con el sensor vía HTTP:

```
Dashboard/Cliente → NLB Público (Puerto 80)
    ↓
NLB Público → ECS Task (Puerto 8080)
    ↓
Sensor procesa request (autenticación, consultas, etc.)
    ↓
Sensor consulta/actualiza DynamoDB
    ↓
Sensor retorna respuesta JSON
    ↓
NLB Público → Dashboard/Cliente
```

**Endpoints principales**:

- `GET /v1/clients/terraform-config` - Configuración para Terraform
- `GET /detections` - Lista de detecciones (requiere autenticación)
- `POST /v1/users/register` - Registro de usuarios
- `POST /v1/users/login` - Autenticación

### 4. Comunicación entre VPCs

El Transit Gateway permite que las VPCs se comuniquen:

```
Cliente VPC (10.20.0.0/16)
    ↓
Transit Gateway
    ↓
Analizador VPC (10.10.0.0/16)
```

**Uso del Transit Gateway**:

- Permite que el cliente consulte la API del analizador sin salir a internet
- Facilita la gestión y monitoreo
- Facilita el multi tenant entre usuarios y la vpc del sensor (funciona por la red de AWS)

## Tecnologías y Protocolos

### VXLAN (Virtual eXtensible LAN)

VXLAN es un protocolo de encapsulación que permite crear redes virtuales sobre infraestructura física. En este sistema:

- **Puerto**: UDP 4789 (puerto estándar de VXLAN)
- **VNI (Virtual Network Identifier)**: Identificador único por cliente (rango 1-16777215)
- **Propósito**: Permite que múltiples clientes envíen tráfico al mismo destino sin conflictos. El VNI actúa como una "etiqueta" que identifica de qué cliente proviene cada paquete.

Cuando AWS Traffic Mirroring espeja tráfico, automáticamente lo encapsula en VXLAN antes de enviarlo al target. El sensor debe desencapsular para obtener el tráfico original.

### AWS Traffic Mirroring

Servicio de AWS que permite duplicar (espejar) tráfico de red sin afectar el flujo original:

- **Traffic Mirror Session**: Define qué interfaz de red espejar y hacia qué target enviar
- **Traffic Mirror Filter**: Reglas que definen qué paquetes capturar (protocolo, puertos, direcciones)
- **Traffic Mirror Target**: Destino del tráfico espejado (en este caso, un NLB)

**Características importantes**:

- El tráfico original no se ve afectado
- Solo se espeja tráfico que cumple con las reglas del filter
- El tráfico se encapsula automáticamente en VXLAN
- Funciona a nivel de ENI (Elastic Network Interface)

### ECS Fargate

Plataforma serverless de contenedores de AWS:

- **Ventaja**: No necesitas gestionar servidores EC2
- **Escalado**: Puedes configurar múltiples tareas para distribuir carga
- **Red**: Cada tarea obtiene su propia IP privada en la VPC
- **Health Checks**: El NLB verifica que las tareas estén saludables en el puerto 8080

### Network Load Balancer (NLB)

Hay dos NLBs en el sistema:

1. **NLB Interno (mirror_nlb)**:

   - Tipo: Internal (no tiene IP pública)
   - Puerto: 4789/UDP
   - Target: ECS Tasks (puerto 4789)
   - Propósito: Recibir tráfico espejado

2. **NLB Público (app_nlb)**:
   - Tipo: Internet-facing
   - Puerto: 80/TCP → 8080/TCP
   - Target: ECS Tasks (puerto 8080)
   - Propósito: Exponer la API HTTP

Los NLBs son de capa 4 (no hacen SSL/TLS termination), así que son rápidos y eficientes para este tipo de carga.

## Seguridad y Aislamiento

### Aislamiento por Cliente

Cada cliente tiene su propio VNI, lo que permite:

- Identificar de qué cliente proviene cada detección
- Aislar visualmente el tráfico en el dashboard
- Mantener la privacidad entre clientes
- Escalar agregando más clientes sin conflictos

### Security Groups

Los security groups controlan el acceso:

- **ECS Security Group**: Permite UDP/4789 desde cualquier origen (para recibir VXLAN) y TCP/8080 para health checks
- **Client Security Group**: Permite SSH (22), HTTP (80), HTTPS (443) según necesidades del cliente

### Autenticación

La API usa JWT (JSON Web Tokens):

- Los usuarios se autentican con email y contraseña
- El servidor genera un token JWT firmado
- El token se incluye en las requests subsiguientes
- El token expira después de un tiempo configurable (por defecto 1440 minutos = 24 horas)

## Escalabilidad

### Escalar el Analizador

Para manejar más carga:

1. **Aumentar tareas ECS**: Cambiar `desired_count` en el servicio ECS
2. **Aumentar recursos**: Ajustar CPU/memoria de las tareas (actualmente 1024 CPU / 2048 MB)
3. **Distribución geográfica**: Desplegar analizadores en múltiples regiones

El NLB distribuye automáticamente el tráfico entre todas las tareas saludables.

### Agregar Más Clientes

Para agregar clientes:

1. Registrar el email del cliente (vía API o dashboard)
2. Desplegar el módulo Terraform del cliente con ese email
3. El sistema automáticamente asigna un VNI único

No hay límite práctico en el número de clientes, siempre que los CIDRs de las VPCs no se solapen.

## Almacenamiento de Datos

### DynamoDB

El sistema usa dos tablas de DynamoDB:

1. **`detections`**: Almacena las detecciones de amenazas

   - Clave de partición: ID único de detección
   - Atributos: timestamp, cliente (email), tipo de amenaza, detalles del tráfico, etc.

2. **`users`**: Almacena información de usuarios/clientes
   - Clave de partición: Email del usuario
   - Atributos: VNI asignado, traffic_mirror_target_id, fecha de creación, etc.

### S3 (Dashboard)

El dashboard frontend es una Single Page Application (SPA) estática:

- Se compila localmente con las variables de entorno correctas
- Se sube a S3 con website hosting habilitado
- Se accede vía HTTP desde el endpoint público de S3

## Consideraciones de Red

### CIDRs por Defecto

- **Analizador**: `10.10.0.0/16`
- **Cliente**: `10.20.0.0/16`

Si despliegas múltiples clientes, debes ajustar los CIDRs para evitar conflictos. Por ejemplo:

- Cliente 1: `10.20.0.0/16`
- Cliente 2: `10.21.0.0/16`
- Cliente 3: `10.22.0.0/16`

### Rutas del Transit Gateway

El Transit Gateway crea automáticamente rutas entre las VPCs conectadas:

- Cada VPC de cliente tiene rutas hacia la VPC del analizador
- Las VPCs de clientes NO tienen rutas entre sí (aislamiento)

## Monitoreo y Logs

### CloudWatch Logs

El contenedor del sensor envía logs a CloudWatch:

- **Log Group**: `/ecs/sensor-analyzer-sensor`
- **Retención**: 7 días (configurable)
- **Contenido**: Logs de la aplicación, errores, estadísticas de procesamiento

## Flujo Completo de un Paquete

Para entender mejor cómo funciona todo junto, aquí está el viaje completo de un paquete:

```
1. Servicio del cliente (ej: aplicación web, EC2, base de datos, etc.)
   genera tráfico de red (ej: curl https://example.com, conexión a API, etc.)
   │
   ├─> Tráfico original va a internet normalmente
   │
   └─> AWS Traffic Mirroring captura una copia
       │
       ├─> Aplica Traffic Mirror Filter (¿es TCP/UDP? ¿cumple reglas?)
       │
       ├─> Si pasa el filter, encapsula en VXLAN con VNI=3001
       │
       ├─> Envía por UDP al NLB interno (puerto 4789)
       │
       ├─> NLB distribuye a una tarea ECS
       │
       ├─> Contenedor recibe VXLAN en puerto 4789
       │
       ├─> Sensor desencapsula VXLAN
       │
       ├─> Analiza el paquete TCP original
       │
       ├─> Detecta patrón sospechoso (ej: conexión a dominio conocido de ransomware)
       │
       ├─> Guarda detección en DynamoDB
       │
       └─> Envía notificación por email configurado
```

Todo esto sucede en paralelo con el tráfico original, que sigue su curso sin saber que fue espejado.

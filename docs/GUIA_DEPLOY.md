# Guía de Despliegue de Infraestructura

Esta guía explica cómo desplegar la infraestructura completa del sistema de análisis de tráfico. El proyecto está dividido en dos módulos de Terraform que deben desplegarse en orden: primero el analizador y luego los clientes.

## Prerrequisitos

Antes de empezar, asegúrate de tener:

- Terraform instalado (versión 1.0 o superior)
- AWS CLI configurado con credenciales válidas
- Acceso a una cuenta de AWS con permisos suficientes para crear VPCs, EC2, ECS, Load Balancers, etc.
- Una clave SSH existente en AWS (o crear una nueva)
- Docker (necesario si usas los scripts automatizados, o si vas a construir la imagen del sensor manualmente)
- Node.js y npm (necesario si usas los scripts para desplegar el dashboard, o si lo construyes manualmente)

## Arquitectura General

El sistema consta de dos VPCs separadas:

1. **VPC del Analizador**: Contiene el servicio ECS que procesa el tráfico duplicado, el Network Load Balancer que recibe el tráfico espejado, y el Transit Gateway para conectar ambas VPCs.

2. **VPC del Cliente**: Contiene una instancia EC2 que envía su tráfico al analizador mediante AWS Traffic Mirroring. Puede haber múltiples clientes, cada uno con su propia VPC.

Las VPCs se conectan a través de un Transit Gateway, y el tráfico se espeja desde las instancias cliente hacia el analizador usando VXLAN sobre UDP en el puerto 4789.

## Método de Despliegue

Hay dos formas de desplegar la infraestructura:

1. **Despliegue automatizado con scripts** (recomendado): Usa los scripts en la carpeta `scripts/` que automatizan todo el proceso.
2. **Despliegue manual con Terraform**: Ejecutas los comandos de Terraform manualmente paso a paso.

### Despliegue Automatizado con Scripts

Si prefieres automatizar todo el proceso, puedes usar los scripts que están en la carpeta `scripts/`. Estos scripts se encargan de ejecutar todos los pasos necesarios en el orden correcto.

#### Despliegue Completo Automático

Para desplegar todo de una vez (analizador, imagen del sensor, dashboard y cliente):

```bash
cd scripts
chmod +x *.sh
./00-run-all.sh
```

Este script ejecuta secuencialmente:

1. Despliegue del analizador con Terraform
2. Construcción y subida de la imagen del sensor a ECR
3. Compilación y despliegue del dashboard en S3
4. Despliegue del cliente con Terraform
5. Envío de tráfico de prueba (opcional)

#### Despliegue Paso a Paso

Si prefieres ejecutar cada paso por separado, puedes usar los scripts individuales:

```bash
# 1. Desplegar el analizador
./01-deploy-analizer.sh

# 2. Subir la imagen del sensor a ECR
./02-push-sensor-image.sh

# 3. Desplegar el dashboard en S3
./03-deploy-dashboard.sh

# 4. Desplegar el cliente
./04-deploy-client.sh
```

**Ventajas de usar los scripts:**

- Automatizan tareas repetitivas (login a ECR, construcción de imágenes, etc.)
- Validan que los prerrequisitos estén cumplidos
- Muestran mensajes claros de progreso
- Manejan errores y detienen el proceso si algo falla
- Actualizan automáticamente el servicio ECS cuando subes una nueva imagen

**Nota importante**: Los scripts asumen que los archivos `terraform.tfvars` ya están configurados correctamente en `terraform/analizer/` y `terraform/client/`. Asegúrate de revisar y ajustar esos archivos antes de ejecutar los scripts, especialmente el `client_email` en el módulo cliente.

Si prefieres tener más control sobre cada paso o entender mejor qué está pasando, puedes seguir con el despliegue manual que se explica a continuación.

## Despliegue Manual con Terraform

Si prefieres hacer el despliegue manualmente o los scripts no se adaptan a tu caso, puedes seguir estos pasos:

## Despliegue del Analizador

El módulo `analizer` debe desplegarse primero, ya que los clientes dependen de sus outputs (especialmente el Traffic Mirror Target ID y la URL de la API).

### Paso 1: Configurar las variables

Ve al directorio del analizador y edita el archivo `terraform.tfvars`:

```bash
cd terraform/analizer
```

Las variables más importantes que debes revisar:

- `aws_region`: La región donde desplegar (por defecto `us-east-1`)
- `account_id`: Tu Account ID de AWS
- `availability_zone_1` y `availability_zone_2`: Las zonas de disponibilidad que quieres usar
- `key_name`: Nombre de la clave SSH que usarás para acceder a instancias (si las necesitas)
- `jwt_secret_key`: **IMPORTANTE**: Cambia esto por una clave segura en producción. Úsala para generar tokens JWT.
- `enable_email_service`: Si quieres habilitar el envío de emails (requiere configuración de Resend)
- `resend_api_key` y `email_from_address`: Solo necesarios si `enable_email_service` es `true`

El resto de variables (como los CIDRs de las VPCs) tienen valores por defecto razonables, pero puedes ajustarlos si tienes conflictos con tu red existente.

### Paso 2: Inicializar Terraform

```bash
terraform init
```

Esto descargará los providers necesarios (AWS principalmente).

### Paso 3: Revisar el plan

Antes de desplegar, siempre es buena idea ver qué recursos se van a crear:

```bash
terraform plan
```

Revisa que los recursos propuestos sean los esperados. Deberías ver:

- Una VPC con subnets públicas y privadas
- Un ECS cluster con task definition
- Dos Network Load Balancers (uno interno para mirroring, uno público para la API)
- Un Transit Gateway
- Un bucket S3 para el dashboard
- Security groups, route tables, etc.

### Paso 4: Desplegar

Si todo se ve bien, aplica los cambios:

```bash
terraform apply
```

Terraform te pedirá confirmación. Esto puede tardar varios minutos (especialmente la creación del servicio ECS y el registro de la imagen en ECR si es la primera vez).

### Paso 5: Verificar los outputs

Una vez completado el despliegue, anota los outputs importantes:

```bash
terraform output
```

Los outputs más relevantes son:

- `traffic_mirror_target_id`: Este ID es necesario para que los clientes puedan configurar sus sesiones de mirroring. Se usa automáticamente por la API.
- `app_nlb_dns`: La URL del Network Load Balancer público donde está expuesta la API.
- `api_base_url`: La URL completa de la API (por defecto usa el NLB DNS).
- `transit_gateway_id`: ID del Transit Gateway (se usa automáticamente por los clientes si no lo especificas).
- `vpc_analizador_cidr`: El CIDR de la VPC del analizador (también se usa automáticamente).

### Paso 6: Subir la imagen del sensor

El despliegue crea el repositorio ECR, pero necesitas subir la imagen del contenedor. Si ya tienes la imagen construida:

```bash
# Obtén la URL del repositorio
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag de la imagen
docker tag mirror-sensor:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest
```

Reemplaza `<account-id>` con tu Account ID de AWS.

Una vez que la imagen esté en ECR, el servicio ECS debería iniciarla automáticamente. Puedes verificar en la consola de AWS que el servicio esté corriendo y que las tareas estén saludables.

### Notas sobre el módulo analizador

- El servicio ECS usa Fargate, así que no necesitas gestionar servidores.
- El dashboard se sirve desde un bucket S3 con website hosting habilitado. La URL se genera automáticamente.
- Si necesitas cambiar la configuración del contenedor (variables de entorno), edita `main.tf` en la sección de `container_definitions` y vuelve a aplicar.

## Despliegue del Cliente

Una vez que el analizador esté desplegado y funcionando (especialmente la API), puedes desplegar clientes. Cada cliente necesita su propia instancia de este módulo.

### Paso 1: Configurar las variables

Ve al directorio del cliente:

```bash
cd terraform/client
```

Edita `terraform.tfvars`. Las variables esenciales son:

- `client_email`: El email del cliente. **Este debe estar registrado previamente en el dashboard del analizador**. La API usa este email para asignar automáticamente un VNI único y obtener la configuración.
- `key_name`: La clave SSH para acceder a la instancia EC2.
- `client_ami_id`: El AMI ID de la instancia. Por defecto usa Amazon Linux 2 en us-east-1.

Las variables opcionales que puedes omitir (se obtienen automáticamente del remote state del analizador):

- `api_url`: Si no la especificas, se obtiene del estado del analizador.
- `transit_gateway_id`: Se obtiene automáticamente del analizador.
- `vpc_1_cidr`: Se obtiene automáticamente del analizador.

### Paso 2: Registrar el cliente en el dashboard

**IMPORTANTE**: Antes de desplegar el cliente con Terraform, el email del cliente debe estar registrado en el sistema. Tienes dos opciones:

1. Usar la API directamente para registrar el cliente.
2. Usar el dashboard web (si está disponible).

La API asignará automáticamente un VNI (Virtual Network Identifier) único para ese cliente. Este VNI se usa para encapsular el tráfico espejado y permite que el analizador distinga el tráfico de diferentes clientes.

### Paso 3: Inicializar Terraform

```bash
terraform init
```

### Paso 4: Revisar el plan

```bash
terraform plan
```

Deberías ver que:

- Se crea una nueva VPC para el cliente
- Se crea una instancia EC2
- Se configura un Traffic Mirror Filter con reglas para TCP y UDP
- Se crea una Traffic Mirror Session que apunta al analizador
- Se crea un attachment al Transit Gateway (para permitir comunicación entre VPCs)

Terraform también intentará consultar la API del analizador para obtener la configuración. Si esto falla, verás un error claro indicando que el email no está registrado o que la API no está disponible.

### Paso 5: Desplegar

```bash
terraform apply
```

Una vez completado, el tráfico de la instancia EC2 del cliente comenzará a espejarse automáticamente hacia el analizador.

### Paso 6: Verificar la conexión

Puedes verificar que la sesión de mirroring esté activa:

```bash
terraform output mirror_session_id
```

Luego en la consola de AWS, ve a EC2 > Traffic Mirroring > Sessions y verifica que el estado sea `available`.

También puedes conectarte a la instancia del cliente y generar algo de tráfico (por ejemplo, hacer un curl a un sitio web). Ese tráfico debería aparecer en los logs del analizador.

### Notas sobre el módulo cliente

- Cada cliente necesita su propio despliegue de este módulo (o puedes usar workspaces de Terraform si prefieres).
- El módulo cliente lee el estado del analizador desde `../analizer/terraform.tfstate`. Asegúrate de que ese archivo exista después de desplegar el analizador.
- Si necesitas múltiples clientes, simplemente repite estos pasos con diferentes `client_email` y ajusta los CIDRs de las VPCs para evitar conflictos.

## Troubleshooting

### El despliegue del analizador falla con errores de permisos

Verifica que tu usuario/rol de AWS tenga permisos para crear todos los recursos necesarios. Los más comunes que suelen faltar son:

- `ec2:CreateTransitGateway`
- `ecs:*` (para crear clusters, servicios, etc.)
- `ecr:*` (para crear repositorios)
- `s3:*` (para crear buckets)

### El servicio ECS no inicia las tareas

Revisa:

1. Que la imagen del contenedor esté en ECR y tenga el tag `latest`.
2. Los logs de CloudWatch para ver errores del contenedor.
3. Que los security groups permitan el tráfico necesario (puerto 8080 para health checks, 4789 para VXLAN).
4. Que las subnets tengan acceso a internet (para pull de imágenes de ECR).

### El despliegue del cliente falla al consultar la API

Posibles causas:

1. El email no está registrado en el sistema. Regístralo primero usando la API o el dashboard.
2. La API no está disponible. Verifica que el servicio ECS esté corriendo y que el NLB tenga el target group saludable.
3. La URL de la API es incorrecta. Si usas `api_url` manualmente, asegúrate de que sea la correcta y que incluya el endpoint completo: `http://<nlb-dns>/v1/clients/terraform-config`

### El tráfico no se está espejando

1. Verifica que la Traffic Mirror Session esté en estado `available` en la consola de AWS.
2. Revisa que el Traffic Mirror Target del analizador esté correcto.
3. Asegúrate de que las reglas del Traffic Mirror Filter permitan el tráfico que quieres espejar (por defecto permite TCP y UDP en todas las direcciones).
4. Verifica que el NLB interno del analizador esté saludable y que el target group tenga las tareas de ECS registradas.

### Conflictos de CIDR

Si tienes conflictos con redes existentes, ajusta los CIDRs en `terraform.tfvars`. Por defecto:

- Analizador: `10.10.0.0/16`
- Cliente: `10.20.0.0/16`

Puedes cambiarlos a lo que necesites, solo asegúrate de que no se solapen entre sí ni con otras VPCs que tengas.

## Despliegue de Múltiples Clientes

Para desplegar múltiples clientes, tienes varias opciones:

1. **Usar directorios separados**: Crea copias del directorio `client` para cada cliente (por ejemplo, `client1`, `client2`, etc.) y ajusta los CIDRs y emails en cada uno.

2. **Usar workspaces de Terraform**: Mantén un solo directorio `client` y usa workspaces para separar los estados.

3. **Parametrizar con variables**: Usa variables para el email y los CIDRs, y despliega desde el mismo directorio cambiando los valores.

Cualquiera de estas opciones funciona. La opción 1 es la más simple pero menos escalable. La opción 3 es más limpia si tienes muchos clientes.

## Destruir la Infraestructura

Para eliminar todo:

```bash
# Primero destruye los clientes (dependen del analizador)
cd terraform/client
terraform destroy

# Luego destruye el analizador
cd ../analizer
terraform destroy
```

**Nota**: Si tienes imágenes en ECR que quieres conservar, asegúrate de hacer backup antes de destruir, ya que el repositorio se eliminará.

## Siguientes Pasos

Una vez desplegado todo:

1. Verifica que el dashboard sea accesible desde la URL del bucket S3.
2. Accede a la API usando la URL del NLB público.
3. Registra clientes en el sistema.
4. Monitorea los logs de CloudWatch para ver el tráfico espejado y las detecciones.

Si necesitas hacer cambios en la infraestructura, simplemente edita los archivos `.tf` y ejecuta `terraform plan` y `terraform apply` nuevamente. Terraform se encargará de actualizar solo lo que cambió.

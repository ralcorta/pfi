# 🏗️ Arquitectura Terraform - VPC Mirroring

## 📁 Estructura de Archivos

```
terraform/
├── main.tf              # Configuración básica
├── vpc_analizador.tf    # VPC del servicio de detección
├── vpc_cliente.tf       # VPC cliente de ejemplo
├── variables.tf         # Variables de configuración
├── outputs.tf           # Outputs de recursos
└── ARQUITECTURA.md      # Este diagrama
```

## 🎯 Arquitectura de Red

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPC CLIENTE (10.1.0.0/16)                   │
│                    (vpc_cliente.tf)                            │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Internet Gateway                                           │
│  ├── Subnet Pública (10.1.1.0/24)                             │
│  │   └── 💻 Instancias Cliente                                │
│  └── Subnet Privada (10.1.2.0/24)                            │
│      └── 🔌 ENI Cliente (10.1.2.10) ← Captura TODO el tráfico │
│          ├── 🪞 Mirror Filter (Solo TCP)                      │
│          └── 🔗 Mirror Session → Envía a VPC Analizador       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ VPC Mirroring
                                    │ (Sin Peering)
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VPC ANALIZADOR (10.0.0.0/16)                  │
│                  (vpc_analizador.tf)                           │
├─────────────────────────────────────────────────────────────────┤
│  🌐 Internet Gateway                                           │
│  ├── Subnet Pública (10.0.1.0/24)                             │
│  │   └── 🔐 Bastion Host (Opcional)                           │
│  └── Subnet Privada (10.0.2.0/24)                            │
│      ├── 🎯 ENI Mirror Target (10.0.2.100) ← Recibe tráfico  │
│      └── 🛡️ Sensor de IA ← Procesa tráfico                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Tráfico

```
1. Cliente genera tráfico en su VPC
   ↓
2. ENI Cliente (10.1.2.10) captura TODO el tráfico
   ↓
3. Mirror Filter filtra solo TCP
   ↓
4. Mirror Session envía tráfico al ENI Target
   ↓
5. ENI Target (10.0.2.100) recibe tráfico
   ↓
6. Sensor de IA procesa y detecta ransomware
```

## 📋 Recursos por Archivo

### 🔧 `main.tf`

- Provider AWS
- Configuración Terraform
- Versiones requeridas

### 🏢 `vpc_analizador.tf`

- **VPC**: `vpc_analizador` (10.0.0.0/16)
- **Internet Gateway**: `igw_analizador`
- **Subnets**:
  - Pública: `analizador_public_subnet` (10.0.1.0/24)
  - Privada: `analizador_private_subnet` (10.0.2.0/24)
- **Route Tables**: Pública y privada
- **Security Groups**:
  - `mirror_target` - Recibe tráfico de clientes
  - `sensor` - Para el sensor de IA
- **ENI Mirror Target**: `mirror_target` (10.0.2.100)

### 🏢 `vpc_cliente.tf`

- **VPC**: `vpc_cliente` (10.1.0.0/16)
- **Internet Gateway**: `igw_cliente`
- **Subnets**:
  - Pública: `cliente_public_subnet` (10.1.1.0/24)
  - Privada: `cliente_private_subnet` (10.1.2.0/24)
- **Route Tables**: Pública y privada
- **Security Groups**:
  - `cliente_instances` - Para instancias del cliente
- **VPC Mirroring**:
  - `cliente_eni` (10.1.2.10) - Captura tráfico
  - `cliente_filter` - Filtro TCP
  - `cliente_mirror` - Session hacia analizador

## 🎯 Casos de Uso

### 🏢 **VPC Analizador** (Tu Servicio)

- Recibe tráfico de múltiples clientes
- Procesa con IA para detectar ransomware
- Escalable para muchos clientes

### 🏢 **VPC Cliente** (Ejemplo)

- Simula un cliente real
- Envía su tráfico al analizador
- Perfecto para demos y testing

## 🚀 Comandos de Despliegue

```bash
# Desplegar todo
terraform init
terraform plan
terraform apply

# Solo el analizador (producción)
terraform apply -target=aws_vpc.vpc_analizador

# Solo el cliente (demo)
terraform apply -target=aws_vpc.vpc_cliente

# Ver outputs
terraform output vpc_mirroring_summary
terraform output cliente_demo_config
```

## 🔍 Verificación

```bash
# Ver configuración del analizador
terraform output vpc_analizador_id
terraform output mirror_target_private_ip

# Ver configuración del cliente
terraform output vpc_cliente_id
terraform output cliente_eni_id
```

## 💡 Ventajas de esta Arquitectura

1. **✅ Separación Clara**: Cada VPC en su archivo
2. **✅ VPC Mirroring**: Sin necesidad de peering
3. **✅ Escalable**: Múltiples clientes pueden enviar tráfico
4. **✅ Seguro**: Solo recibe tráfico, no envía de vuelta
5. **✅ Mantenible**: Fácil de modificar cada VPC por separado

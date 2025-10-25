<template>
  <div class="detections-container">
    <div class="detections-header">
      <h2>Detecciones de Malware</h2>
      <p>{{ detections.length }} detecciones encontradas</p>
    </div>
    
    <div v-if="loading" class="loading">
      <p>🔄 Cargando detecciones...</p>
    </div>
    
    <div v-else-if="error" class="error">
      <p>❌ {{ error }}</p>
      <button @click="$emit('retry')" class="btn btn-primary">
        🔄 Reintentar
      </button>
    </div>
    
    <div v-else-if="detections.length === 0" class="empty-state">
      <h3>🔍 No se encontraron detecciones</h3>
      <p>No hay registros de malware en la base de datos.</p>
      <button @click="$emit('start-demo')" class="btn btn-success">
        🚀 Iniciar Demo
      </button>
    </div>
    
    <div v-else class="table-container">
      <table class="detections-table">
        <thead>
          <tr>
            <th>IP Origen</th>
            <!-- <th>Estado</th> -->
            <th>Paquetes</th>
            <th>Puertos</th>
            <th>Primera Detección</th>
            <th>Última Detección</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="detection in detections" :key="detection.id" class="fade-in">
            <td>
              <span class="ip-address">{{ detection.source_ip }}</span>
            </td>
            <!-- <td>
              <span class="status-badge" :class="getStatusClass(detection)">
                {{ getStatusText(detection) }}
              </span>
            </td> -->
            <td>
              <strong>{{ detection.packet_count }}</strong>
            </td>
            <td>
              <div class="ports">
                <span 
                  v-for="port in detection.ports?.slice(0, 3)" 
                  :key="`${port.src_port}-${port.dst_port}`"
                  class="port"
                >
                  {{ port.src_port }}→{{ port.dst_port }}
                </span>
                <span v-if="detection.ports?.length > 3" class="port-more">
                  +{{ detection.ports.length - 3 }} más
                </span>
              </div>
            </td>
            <td class="timestamp">
              {{ formatTimestamp(detection.first_seen) }}
            </td>
            <td class="timestamp">
              {{ formatTimestamp(detection.last_seen) }}
            </td>
            <td>
              <button 
                @click="$emit('view-details', detection)" 
                class="btn btn-secondary btn-sm"
              >
                Ver
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DetectionTable',
  props: {
    detections: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: null
    }
  },
  emits: ['retry', 'start-demo', 'view-details'],
  methods: {
    getStatusClass(detection) {
      const now = Math.floor(Date.now() / 1000)
      const lastSeen = detection.last_seen || detection.first_seen
      const timeDiff = now - lastSeen
      
      return timeDiff < 300 ? 'status-active' : 'status-inactive'
    },
    
    getStatusText(detection) {
      const now = Math.floor(Date.now() / 1000)
      const lastSeen = detection.last_seen || detection.first_seen
      const timeDiff = now - lastSeen
      
      return timeDiff < 300 ? 'Activo' : 'Inactivo'
    },
    
    formatTimestamp(timestamp) {
      if (!timestamp) return 'N/A'
      const date = new Date(timestamp * 1000)
      return date.toLocaleString('es-ES', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.table-container {
  overflow-x: auto;
}

.detections-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.detections-table th,
.detections-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.detections-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
  position: sticky;
  top: 0;
  z-index: 10;
}

.detections-table tr:hover {
  background: #f8f9fa;
}

.detections-table tr:last-child td {
  border-bottom: none;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.port-more {
  background: #6c757d;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: 'Courier New', monospace;
}

@media (max-width: 768px) {
  .detections-table {
    font-size: 0.8rem;
  }
  
  .detections-table th,
  .detections-table td {
    padding: 8px 10px;
  }
  
  .detections-table th:nth-child(4),
  .detections-table td:nth-child(4),
  .detections-table th:nth-child(5),
  .detections-table td:nth-child(5) {
    display: none;
  }
}
</style>

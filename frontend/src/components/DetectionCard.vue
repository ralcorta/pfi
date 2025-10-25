<template>
  <div class="detection-card">
    <div class="card-header">
      <h3 class="ip-address">{{ detection.source_ip }}</h3>
      <span class="status-badge" :class="statusClass">
        {{ statusText }}
      </span>
    </div>
    
    <div class="card-body">
      <div class="stats-row">
        <div class="stat">
          <span class="stat-label">Paquetes:</span>
          <span class="stat-value">{{ detection.packet_count }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Puertos:</span>
          <span class="stat-value">{{ detection.ports?.length || 0 }}</span>
        </div>
      </div>
      
      <div class="ports-section" v-if="detection.ports?.length">
        <h4>Puertos detectados:</h4>
        <div class="ports">
          <span 
            v-for="port in detection.ports" 
            :key="`${port.src_port}-${port.dst_port}`"
            class="port"
          >
            {{ port.src_port }} → {{ port.dst_port }}
          </span>
        </div>
      </div>
      
      <div class="timestamps">
        <div class="timestamp" v-if="detection.first_seen">
          <span class="timestamp-label">Primera detección:</span>
          <span class="timestamp-value">{{ formatTimestamp(detection.first_seen) }}</span>
        </div>
        <div class="timestamp" v-if="detection.last_seen">
          <span class="timestamp-label">Última detección:</span>
          <span class="timestamp-value">{{ formatTimestamp(detection.last_seen) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'DetectionCard',
  props: {
    detection: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const statusClass = computed(() => {
      const now = Math.floor(Date.now() / 1000)
      const lastSeen = props.detection.last_seen || props.detection.first_seen
      const timeDiff = now - lastSeen
      
      // Si fue detectado en los últimos 5 minutos, está activo
      return timeDiff < 300 ? 'status-active' : 'status-inactive'
    })
    
    const statusText = computed(() => {
      const now = Math.floor(Date.now() / 1000)
      const lastSeen = props.detection.last_seen || props.detection.first_seen
      const timeDiff = now - lastSeen
      
      return timeDiff < 300 ? 'Activo' : 'Inactivo'
    })
    
    const formatTimestamp = (timestamp) => {
      if (!timestamp) return 'N/A'
      const date = new Date(timestamp * 1000)
      return date.toLocaleString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }
    
    return {
      statusClass,
      statusText,
      formatTimestamp
    }
  }
}
</script>

<style scoped>
.detection-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.detection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.card-header {
  background: #f8f9fa;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #dee2e6;
}

.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #495057;
}

.card-body {
  padding: 20px;
}

.stats-row {
  display: flex;
  gap: 30px;
  margin-bottom: 15px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: 500;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: bold;
  color: #495057;
}

.ports-section {
  margin-bottom: 15px;
}

.ports-section h4 {
  margin-bottom: 8px;
  color: #495057;
  font-size: 1rem;
}

.ports {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.port {
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
  color: #495057;
}

.timestamps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timestamp {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.timestamp-label {
  color: #6c757d;
  font-weight: 500;
}

.timestamp-value {
  color: #495057;
  font-family: 'Courier New', monospace;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active {
  background: #d4edda;
  color: #155724;
}

.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.ip-address {
  font-family: 'Courier New', monospace;
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 1rem;
  color: #495057;
}

@media (max-width: 768px) {
  .stats-row {
    flex-direction: column;
    gap: 15px;
  }
  
  .card-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .timestamp {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>

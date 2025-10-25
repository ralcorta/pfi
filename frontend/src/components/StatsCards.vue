<template>
  <div class="stats-container">
    <div class="stat-card">
      <h3>Total Paquetes</h3>
      <div class="number">{{ stats.totalPackets }}</div>
    </div>
    
    <div class="stat-card">
      <h3>IPs </h3>
      <div class="number">{{ stats.uniqueIPs }}</div>
    </div>
    
    <div class="stat-card">
      <h3>Estado API</h3>
      <div class="api-status" :class="apiStatusClass">
        {{ apiStatusText }}
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'StatsCards',
  props: {
    detections: {
      type: Array,
      default: () => []
    },
    apiHealth: {
      type: Object,
      default: null
    }
  },
  setup(props) {
    const stats = computed(() => {
      const now = Math.floor(Date.now() / 1000)
      let active = 0
      let inactive = 0
      let totalPackets = 0
      const uniqueIPs = new Set()
      
      props.detections.forEach(detection => {
        uniqueIPs.add(detection.source_ip)
        totalPackets += detection.packet_count || 0
        
        const lastSeen = detection.last_seen || detection.first_seen
        const timeDiff = now - lastSeen
        
        if (timeDiff < 300) { // 5 minutos
          active++
        } else {
          inactive++
        }
      })
      
      return {
        total: props.detections.length,
        active,
        inactive,
        totalPackets,
        uniqueIPs: uniqueIPs.size
      }
    })
    
    const apiStatusClass = computed(() => {
      if (!props.apiHealth) return 'api-status-unknown'
      return props.apiHealth.status === 'healthy' ? 'api-status-healthy' : 'api-status-unhealthy'
    })
    
    const apiStatusText = computed(() => {
      if (!props.apiHealth) return 'Desconocido'
      return props.apiHealth.status === 'healthy' ? 'Saludable' : 'Error'
    })
    
    return {
      stats,
      apiStatusClass,
      apiStatusText
    }
  }
}
</script>

<style scoped>
.api-status {
  font-size: 1.2rem;
  font-weight: bold;
  padding: 8px 16px;
  border-radius: 20px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.api-status-healthy {
  background: #d4edda;
  color: #155724;
}

.api-status-unhealthy {
  background: #f8d7da;
  color: #721c24;
}

.api-status-unknown {
  background: #fff3cd;
  color: #856404;
}
</style>

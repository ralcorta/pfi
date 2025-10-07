<template>
  <div class="app">
    <!-- Header -->
    <header class="header">
      <h1>🛡️ Malware Detection Dashboard</h1>
      <p>Monitoreo en tiempo real de detecciones de malware</p>
    </header>

    <!-- Stats Cards -->
    <StatsCards 
      :detections="detections" 
      :api-health="apiHealth"
    />

    <!-- Controls -->
    <div class="controls">
      <button 
        @click="loadDetections" 
        :disabled="loading"
        class="btn btn-primary"
      >
        🔄 {{ loading ? 'Cargando...' : 'Actualizar' }}
      </button>
      
      <button 
        @click="startDemo" 
        :disabled="loading"
        class="btn btn-success"
      >
        🚀 Iniciar Demo
      </button>
      
      <button 
        @click="stopDemo" 
        :disabled="loading"
        class="btn btn-danger"
      >
        ⏹️ Detener Demo
      </button>
      
      <button 
        @click="toggleAutoRefresh" 
        :class="autoRefresh ? 'btn btn-secondary' : 'btn btn-primary'"
      >
        {{ autoRefresh ? '⏸️ Pausar Auto-refresh' : '▶️ Auto-refresh' }}
      </button>
    </div>

    <!-- Main Content -->
    <DetectionTable
      :detections="detections"
      :loading="loading"
      :error="error"
      @retry="loadDetections"
      @start-demo="startDemo"
      @view-details="viewDetails"
    />

    <!-- Modal para detalles -->
    <div v-if="selectedDetection" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Detalles de Detección</h3>
          <button @click="closeModal" class="btn-close">×</button>
        </div>
        <div class="modal-body">
          <DetectionCard :detection="selectedDetection" />
        </div>
      </div>
    </div>

    <!-- Notifications -->
    <div v-if="notification" class="notification" :class="notification.type">
      {{ notification.message }}
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { malwareAPI } from './services/api'
import StatsCards from './components/StatsCards.vue'
import DetectionTable from './components/DetectionTable.vue'
import DetectionCard from './components/DetectionCard.vue'

export default {
  name: 'App',
  components: {
    StatsCards,
    DetectionTable,
    DetectionCard
  },
  setup() {
    const detections = ref([])
    const loading = ref(false)
    const error = ref(null)
    const apiHealth = ref(null)
    const selectedDetection = ref(null)
    const autoRefresh = ref(false)
    const refreshInterval = ref(null)
    const notification = ref(null)

    const showNotification = (message, type = 'info') => {
      notification.value = { message, type }
      setTimeout(() => {
        notification.value = null
      }, 3000)
    }

    const loadDetections = async () => {
      loading.value = true
      error.value = null
      
      try {
        const response = await malwareAPI.getDetections()
        detections.value = response.detections || []
        showNotification(`✅ ${detections.value.length} detecciones cargadas`, 'success')
      } catch (err) {
        error.value = err.message
        showNotification(`❌ Error: ${err.message}`, 'error')
      } finally {
        loading.value = false
      }
    }

    const loadHealth = async () => {
      try {
        apiHealth.value = await malwareAPI.getHealth()
      } catch (err) {
        console.error('Error cargando health:', err)
      }
    }

    const startDemo = async () => {
      loading.value = true
      try {
        await malwareAPI.startDemo()
        showNotification('🚀 Demo iniciado correctamente', 'success')
        // Recargar detecciones después de un breve delay
        setTimeout(loadDetections, 2000)
      } catch (err) {
        showNotification(`❌ Error iniciando demo: ${err.message}`, 'error')
      } finally {
        loading.value = false
      }
    }

    const stopDemo = async () => {
      loading.value = true
      try {
        await malwareAPI.stopDemo()
        showNotification('⏹️ Demo detenido correctamente', 'success')
      } catch (err) {
        showNotification(`❌ Error deteniendo demo: ${err.message}`, 'error')
      } finally {
        loading.value = false
      }
    }

    const toggleAutoRefresh = () => {
      autoRefresh.value = !autoRefresh.value
      
      if (autoRefresh.value) {
        refreshInterval.value = setInterval(() => {
          loadDetections()
          loadHealth()
        }, 5000) // Actualizar cada 5 segundos
        showNotification('▶️ Auto-refresh activado (cada 5s)', 'info')
      } else {
        if (refreshInterval.value) {
          clearInterval(refreshInterval.value)
          refreshInterval.value = null
        }
        showNotification('⏸️ Auto-refresh pausado', 'info')
      }
    }

    const viewDetails = (detection) => {
      selectedDetection.value = detection
    }

    const closeModal = () => {
      selectedDetection.value = null
    }

    // Lifecycle
    onMounted(() => {
      loadDetections()
      loadHealth()
    })

    onUnmounted(() => {
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value)
      }
    })

    return {
      detections,
      loading,
      error,
      apiHealth,
      selectedDetection,
      autoRefresh,
      notification,
      loadDetections,
      startDemo,
      stopDemo,
      toggleAutoRefresh,
      viewDetails,
      closeModal
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #dee2e6;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.modal-header h3 {
  margin: 0;
  color: #495057;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.btn-close:hover {
  background: #e9ecef;
}

.modal-body {
  padding: 20px;
}

.notification {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 15px 20px;
  border-radius: 8px;
  color: white;
  font-weight: 500;
  z-index: 1001;
  animation: slideIn 0.3s ease-out;
  max-width: 400px;
}

.notification.success {
  background: #28a745;
}

.notification.error {
  background: #dc3545;
}

.notification.info {
  background: #17a2b8;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
  }
  
  .notification {
    right: 10px;
    left: 10px;
    max-width: none;
  }
}
</style>

<template>
  <div>
    <h1 class="page-title font-bold mb-4">Detecciones</h1>

    
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
      <VaCard>
        <VaCardContent>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary mb-1">Total de Vulnerabilidades</p>
              <p class="text-3xl font-bold" :class="totalVulnerabilities > 0 ? 'text-danger' : 'text-success'">
                {{ totalVulnerabilities }}
              </p>
            </div>
            <div
              class="p-3 rounded"
              :style="{
                backgroundColor: totalVulnerabilities > 0 ? 'var(--va-danger)' : 'var(--va-success)',
                color: 'white',
              }"
            >
              <VaIcon name="mso-warning" size="large" />
            </div>
          </div>
        </VaCardContent>
      </VaCard>

      <VaCard>
        <VaCardContent>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary mb-1">IPs Vulneradas</p>
              <p class="text-3xl font-bold" :class="vulnerableIps > 0 ? 'text-danger' : 'text-success'">
                {{ vulnerableIps }}
              </p>
            </div>
            <div
              class="p-3 rounded"
              :style="{
                backgroundColor: vulnerableIps > 0 ? 'var(--va-danger)' : 'var(--va-success)',
                color: 'white',
              }"
            >
              <VaIcon name="mso-computer" size="large" />
            </div>
          </div>
        </VaCardContent>
      </VaCard>
    </div>

    <VaCard>
      <VaCardContent>
        <VaDataTable :items="groupedDetections" :columns="columns" :loading="loading">
          <template #cell(src_ip)="{ rowData }">
            <strong>{{ rowData.src_ip }}</strong>
          </template>

          <template #cell(malware_count)="{ rowData }">
            <VaBadge
              :text="rowData.malware_count.toString()"
              :color="rowData.malware_count > 0 ? 'danger' : 'success'"
            />
          </template>

          <template #cell(last_detection)="{ rowData }">
            {{ formatTimestamp(rowData.last_detection) }}
          </template>

          <template #cell(actions)="{ rowData }">
            <VaButton preset="primary" size="small" icon="mso-visibility" @click="openDetailsModal(rowData.src_ip)">
              Ver Detalles
            </VaButton>
          </template>
        </VaDataTable>
      </VaCardContent>
    </VaCard>

    
    <VaModal
      v-model="showDetailsModal"
      size="large"
      max-width="90vw"
      close-button
      hide-default-actions
      :title="`Detecciones para ${selectedSrcIp}`"
    >
      <VaCardContent>
        <VaDataTable :items="selectedDetections" :columns="detailColumns" :loading="false">
          <template #cell(vni)="{ rowData }">
            {{ rowData.vni }}
          </template>

          <template #cell(src_port)="{ rowData }">
            {{ rowData.src_port }}
          </template>

          <template #cell(src_mac)="{ rowData }">
            {{ rowData.src_mac }}
          </template>

          <template #cell(protocol)="{ rowData }">
            <VaBadge :text="rowData.protocol" color="info" />
          </template>

          <template #cell(is_malware)="{ rowData }">
            <VaBadge
              :text="rowData.is_malware ? 'Malware' : 'Safe'"
              :color="rowData.is_malware ? 'danger' : 'success'"
            />
          </template>

          <template #cell(dst_port)="{ rowData }">
            {{ rowData.dst_port }}
          </template>

          <template #cell(malware_probability)="{ rowData }">
            {{ (rowData.malware_probability * 100).toFixed(2) }}%
          </template>

          <template #cell(dst_ip)="{ rowData }">
            {{ rowData.dst_ip }}
          </template>

          <template #cell(dst_mac)="{ rowData }">
            {{ rowData.dst_mac }}
          </template>

          <template #cell(timestamp)="{ rowData }">
            {{ formatTimestamp(rowData.timestamp) }}
          </template>
        </VaDataTable>
      </VaCardContent>
      <VaCardActions align="right">
        <VaButton preset="secondary" @click="showDetailsModal = false">Cerrar</VaButton>
      </VaCardActions>
    </VaModal>
  </div>
</template>

<script setup lang="ts">import { ref, onMounted, computed } from 'vue'
import { defineVaDataTableColumns } from 'vuestic-ui'
import api from '../services/api'
import { useToast } from 'vuestic-ui'
interface Detection {
  vni: number
  src_ip: string
  src_port: number
  src_mac: string
  protocol: string
  is_malware: boolean
  dst_port: number
  malware_probability: number
  id: string
  dst_ip: string
  dst_mac: string
  timestamp: number
}
interface DetectionsResponse {
  detections: Detection[]
}
interface GroupedDetection {
  src_ip: string
  total_detections: number
  malware_count: number
  last_detection: number
  detections: Detection[]
}
const columns = defineVaDataTableColumns([
  { label: 'Source IP', key: 'src_ip', sortable: true },
  { label: 'Detecciones Malware', key: 'malware_count', sortable: true },
  { label: 'Última Detección', key: 'last_detection', sortable: true },
  { label: 'Acciones', key: 'actions', align: 'right' },
])
const detailColumns = defineVaDataTableColumns([
  { label: 'VNI', key: 'vni', sortable: true },
  { label: 'Source Port', key: 'src_port', sortable: true },
  { label: 'Source MAC', key: 'src_mac' },
  { label: 'Protocol', key: 'protocol', sortable: true },
  { label: 'Is Malware', key: 'is_malware', sortable: true },
  { label: 'Destination Port', key: 'dst_port', sortable: true },
  { label: 'Malware Probability', key: 'malware_probability', sortable: true },
  { label: 'Destination IP', key: 'dst_ip', sortable: true },
  { label: 'Destination MAC', key: 'dst_mac' },
  { label: 'Timestamp', key: 'timestamp', sortable: true },
])
const detections = ref<Detection[]>([])
const loading = ref(false)
const showDetailsModal = ref(false)
const selectedSrcIp = ref('')
const { init } = useToast()
const groupedDetections = computed<GroupedDetection[]>(() => {
  const grouped = new Map<string, Detection[]>()
  detections.value.forEach((detection) => {
    const ip = detection.src_ip
    if (!grouped.has(ip)) {
      grouped.set(ip, [])
    }
    grouped.get(ip)!.push(detection)
  })
  return Array.from(grouped.entries()).map(([src_ip, detections]) => {
    const malware_count = detections.filter((d) => d.is_malware).length
    const last_detection = Math.max(...detections.map((d) => d.timestamp))
    return {
      src_ip,
      total_detections: detections.length,
      malware_count,
      last_detection,
      detections,
    }
  })
})
const selectedDetections = computed<Detection[]>(() => {
  const group = groupedDetections.value.find((g) => g.src_ip === selectedSrcIp.value)
  return group ? group.detections : []
})
const totalVulnerabilities = computed(() => {
  return detections.value.filter((d) => d.is_malware).length
})
const vulnerableIps = computed(() => {
  return groupedDetections.value.filter((g) => g.malware_count > 0).length
})
const openDetailsModal = (srcIp: string) => {
  selectedSrcIp.value = srcIp
  showDetailsModal.value = true
}
const fetchDetections = async () => {
  loading.value = true
  try {
    const { fetchWithAuth } = await import('../services/api')
    const response = await fetchWithAuth(api.detections())
    if (!response.ok) {
      if (response.status === 401) {
        const { logout } = await import('../services/auth')
        logout()
        window.location.href = '/auth/login'
        return
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data: DetectionsResponse = await response.json()
    detections.value = data.detections || []
  } catch (error) {
    console.error('Error fetching detections:', error)
    init({
      message: 'Error al cargar las detecciones',
      color: 'danger',
    })
  } finally {
    loading.value = false
  }
}
const formatTimestamp = (timestamp: number) => {
  return new Date(timestamp).toLocaleString()
}
onMounted(() => {
  fetchDetections()
})</script>

<style scoped>
.page-title {
  font-size: 2rem;
}
</style>

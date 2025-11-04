<template>
  <div>
    <h1 class="page-title font-bold mb-4">Mi VNI</h1>

    <VaCard v-if="loading">
      <VaCardContent>
        <div class="flex flex-col items-center justify-center p-8">
          <VaIcon name="mso-hourglass_empty" size="64px" color="secondary" class="mb-4" />
          <p class="text-lg text-secondary">Cargando información...</p>
        </div>
      </VaCardContent>
    </VaCard>

    <VaCard v-else-if="error">
      <VaCardContent>
        <div class="flex flex-col items-center justify-center p-8">
          <VaIcon name="mso-error" size="64px" color="danger" class="mb-4" />
          <h2 class="text-2xl font-semibold mb-2 text-danger">Error</h2>
          <p class="text-lg text-secondary mb-4">{{ error }}</p>
        </div>
      </VaCardContent>
    </VaCard>

    <VaCard v-else>
      <VaCardContent>
        <div class="flex flex-col items-center justify-center p-8">
          <VaIcon name="mso-computer" size="64px" color="primary" class="mb-4" />
          <h2 class="text-2xl font-semibold mb-2">VNI del Cliente</h2>
          <div v-if="userInfo" class="text-4xl font-bold text-primary mb-4">
            {{ userInfo.vni_cliente }}
          </div>
          <div v-else class="text-lg text-secondary mb-4">No disponible</div>
          <div v-if="userInfo" class="text-sm text-secondary mt-4 text-center max-w-md">
            <p class="mb-2"><strong>Email:</strong> {{ userInfo.email }}</p>
            <p class="mb-2"><strong>Traffic Mirror Target ID:</strong> {{ userInfo.traffic_mirror_target_id }}</p>
            <p class="mb-4"><strong>Fecha de creación:</strong> {{ formatDate(userInfo.created_at) }}</p>
          </div>
          <p class="text-sm text-secondary text-center max-w-md">
            El VNI (Virtual Network Identifier) es un identificador único asignado a su infraestructura virtual. Este
            valor es de solo lectura y no puede ser modificado.
          </p>
        </div>
      </VaCardContent>
    </VaCard>
  </div>
</template>

<script lang="ts" setup>import { ref, onMounted } from 'vue'
import { useToast } from 'vuestic-ui'
import { getCurrentUser, type CurrentUser } from '../services/user'
const { init } = useToast()
const loading = ref(true)
const error = ref<string | null>(null)
const userInfo = ref<CurrentUser | null>(null)
const formatDate = (timestamp: number) => {
  return new Date(timestamp).toLocaleString('es-AR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    userInfo.value = await getCurrentUser()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error al cargar la información del usuario'
    init({
      message: error.value,
      color: 'danger',
    })
  } finally {
    loading.value = false
  }
})</script>

<style scoped>
.page-title {
  font-size: 1.875rem;
  font-weight: 700;
}
</style>

<template>
  <VaForm ref="form" @submit.prevent="submit">
    <h1 class="font-semibold text-4xl mb-4">Establecer Contraseña</h1>

    <div v-if="!tokenValid && !loading" class="mb-4">
      <div class="p-4 mb-4 rounded bg-red-50 border border-red-200 text-red-700">
        {{ errorMessage || 'Token inválido o expirado' }}
      </div>
    </div>

    <template v-if="tokenValid && !success">
      <VaInput
        v-model="formData.password"
        :rules="passwordRules"
        :type="isPasswordVisible ? 'text' : 'password'"
        class="mb-4"
        label="Nueva Contraseña"
        :disabled="submitting"
      >
        <template #appendInner>
          <VaIcon
            :name="isPasswordVisible ? 'mso-visibility_off' : 'mso-visibility'"
            class="cursor-pointer"
            color="secondary"
            @click="isPasswordVisible = !isPasswordVisible"
          />
        </template>
      </VaInput>
      <VaInput
        v-model="formData.passwordConfirm"
        :rules="[
          (v) => !!v || 'El campo de confirmación es requerido',
          (v) => v === formData.password || 'Las contraseñas no coinciden',
        ]"
        :type="isPasswordVisible ? 'text' : 'password'"
        class="mb-4"
        label="Confirmar Contraseña"
        :disabled="submitting"
      >
        <template #appendInner>
          <VaIcon
            :name="isPasswordVisible ? 'mso-visibility_off' : 'mso-visibility'"
            class="cursor-pointer"
            color="secondary"
            @click="isPasswordVisible = !isPasswordVisible"
          />
        </template>
      </VaInput>

      <div class="flex justify-center mt-4">
        <VaButton class="w-full" :loading="submitting" :disabled="submitting" @click="submit">
          Establecer Contraseña
        </VaButton>
      </div>
    </template>

    <div v-if="success" class="text-center">
      <div class="p-4 mb-4 rounded bg-green-50 border border-green-200 text-green-700">
        ¡Contraseña establecida exitosamente!
      </div>
      <VaButton @click="goToLogin">Ir a Iniciar Sesión</VaButton>
    </div>
  </VaForm>
</template>

<script lang="ts" setup>import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useForm, useToast } from 'vuestic-ui'
const { validate } = useForm('form')
const router = useRouter()
const route = useRoute()
const { init } = useToast()
const formData = reactive({
  password: '',
  passwordConfirm: '',
})
const isPasswordVisible = ref(false)
const loading = ref(true)
const tokenValid = ref(false)
const submitting = ref(false)
const success = ref(false)
const errorMessage = ref('')
const passwordRules = [
  (v: string) => !!v || 'El campo contraseña es requerido',
  (v: string) => (v && v.length >= 6) || 'La contraseña debe tener al menos 6 caracteres',
]
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
const verifyToken = async () => {
  const token = route.query.token as string
  if (!token) {
    errorMessage.value = 'Token no proporcionado'
    loading.value = false
    return
  }
  try {
    const response = await fetch(`${API_BASE_URL}/v1/users/verify-token?token=${encodeURIComponent(token)}`)
    const data = await response.json()
    if (data.valid) {
      tokenValid.value = true
    } else {
      errorMessage.value = data.message || 'Token inválido o expirado'
    }
  } catch (error) {
    errorMessage.value = 'Error al verificar el token'
    console.error('Error verifying token:', error)
  } finally {
    loading.value = false
  }
}
const submit = async () => {
  if (!validate()) {
    return
  }
  const token = route.query.token as string
  if (!token) {
    init({ message: 'Token no encontrado', color: 'danger' })
    return
  }
  submitting.value = true
  try {
    const response = await fetch(`${API_BASE_URL}/v1/users/setup-password?token=${encodeURIComponent(token)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        password: formData.password,
        password_confirm: formData.passwordConfirm,
      }),
    })
    const data = await response.json()
    if (response.ok) {
      success.value = true
      init({ message: 'Contraseña establecida exitosamente', color: 'success' })
    } else {
      init({ message: data.detail || 'Error al establecer contraseña', color: 'danger' })
    }
  } catch (error) {
    init({ message: 'Error de conexión. Por favor, intente nuevamente.', color: 'danger' })
    console.error('Error setting password:', error)
  } finally {
    submitting.value = false
  }
}
const goToLogin = () => {
  router.push({ name: 'login' })
}
onMounted(() => {
  verifyToken()
})</script>

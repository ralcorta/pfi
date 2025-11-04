<template>
  <VaForm ref="form" @submit.prevent="submit">
    <h1 class="font-semibold text-4xl mb-4">Iniciar Sesión</h1>

    <VaInput
      v-model="formData.email"
      :rules="[validators.required, validators.email]"
      class="mb-4"
      label="Email"
      type="email"
    />
    <VaValue v-slot="isPasswordVisible" :default-value="false">
      <VaInput
        v-model="formData.password"
        :rules="[validators.required]"
        :type="isPasswordVisible.value ? 'text' : 'password'"
        class="mb-4"
        label="Contraseña"
        @clickAppendInner.stop="isPasswordVisible.value = !isPasswordVisible.value"
      >
        <template #appendInner>
          <VaIcon
            :name="isPasswordVisible.value ? 'mso-visibility_off' : 'mso-visibility'"
            class="cursor-pointer"
            color="secondary"
          />
        </template>
      </VaInput>
    </VaValue>

    <div v-if="errorMessage" class="p-4 mb-4 rounded bg-red-50 border border-red-200 text-red-700">
      {{ errorMessage }}
    </div>

    <div class="flex justify-center mt-4">
      <VaButton class="w-full" :loading="isLoading" @click="submit">Iniciar Sesión</VaButton>
    </div>
  </VaForm>
</template>

<script lang="ts" setup>import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useToast } from 'vuestic-ui'
import { validators } from '../../services/utils'
import { login } from '../../services/auth'
const { validate } = useForm('form')
const { push } = useRouter()
const { init } = useToast()
const formData = reactive({
  email: '',
  password: '',
})
const isLoading = ref(false)
const errorMessage = ref('')
const submit = async () => {
  if (!validate()) {
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  try {
    await login(formData.email, formData.password)
    init({ message: 'Inicio de sesión exitoso', color: 'success' })
    push({ name: 'home' })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Error al iniciar sesión'
    init({
      message: errorMessage.value,
      color: 'danger',
    })
  } finally {
    isLoading.value = false
  }
}</script>

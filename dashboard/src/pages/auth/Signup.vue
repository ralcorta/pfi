<template>
  <VaForm ref="form" @submit.prevent="submit">
    <h1 class="font-semibold text-4xl mb-4">Registro</h1>

    <VaInput
      v-model="formData.email"
      :rules="[(v) => !!v || 'El campo email es requerido', (v) => /.+@.+\..+/.test(v) || 'El email debe ser válido']"
      class="mb-4"
      label="Email"
      type="email"
    />
    <VaValue v-slot="isPasswordVisible" :default-value="false">
      <VaInput
        ref="password1"
        v-model="formData.password"
        :rules="passwordRules"
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
      <VaInput
        ref="password2"
        v-model="formData.repeatPassword"
        :rules="[
          (v) => !!v || 'El campo de confirmación es requerido',
          (v) => v === formData.password || 'Las contraseñas no coinciden',
        ]"
        :type="isPasswordVisible.value ? 'text' : 'password'"
        class="mb-4"
        label="Confirmar Contraseña"
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

    <div class="flex justify-center mt-4">
      <VaButton class="w-full" @click="submit">Crear Cuenta</VaButton>
    </div>
  </VaForm>
</template>

<script lang="ts" setup>import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useToast } from 'vuestic-ui'
const { validate } = useForm('form')
const { push } = useRouter()
const { init } = useToast()
const formData = reactive({
  email: '',
  password: '',
  repeatPassword: '',
})
const submit = () => {
  if (validate()) {
    init({
      message: 'Registro exitoso',
      color: 'success',
    })
    push({ name: 'home' })
  }
}
const passwordRules: ((v: string) => boolean | string)[] = [
  (v) => !!v || 'El campo contraseña es requerido',
  (v) => (v && v.length >= 8) || 'La contraseña debe tener al menos 8 caracteres',
]</script>

<template>
  <VaLayout v-if="breakpoint.lgUp" class="h-screen bg-[var(--va-background-secondary)]">
    <template #left>
      <div class="bg-[var(--va-background-element)] h-full flex items-center justify-center" style="width: 35vw">
        <img src="/logo_only_eye.png" alt="Logo" style="max-width: 80%; max-height: 80%; object-fit: contain" />
      </div>
    </template>
    <template #content>
      <main class="h-full flex items-center justify-center mx-auto max-w-[420px]">
        <RouterView />
      </main>
    </template>
  </VaLayout>

  <VaLayout v-else class="h-screen bg-[var(--va-background-secondary)]">
    <template #content>
      <div class="p-4">
        <main class="h-full flex flex-col items-center justify-start mx-auto max-w-[420px]">
          <div class="flex flex-col items-center w-full mb-4">
            <img
              src="/logo_only_eye.png"
              alt="Logo"
              style="max-width: 200px; max-height: 200px; object-fit: contain"
              class="mb-4"
            />
          </div>
          <div class="w-full">
            <RouterView />
          </div>
        </main>
      </div>
    </template>
  </VaLayout>
</template>

<script lang="ts" setup>import { useBreakpoint } from 'vuestic-ui'
const breakpoint = useBreakpoint()</script>

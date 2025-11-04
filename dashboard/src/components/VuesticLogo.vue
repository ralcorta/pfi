<template>
  <img
    :height="height"
    :style="{ height: height ? `${height}px` : 'auto', width: 'auto' }"
    src="/logo.png"
    alt="Logo"
  />
</template>

<script lang="ts" setup>withDefaults(
  defineProps<{
    height?: number
    start?: string
    end?: string
  }>(),
  {
    height: 28,
    start: 'primary',
    end: undefined,
  },
)</script>

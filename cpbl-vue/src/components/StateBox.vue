<template>
  <section :class="['empty-state', { 'error-state': type === 'error' }]">
    <i :class="iconClass"></i>
    <h3 v-if="title">{{ title }}</h3>
    <p>{{ message }}</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'empty' },
  title: { type: String, default: '' },
  message: { type: String, default: '尚無資料' }
})

const iconClass = computed(() => {
  if (props.type === 'loading') return 'fa-solid fa-circle-notch fa-spin'
  if (props.type === 'error') return 'fa-solid fa-triangle-exclamation'
  return 'fa-regular fa-calendar'
})
</script>

<template>
  <div class="base-diamond-card">
    <span>{{ label }}</span>
    <div class="base-diamond" aria-hidden="true">
      <i :class="{ occupied: bases.second }" class="base second"></i>
      <i :class="{ occupied: bases.third }" class="base third"></i>
      <i :class="{ occupied: bases.first }" class="base first"></i>
      <i class="home-plate"></i>
    </div>
    <small>{{ runnerText }}</small>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: ''
  },
  bases: {
    type: Object,
    default: () => ({ first: '', second: '', third: '' })
  }
})

const runnerText = computed(() => {
  const runners = [
    props.bases.first ? `一壘 ${props.bases.first}` : '',
    props.bases.second ? `二壘 ${props.bases.second}` : '',
    props.bases.third ? `三壘 ${props.bases.third}` : ''
  ].filter(Boolean)

  return runners.length ? runners.join(' / ') : '壘上無人'
})
</script>

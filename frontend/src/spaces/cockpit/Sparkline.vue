<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ values: (number | null)[]; color?: string; height?: number; max?: number }>(), {
  color: 'var(--accent)',
  height: 34,
  max: 1,
})
const W = 120
const gid = `sg${Math.random().toString(36).slice(2, 8)}`
const pts = computed(() => {
  const v = props.values.filter((x): x is number => x != null)
  if (v.length < 2) return ''
  const top = Math.max(props.max, ...v) || 1
  return v.map((y, i) => `${((i / (v.length - 1)) * W).toFixed(1)},${(props.height - (y / top) * (props.height - 3) - 1).toFixed(1)}`).join(' ')
})
</script>

<template>
  <svg class="spark" :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="none" :style="{ height: `${height}px` }" aria-hidden="true">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" :stop-color="color" stop-opacity="0.28" />
        <stop offset="1" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <template v-if="pts">
      <polygon :points="`0,${height} ${pts} ${W},${height}`" :fill="`url(#${gid})`" />
      <polyline :points="pts" fill="none" :stroke="color" stroke-width="1.8" vector-effect="non-scaling-stroke" stroke-linejoin="round" />
    </template>
  </svg>
</template>

<style scoped>
.spark {
  width: 100%;
  display: block;
}
</style>

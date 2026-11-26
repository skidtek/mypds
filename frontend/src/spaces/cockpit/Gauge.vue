<script setup lang="ts">
import { computed } from 'vue'
import { level } from './format'

const props = defineProps<{ value: number | null; label: string; detail?: string }>()
const R = 34
const C = 2 * Math.PI * R
const arc = 0.75 // jauge en fer à cheval
const dash = computed(() => `${C * arc * Math.min(1, props.value ?? 0)} ${C}`)
const COLORS = { ok: 'var(--accent)', warn: 'var(--warn)', down: 'var(--down)', unknown: 'var(--unknown)' }
const color = computed(() => COLORS[level(props.value)])
</script>

<template>
  <figure class="gauge" :aria-label="`${label} : ${value == null ? $t('inconnu') : Math.round(value * 100) + ' %'}`">
    <svg viewBox="0 0 80 80" aria-hidden="true">
      <circle cx="40" cy="40" :r="R" class="track" :stroke-dasharray="`${C * arc} ${C}`" />
      <circle cx="40" cy="40" :r="R" class="val" :stroke="color" :stroke-dasharray="dash" />
    </svg>
    <span class="v">{{ value == null ? '—' : Math.round(value * 100) }}<small>%</small></span>
    <figcaption>
      <strong>{{ label }}</strong>
      <span v-if="detail" class="faint">{{ detail }}</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.gauge {
  position: relative;
  margin: 0;
  display: grid;
  justify-items: center;
  gap: 4px;
}
svg {
  width: 92px;
  height: 92px;
  transform: rotate(135deg);
}
circle {
  fill: none;
  stroke-width: 7;
  stroke-linecap: round;
}
.track {
  stroke: var(--hairline);
}
.val {
  transition: stroke-dasharray var(--dur-slow) var(--ease);
}
.v {
  position: absolute;
  top: 28px;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.v small {
  font-size: 12px;
  margin-left: 1px;
  font-weight: 600;
}
figcaption {
  display: grid;
  justify-items: center;
  font-size: 12.5px;
  margin-top: -10px;
}
</style>

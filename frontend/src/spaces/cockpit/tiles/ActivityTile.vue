<script setup lang="ts">
import { PhClockCounterClockwise } from '@phosphor-icons/vue'
import { computed } from 'vue'
import { since } from '@/design-system/time'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { taskPhrase } from '../labels'

defineProps<{ editing: boolean }>()
const store = useCockpit()
const items = computed(() => store.tasks.slice(0, 7))

</script>

<template>
  <div class="act">
    <header class="head">
      <PhClockCounterClockwise :size="20" />
      <h3>{{ $t('Dernières activités') }}</h3>
      <DemoBadge v-if="store.anyDemo" class="badge" />
    </header>
    <p v-if="!items.length" class="faint empty">{{ $t('Aucune activité récente.') }}</p>
    <ol v-else class="list">
      <li v-for="t in items" :key="t.upid">
        <span class="dot" :class="t.state" />
        <div class="txt">
          <strong>{{ taskPhrase(t) }}</strong>
          <span class="faint">{{ since(new Date((t.end ?? t.start) * 1000).toISOString()) }} · {{ t.node }}</span>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.act {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.head {
  display: flex;
  align-items: center;
  gap: 10px;
}
h3 {
  font-size: 16.5px;
  font-weight: 680;
}
.badge {
  margin-left: auto;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
  overflow-y: auto;
  max-height: 360px;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--text-3) 50%, transparent) transparent;
}
.list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
}
.list li:hover {
  background: rgb(var(--surface-rgb) / 0.3);
}
.dot.ok {
  background: var(--ok);
}
.dot.running {
  background: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.dot.warning {
  background: var(--warn);
}
.dot.error {
  background: var(--down);
}
.txt {
  display: grid;
  gap: 1px;
  min-width: 0;
}
.txt strong {
  font-size: 14px;
  font-weight: 600;
}
.txt .faint {
  font-size: 12.5px;
}
.empty {
  margin: auto 0;
}
</style>

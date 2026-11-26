<script setup lang="ts">
import { PhArrowUpRight } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile, DockerData } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytes } from '../format'
import TileIcon from '../TileIcon.vue'
import { t } from '@/i18n'

const props = defineProps<{ tile: CockpitTile; editing: boolean }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const c = computed(() => (snap.value?.data as unknown as DockerData | null)?.containers.find((x) => x.name === props.tile.config.container))
const state = computed(() => {
  const x = c.value
  if (!x) return { cls: '', text: snap.value?.data ? t('Introuvable') : t('Inconnu') }
  if (x.state === 'running') return x.health === 'unhealthy' ? { cls: 'warn', text: t('En marche, mauvaise santé') } : { cls: 'ok', text: t('En marche') }
  if (x.state === 'restarting') return { cls: 'warn', text: t('Redémarre') }
  if (x.state === 'paused') return { cls: 'warn', text: t('En pause') }
  return x.on_demand ? { cls: '', text: t('Arrêté (à la demande)') } : { cls: 'down', text: t('Arrêté') }
})
const name = computed(() => props.tile.config.label || c.value?.name || props.tile.config.container)
const href = computed(() => (props.editing ? undefined : props.tile.config.url))
const image = computed(() => (c.value?.image ?? '').replace(/@sha256:.*/, ''))
</script>

<template>
  <component
    :is="href ? 'a' : 'div'"
    class="ct"
    :class="{ link: !!href }"
    :href="href"
    :target="href ? '_blank' : undefined"
    :rel="href ? 'noopener noreferrer' : undefined"
    :aria-label="href ? $t('{name} — {state}, ouvrir le service', { name, state: state.text }) : `${name} — ${state.text}`"
  >
    <TileIcon :icon="tile.config.icon ?? { kind: 'simple', value: 'docker' }" :size="44" />
    <div class="info">
      <strong class="name">{{ name }}</strong>
      <span class="sub faint" :title="c?.image ?? ''">{{ image }}</span>
      <span v-if="c?.state === 'running' && c.cpu_pct != null" class="metrics faint">CPU {{ c.cpu_pct.toLocaleString() }} % · RAM {{ bytes(c.mem_used) }}</span>
    </div>
    <span class="dot" :class="state.cls" :title="state.text" />
    <span class="sr-only">{{ state.text }}</span>
    <DemoBadge v-if="snap?.demo" class="badge" />
    <PhArrowUpRight v-if="href" class="go" :size="15" />
  </component>
</template>

<style scoped>
.ct {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  container-type: inline-size;
  color: inherit;
  text-decoration: none;
}
.info {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.name {
  font-size: 15.5px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub,
.metrics {
  font-size: 12.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metrics {
  display: none;
}
@container (min-width: 300px) {
  .metrics {
    display: block;
  }
}
.dot {
  width: 10px;
  height: 10px;
  flex: none;
}
.dot.warn {
  background: var(--warn);
}
.badge {
  position: absolute;
  right: -6px;
  bottom: -12px;
  height: 15px;
  padding: 0 6px;
  font-size: 9px;
}
.go {
  position: absolute;
  right: -6px;
  bottom: -6px;
  color: var(--text-3);
  opacity: 0;
  transition: opacity var(--dur-fast);
}
.link:hover .go,
.link:focus-visible .go {
  opacity: 1;
}
</style>

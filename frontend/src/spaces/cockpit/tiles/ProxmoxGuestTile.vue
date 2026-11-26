<script setup lang="ts">
import { PhArrowUpRight } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { bytes, pct, ratio } from '../format'
import TileIcon from '../TileIcon.vue'
import { t } from '@/i18n'

const props = defineProps<{ tile: CockpitTile; editing: boolean }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const g = computed(() => store.guest(props.tile.config.connector_id, props.tile.config.guest))
const kind = computed(() => (props.tile.config.guest?.startsWith('qemu') ? 'qemu' : 'lxc'))
const state = computed(() => {
  if (!g.value) return { cls: '', text: snap.value?.data ? t('Introuvable') : t('Inconnu') }
  if (g.value.status === 'running') return { cls: 'ok', text: t('En marche') }
  if (g.value.status === 'stopped') return g.value.on_demand ? { cls: '', text: t('Arrêté (à la demande)') } : { cls: 'down', text: t('Arrêté') }
  return { cls: 'warn', text: g.value.status }
})
const name = computed(() => props.tile.config.label || g.value?.name || props.tile.config.guest)
const href = computed(() => (props.editing ? undefined : props.tile.config.url))
</script>

<template>
  <component
    :is="href ? 'a' : 'div'"
    class="guest"
    :class="{ link: !!href }"
    :href="href"
    :target="href ? '_blank' : undefined"
    :rel="href ? 'noopener noreferrer' : undefined"
    :aria-label="href ? $t('{name} — {state}, ouvrir le service', { name, state: state.text }) : `${name} — ${state.text}`"
  >
    <TileIcon :icon="tile.config.icon" :fallback="kind" :size="44" />
    <div class="info">
      <strong class="name">{{ name }}</strong>
      <span class="sub faint">{{ kind === 'qemu' ? 'VM' : 'LXC' }} {{ g?.vmid ?? '' }}<template v-if="g"> · {{ g.node }}</template></span>
      <span v-if="g && g.status === 'running'" class="metrics faint">
        CPU {{ pct(g.cpu) }} · RAM {{ bytes(g.mem) }} ({{ pct(ratio(g.mem, g.maxmem)) }})
      </span>
    </div>
    <span class="state">
      <span class="dot" :class="state.cls" :title="state.text" />
      <span class="sr-only">{{ state.text }}</span>
    </span>
    <DemoBadge v-if="snap?.demo" class="badge" />
    <PhArrowUpRight v-if="href" class="go" :size="15" />
  </component>
</template>

<style scoped>
.guest {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  container-type: inline-size;
}
.link {
  cursor: pointer;
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

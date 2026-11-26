<script setup lang="ts">
import { PhArrowCircleUp, PhGlobe, PhHardDrives, PhTreeStructure, PhWifiHigh } from '@phosphor-icons/vue'
import { computed } from 'vue'
import type { CockpitTile, UnifiData } from '@/api/types'
import { useCockpit } from '@/stores/cockpit'
import DemoBadge from '../DemoBadge.vue'
import { uptime } from '../format'
import { t } from '@/i18n'

const props = defineProps<{ tile: CockpitTile }>()
const store = useCockpit()
const snap = computed(() => store.snapshot(props.tile.config.connector_id))
const dev = computed(() => (snap.value?.data as unknown as UnifiData | null)?.devices.find((x) => x.id === props.tile.config.device))
const icon = computed(() => ({ gateway: PhGlobe, switch: PhTreeStructure, ap: PhWifiHigh, other: PhHardDrives })[dev.value?.kind ?? 'other'])
const state = computed(() =>
  !dev.value ? { cls: '', text: snap.value?.data ? t('Introuvable') : t('Inconnu') } : dev.value.online ? { cls: 'ok', text: t('En ligne') } : { cls: 'down', text: t('Hors ligne') },
)
const name = computed(() => props.tile.config.label || dev.value?.name || props.tile.config.device)
</script>

<template>
  <div class="dev" :aria-label="`${name} — ${state.text}`">
    <span class="ic"><component :is="icon" :size="24" weight="duotone" /></span>
    <div class="info">
      <strong class="name">{{ name }}</strong>
      <span class="sub faint">{{ dev?.model ?? '' }}<template v-if="dev?.ip"> · {{ dev.ip }}</template></span>
      <span v-if="dev?.online && (dev.cpu_pct != null || dev.uptime_s)" class="metrics faint">
        <template v-if="dev.cpu_pct != null">CPU {{ Math.round(dev.cpu_pct) }} % · RAM {{ Math.round(dev.mem_pct ?? 0) }} % · </template>{{ uptime(dev.uptime_s) }}
      </span>
    </div>
    <PhArrowCircleUp v-if="dev?.firmware_updatable" class="upd" :size="18" weight="fill" :aria-label="$t('Mise à jour disponible')" />
    <span class="dot" :class="state.cls" :title="state.text" />
    <DemoBadge v-if="snap?.demo" class="badge" />
  </div>
</template>

<style scoped>
.dev {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  container-type: inline-size;
}
.ic {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: color-mix(in srgb, #1f6feb 18%, rgb(var(--surface-rgb) / 0.6));
  color: #1f6feb;
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
.upd {
  color: var(--accent);
  flex: none;
}
.dot {
  width: 10px;
  height: 10px;
  flex: none;
}
.badge {
  position: absolute;
  right: -6px;
  bottom: -12px;
  height: 15px;
  padding: 0 6px;
  font-size: 9px;
}
</style>
